"""Fetch tweets from X/Twitter user via GraphQL API through proxy.
    
Usage: python fetch_tweets.py <screen_name> [--cursor <cursor>] [--count <N>]
Output: JSON to stdout — list of tweet objects with id, text, created, likes, rts, replies, views

Requires: proxy at 127.0.0.1:7897 (Clash Verge default)
"""

import urllib.request
import urllib.parse
import json
import ssl
import sys
import os

# ── Config ──────────────────────────────────────────────
os.environ['HTTP_PROXY'] = 'http://127.0.0.1:7897'
os.environ['HTTPS_PROXY'] = 'http://127.0.0.1:7897'

# Bearer token from x.com main JS (static, rarely changes)
BEARER = "AAAAAAAAAAAAAAAAAAAAANRILgAAAAAAnNwIzUejRCOuH5E6I8xnZz4puTs%3D1Zv7ttfk8LF81IUq16cHjhLTvJu4FA33AGWWjCpTnA"

# GraphQL query IDs — EXTRACT FRESH from x.com main JS if these stop working
# Search main.bfb69eea.js (or current bundle) for: queryId:"<ID>",operationName:"UserTweets"
QUERY_ID_USERTWEETS = "hr4gzZONlq23okjU8fIe_A"
QUERY_ID_USER_BY_SCREEN_NAME = "32pL5BWe9WKeSK1MoKv20w"

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE


def api_call(url, method='GET', headers=None, data=None):
    """Make an API call through proxy with SSL workaround."""
    req = urllib.request.Request(url, data=data, headers=headers or {}, method=method)
    with urllib.request.urlopen(req, context=ctx, timeout=15) as resp:
        return json.loads(resp.read())


def activate_guest_token():
    """Get a fresh guest token for X API."""
    resp = api_call(
        "https://api.x.com/1.1/guest/activate.json",
        method='POST',
        headers={"Authorization": f"Bearer {BEARER}", "User-Agent": "Mozilla/5.0"}
    )
    return resp['guest_token']


def get_user_id(screen_name, guest_token):
    """Resolve screen_name to numeric user ID."""
    vars_dict = {"screen_name": screen_name, "withSafetyModeUserFields": True}
    feats_dict = {"hidden_profile_subscriptions_enabled": True, "highlights_tweets_tab_ui_enabled": True}

    query_url = (
        f"https://x.com/i/api/graphql/{QUERY_ID_USER_BY_SCREEN_NAME}/UserByScreenName"
        f"?variables={urllib.parse.quote(json.dumps(vars_dict))}"
        f"&features={urllib.parse.quote(json.dumps(feats_dict))}"
    )

    headers = {
        "Authorization": f"Bearer {BEARER}",
        "x-guest-token": guest_token,
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }

    resp = api_call(query_url, headers=headers)
    result = resp['data']['user']['result']
    return result.get('rest_id', result.get('id'))


def fetch_tweets(user_id, guest_token, cursor=None, count=20):
    """Fetch tweets via UserTweets GraphQL query. Supports cursor pagination."""
    vars_dict = {
        "userId": user_id,
        "count": count,
        "includePromotedContent": False,
        "withVoice": True,
        "withV2Timeline": True
    }
    if cursor:
        vars_dict["cursor"] = cursor

    feats_dict = {
        "responsive_web_graphql_exclude_directive_enabled": True,
        "view_counts_everywhere_api_enabled": True,
        "longform_notetweets_consumption_enabled": True,
        "responsive_web_twitter_article_tweet_consumption_enabled": False,
        "tweet_with_visibility_results_prefer_gql_limited_actions_policy_enabled": True,
        "longform_notetweets_rich_text_read_enabled": True,
        "longform_notetweets_inline_media_enabled": True,
        "responsive_web_media_download_video_enabled": False,
        "responsive_web_enhance_cards_enabled": False
    }

    query_url = (
        f"https://x.com/i/api/graphql/{QUERY_ID_USERTWEETS}/UserTweets"
        f"?variables={urllib.parse.quote(json.dumps(vars_dict))}"
        f"&features={urllib.parse.quote(json.dumps(feats_dict))}"
    )

    headers = {
        "Authorization": f"Bearer {BEARER}",
        "x-guest-token": guest_token,
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }

    resp = api_call(query_url, headers=headers)

    if 'errors' in resp:
        raise Exception(f"API errors: {resp['errors']}")

    # Navigate response structure
    user = resp['data']['user']
    result = user['result']
    timeline = result.get('timeline', {}).get('timeline', {})

    instructions = timeline.get('instructions', [])
    if not instructions:
        # Search deeper — X occasionally changes nesting
        found = []

        def find_instructions(obj, depth=0):
            if depth > 5:
                return
            if isinstance(obj, dict):
                if 'instructions' in obj:
                    found.extend(obj['instructions'])
                for v in obj.values():
                    find_instructions(v, depth + 1)
            elif isinstance(obj, list):
                for item in obj[:3]:
                    find_instructions(item, depth + 1)

        find_instructions(result)
        instructions = found

    # Extract tweets
    tweets = []
    next_cursor = None

    for inst in instructions:
        if inst.get('type') == 'TimelineAddEntries':
            for entry in inst.get('entries', []):
                content = entry.get('content', {})
                if content.get('entryType') == 'TimelineTimelineItem':
                    item_content = content.get('itemContent', {})
                    tweet_result = item_content.get('tweet_results', {}).get('result', {})
                    legacy = tweet_result.get('legacy', {})
                    if legacy:
                        views = tweet_result.get('views', {}).get('count', 0)
                        tweets.append({
                            'id': legacy.get('id_str', ''),
                            'text': legacy.get('full_text', ''),
                            'created': legacy.get('created_at', ''),
                            'likes': legacy.get('favorite_count', 0),
                            'rts': legacy.get('retweet_count', 0),
                            'replies': legacy.get('reply_count', 0),
                            'views': views
                        })
                elif content.get('entryType') == 'TimelineTimelineCursor':
                    if content.get('cursorType') == 'Bottom':
                        next_cursor = content.get('value')

    return {'tweets': tweets, 'next_cursor': next_cursor}


def fetch_all_history(user_id, guest_token, max_pages=100):
    """Paginate through ALL tweets from newest to oldest. Returns complete list."""
    all_tweets = []
    cursor = None
    page = 0

    while page < max_pages:
        result = fetch_tweets(user_id, guest_token, cursor=cursor, count=50)
        tweets = result['tweets']
        cursor = result['next_cursor']

        if not tweets:
            break

        all_tweets.extend(tweets)
        page += 1
        print(f"Page {page}: {len(tweets)} tweets, total {len(all_tweets)}", file=sys.stderr)

        if not cursor:
            break

    return all_tweets


# ── CLI ─────────────────────────────────────────────────
if __name__ == '__main__':
    import argparse

    p = argparse.ArgumentParser(description='Fetch X/Twitter tweets via GraphQL API')
    p.add_argument('screen_name', help='X username (without @)')
    p.add_argument('--cursor', help='Pagination cursor for next page', default=None)
    p.add_argument('--count', type=int, default=20, help='Tweets per page (max ~100)')
    p.add_argument('--all', action='store_true', help='Fetch ALL history (paginates)')
    p.add_argument('--max-pages', type=int, default=100, help='Max pages for --all')

    args = p.parse_args()

    try:
        guest_token = activate_guest_token()
        user_id = get_user_id(args.screen_name, guest_token)

        if args.all:
            tweets = fetch_all_history(user_id, guest_token, max_pages=args.max_pages)
        else:
            result = fetch_tweets(user_id, guest_token, cursor=args.cursor, count=args.count)
            tweets = result['tweets']
            if result['next_cursor']:
                print(f"NEXT_CURSOR: {result['next_cursor']}", file=sys.stderr)

        print(json.dumps(tweets, indent=2, ensure_ascii=False))
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)
