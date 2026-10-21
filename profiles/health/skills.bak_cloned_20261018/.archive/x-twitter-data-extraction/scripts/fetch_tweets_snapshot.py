"""
Quick X/Twitter snapshot: fetch a user's top 97 tweets via guest token.
Usage: python fetch_tweets_snapshot.py <screen_name> [--output tweets.jsonl]

Requires proxy at 127.0.0.1:7897 (or edit PROXY below).
"""
import subprocess, json, urllib.parse, sys, os

BEARER = "AAAAAAAAAAAAAAAAAAAAANRILgAAAAAAnNwIzUejRCOuH5E6I8xnZz4puTs%3D1Zv7ttfk8LF81IUq16cHjhLTvJu4FA33AGWWjCpTnA"
USER_TWEETS_QID = "hr4gzZONlq23okjU8fIe_A"
PROXY = "http://127.0.0.1:7897"


def curl(method, url, headers=None):
    cmd = ["curl", "-sL", "--connect-timeout", "15",
           "-X", method, "--proxy", PROXY]
    if headers:
        for k, v in headers.items():
            cmd.extend(["-H", f"{k}: {v}"])
    cmd.append(url)
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
    if not result.stdout.strip():
        raise RuntimeError(f"Empty response from {url}")
    return json.loads(result.stdout)


def get_user_id(screen_name):
    """Get user ID via fxtwitter (no auth needed)."""
    resp = curl("GET", f"https://api.fxtwitter.com/{screen_name}")
    uid = resp.get("user", {}).get("id")
    if not uid:
        raise RuntimeError(f"Cannot find user ID for @{screen_name}")
    return uid


def fetch_tweets(user_id, count=100):
    """Fetch tweets via UserTweets GraphQL. Returns list of dicts."""
    gt_resp = curl("POST", "https://api.x.com/1.1/guest/activate.json",
                   {"Authorization": f"Bearer {BEARER}"})
    guest_token = gt_resp["guest_token"]

    vars_d = {"userId": user_id, "count": count,
              "includePromotedContent": False,
              "withVoice": True, "withV2Timeline": True}
    feats = {"responsive_web_graphql_exclude_directive_enabled": True,
             "view_counts_everywhere_api_enabled": True,
             "longform_notetweets_consumption_enabled": True,
             "tweet_with_visibility_results_prefer_gql_limited_actions_policy_enabled": True}

    url = (f"https://x.com/i/api/graphql/{USER_TWEETS_QID}/UserTweets"
           f"?variables={urllib.parse.quote(json.dumps(vars_d))}"
           f"&features={urllib.parse.quote(json.dumps(feats))}")

    resp = curl("GET", url, {
        "Authorization": f"Bearer {BEARER}",
        "x-guest-token": guest_token,
        "User-Agent": "Mozilla/5.0"
    })

    tweets = []
    timeline = resp["data"]["user"]["result"]["timeline"]["timeline"]
    for inst in timeline["instructions"]:
        if inst.get("type") == "TimelineAddEntries":
            for entry in inst.get("entries", []):
                content = entry.get("content", {})
                if content.get("entryType") == "TimelineTimelineItem":
                    result = content["itemContent"]["tweet_results"]["result"]
                    legacy = result.get("legacy", {})
                    if legacy:
                        tweets.append({
                            "id": legacy.get("id_str"),
                            "created_at": legacy.get("created_at"),
                            "full_text": legacy.get("full_text"),
                            "favorite_count": legacy.get("favorite_count", 0),
                            "retweet_count": legacy.get("retweet_count", 0),
                            "reply_count": legacy.get("reply_count", 0),
                            "view_count": result.get("views", {}).get("count"),
                        })
    return tweets


def main():
    if len(sys.argv) < 2:
        print(f"Usage: python {sys.argv[0]} <screen_name> [--output file.jsonl]")
        sys.exit(1)

    screen_name = sys.argv[1].lstrip("@")
    output = None
    if "--output" in sys.argv:
        idx = sys.argv.index("--output")
        output = sys.argv[idx + 1]

    print(f"Fetching @{screen_name}...")
    user_id = get_user_id(screen_name)
    tweets = fetch_tweets(user_id)
    print(f"Got {len(tweets)} tweets (guest API limit)")

    if output:
        with open(output, "w", encoding="utf-8") as f:
            for t in tweets:
                f.write(json.dumps(t, ensure_ascii=False) + "\n")
        print(f"Saved to {output}")
    else:
        for i, t in enumerate(tweets):
            favs = t["favorite_count"]
            text = t["full_text"].replace("\n", " ")[:80]
            print(f"{i+1:3d}. ❤️{favs:5d} | {t['created_at'][:20]} | {text}...")


if __name__ == "__main__":
    main()
