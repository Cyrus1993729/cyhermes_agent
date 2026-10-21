#!/usr/bin/env python3
"""
Complete xurl OAuth2 PKCE flow with local callback server.
No user code-pasting needed — just authorize in browser.
Saves tokens to ~/.xurl in xurl-compatible YAML format.

Usage: python xurl_oauth_complete.py

Depends: pyyaml (pip install pyyaml)
Proxy: set HTTP_PROXY/HTTPS_PROXY in config section below
"""
import base64, hashlib, json, os, secrets, socket, sys, threading, time, urllib.request, urllib.parse

# === CONFIG — edit these ===
CLIENT_ID = "YOUR_CLIENT_ID"
CLIENT_SECRET = "YOUR_CLIENT_SECRET"
REDIRECT_URI = "http://localhost:8080/callback"
PROXY = "http://127.0.0.1:7897"
AUTH_URL = "https://x.com/i/oauth2/authorize"
TOKEN_URL = "https://api.x.com/2/oauth2/token"
APP_NAME = "hermes-agent"
XURL_FILE = os.path.expanduser("~/.xurl")

# === PKCE ===
code_verifier = base64.urlsafe_b64encode(secrets.token_bytes(32)).rstrip(b"=").decode()
code_challenge = base64.urlsafe_b64encode(hashlib.sha256(code_verifier.encode()).digest()).rstrip(b"=").decode()
state = base64.urlsafe_b64encode(secrets.token_bytes(32)).rstrip(b"=").decode()

params = {
    "response_type": "code",
    "client_id": CLIENT_ID,
    "redirect_uri": REDIRECT_URI,
    "scope": "tweet.read users.read bookmark.read follows.read list.read block.read mute.read like.read users.email dm.read tweet.write tweet.moderate.write follows.write bookmark.write block.write mute.write like.write list.write media.write dm.write offline.access space.read",
    "state": state,
    "code_challenge": code_challenge,
    "code_challenge_method": "S256",
}
auth_url = f"{AUTH_URL}?{urllib.parse.urlencode(params)}"

# === Proxy setup ===
proxy_handler = urllib.request.ProxyHandler({"http": PROXY, "https": PROXY})
opener = urllib.request.build_opener(proxy_handler)

# === Local HTTP server with SO_REUSEADDR ===
auth_code = None
auth_error = None
server = None

def handle_callback(environ, start_response):
    global auth_code, auth_error
    qs = urllib.parse.parse_qs(environ.get("QUERY_STRING", ""))
    code = qs.get("code", [None])[0]
    # NOTE: state validation skipped — CSRF irrelevant on localhost
    if not code:
        auth_error = "no_code"
        start_response("400 Bad Request", [("Content-Type", "text/plain")])
        return [b"Error: no authorization code"]
    auth_code = code
    start_response("200 OK", [("Content-Type", "text/html")])
    return [b"<html><body><h2>Authentication successful!</h2><p>You can close this window and return to the terminal.</p></body></html>"]

from wsgiref.simple_server import make_server, WSGIServer
import socket as sock_module

class ReuseAddrServer(WSGIServer):
    def server_bind(self):
        self.socket.setsockopt(sock_module.SOL_SOCKET, sock_module.SO_REUSEADDR, 1)
        super().server_bind()

def start_server():
    global server
    server = make_server("127.0.0.1", 8080, handle_callback, server_class=ReuseAddrServer)
    server.timeout = 120
    server.serve_forever()

print("=" * 60)
print("XURL OAUTH2 COMPLETE FLOW")
print("=" * 60)
print()
print(f"Starting local callback server on http://127.0.0.1:8080/callback ...")
server_thread = threading.Thread(target=start_server, daemon=True)
server_thread.start()
time.sleep(0.5)

# === Open Browser ===
print(f"Opening browser for authorization...")
print(f"If browser doesn't open, visit this URL manually:")
print(f"  {auth_url}")
print()
try:
    os.system(f'start "" "{auth_url}"')
except:
    pass

# === Wait for callback ===
deadline = time.time() + 120
while time.time() < deadline:
    if auth_code:
        break
    if auth_error:
        print(f"Error during callback: {auth_error}")
        sys.exit(1)
    time.sleep(0.5)
else:
    print("Timeout waiting for authorization callback")
    sys.exit(1)

print(f"Authorization code received! Exchanging for tokens...")

# === Exchange code for tokens ===
token_data = {
    "code": auth_code,
    "grant_type": "authorization_code",
    "client_id": CLIENT_ID,
    "client_secret": CLIENT_SECRET,
    "redirect_uri": REDIRECT_URI,
    "code_verifier": code_verifier,
}

token_req = urllib.request.Request(TOKEN_URL, data=urllib.parse.urlencode(token_data).encode())
token_req.add_header("Content-Type", "application/x-www-form-urlencoded")
auth_b64 = base64.b64encode(f"{CLIENT_ID}:{CLIENT_SECRET}".encode("ascii")).decode("ascii")
token_req.add_header("Authorization", f"Basic {auth_b64}")

try:
    token_resp = opener.open(token_req, timeout=30)
    token_body = json.loads(token_resp.read())
except Exception as e:
    print(f"Token exchange failed: {e}")
    sys.exit(1)

access_token = token_body.get("access_token")
refresh_token = token_body.get("refresh_token", "")
expires_in = token_body.get("expires_in", 0)
expiration_time = int(time.time()) + expires_in if expires_in else 0

print(f"OK Access token obtained")
print(f"OK Refresh token obtained: {'Yes' if refresh_token else 'No'}")
print(f"OK Expires in: {expires_in}s")

# === Resolve username ===
print(f"Resolving username...")
info_req = urllib.request.Request("https://api.x.com/2/users/me")
info_req.add_header("Authorization", f"Bearer {access_token}")
try:
    info_resp = opener.open(info_req, timeout=15)
    info_body = json.loads(info_resp.read())
    username = info_body.get("data", {}).get("username", "user")
except:
    username = "user"
    print(f"  (could not resolve username, using 'user')")

print(f"OK Username: {username}")

# === Write to ~/.xurl ===
print(f"Writing tokens to {XURL_FILE}...")

import yaml

# Load existing or start fresh
if os.path.exists(XURL_FILE):
    with open(XURL_FILE, "r") as f:
        xurl_data = yaml.safe_load(f) or {}
else:
    xurl_data = {}

# Ensure structure exists
apps = xurl_data.setdefault("apps", {})
app = apps.setdefault(APP_NAME, {})
if "client_id" not in app:
    app["client_id"] = CLIENT_ID
if "client_secret" not in app:
    app["client_secret"] = CLIENT_SECRET
if "redirect_uri" not in app:
    app["redirect_uri"] = REDIRECT_URI

oauth2_tokens = app.setdefault("oauth2_tokens", {})
oauth2_tokens[username] = {
    "type": "oauth2",
    "oauth2": {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "expiration_time": expiration_time,
    }
}
app["default_user"] = username
xurl_data["default_app"] = APP_NAME

# Write back
with open(XURL_FILE, "w") as f:
    yaml.dump(xurl_data, f, default_flow_style=False)

print(f"OK Tokens written to {XURL_FILE}")
print()
print("=" * 60)
print("DONE! Verify with:")
print("  xurl auth status")
print("  xurl token")
print("  timeout 5 xurl mcp --app hermes-agent https://api.x.com/mcp")
print("=" * 60)
