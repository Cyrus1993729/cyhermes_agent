# -*- coding: utf-8 -*-
"""Tavily search helper - direct API (bypasses unregistered web_search tool)"""
import json, urllib.request, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
from hermes_cli.config import get_env_value

def tavily_search(query, max_results=10, depth="advanced"):
    key = get_env_value('TAVILY_API_KEY')
    req = urllib.request.Request(
        'https://api.tavily.com/search',
        data=json.dumps({'api_key': key, 'query': query, 'max_results': max_results, 'search_depth': depth}).encode('utf-8'),
        headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=40) as r:
        return json.load(r)

def show(q, n=10):
    d = tavily_search(q, n)
    print(f"### {q}  ({len(d.get('results', []))} results)")
    for x in d.get('results', []):
        print("-", x.get('title'))
        print(" ", x.get('url'))
        print(" ", (x.get('content') or '')[:220].replace('\n', ' '))
    print()

if __name__ == '__main__':
    for q in sys.argv[1:]:
        try:
            show(q)
        except Exception as e:
            print(f"ERR {q}: {e}")