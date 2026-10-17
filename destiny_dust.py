"""Destiny 2 Tess Everis Bright Dust tracker and dashboard.

Usage:
    python destiny_dust.py setup     # one-time Bungie login
    python destiny_dust.py list      # print eligible Tess Everis sales
    python destiny_dust.py check     # notify for new watchlist matches
    python destiny_dust.py loop      # check every 60 minutes
    python destiny_dust.py web       # open the local dashboard
"""
import hmac
import json
import os
import sys
import time
import webbrowser
from base64 import b64decode
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

import requests

BASE = "https://www.bungie.net/Platform"
AUTH_URL = "https://www.bungie.net/en/OAuth/Authorize"
TOKEN_URL = f"{BASE}/app/oauth/token/"
BRIGHT_DUST = 2817410917

HERE = Path(__file__).parent
CONFIG = HERE / "config.json"
TOKENS = HERE / "tokens.json"
WATCHLIST = HERE / "watchlist.txt"
SEEN = HERE / "seen.json"
CACHE = HERE / "name_cache.json"
ITEM_CACHE = HERE / "item_cache.json"

cache = json.loads(CACHE.read_text()) if CACHE.exists() else {}
item_cache = json.loads(ITEM_CACHE.read_text()) if ITEM_CACHE.exists() else {}


def load_config():
    cfg = json.loads(CONFIG.read_text(encoding="utf-8")) if CONFIG.exists() else {}
    env_names = {
        "api_key": "BUNGIE_API_KEY",
        "client_id": "BUNGIE_CLIENT_ID",
        "client_secret": "BUNGIE_CLIENT_SECRET",
        "ntfy_topic": "NTFY_TOPIC",
    }
    for key, env_name in env_names.items():
        if os.getenv(env_name):
            cfg[key] = os.environ[env_name]
    required = ("api_key", "client_id", "client_secret")
    missing = [key for key in required if not cfg.get(key)]
    if missing:
        raise RuntimeError(
            "Missing Bungie configuration. Copy config.example.json to config.json "
            "and fill in the required values."
        )
    return cfg


def save_cache():
    CACHE.write_text(json.dumps(cache))


def save_item_cache():
    ITEM_CACHE.write_text(json.dumps(item_cache))


# ---------- auth ----------
def token_request(cfg, data):
    r = requests.post(
        TOKEN_URL,
        data=data,
        auth=(cfg["client_id"], cfg["client_secret"]),
        headers={"X-API-Key": cfg["api_key"]},
    )
    r.raise_for_status()
    t = r.json()
    t["expires_at"] = time.time() + t["expires_in"] - 60
    t["refresh_expires_at"] = time.time() + t["refresh_expires_in"] - 60
    TOKENS.write_text(json.dumps(t))
    return t


def setup():
    cfg = load_config()
    url = f"{AUTH_URL}?client_id={cfg['client_id']}&response_type=code"
    print("Opening Bungie login. After you approve, copy the value after 'code='")
    print("from the redirected address bar and paste it into this terminal.")
    webbrowser.open(url)
    code = input("Paste code: ").strip()
    token_request(cfg, {"grant_type": "authorization_code", "code": code})
    print("Logged in. Tokens saved locally.")


def get_access_token(cfg):
    if not TOKENS.exists():
        sys.exit("Not logged in. Run: python destiny_dust.py setup")
    t = json.loads(TOKENS.read_text())
    if time.time() < t["expires_at"]:
        return t["access_token"]
    if time.time() > t["refresh_expires_at"]:
        sys.exit("Login expired. Run: python destiny_dust.py setup")
    t = token_request(cfg, {"grant_type": "refresh_token", "refresh_token": t["refresh_token"]})
    return t["access_token"]


# ---------- api ----------
def api(cfg, path, auth=True, params=None):
    headers = {"X-API-Key": cfg["api_key"]}
    if auth:
        headers["Authorization"] = f"Bearer {get_access_token(cfg)}"
    r = requests.get(f"{BASE}{path}", headers=headers, params=params)
    r.raise_for_status()
    body = r.json()
    if body.get("ErrorCode") != 1:
        raise RuntimeError(f"Bungie error: {body.get('Message')}")
    return body["Response"]


def find_character(cfg):
    memberships = api(cfg, "/User/GetMembershipsForCurrentUser/")
    primary = memberships.get("primaryMembershipId")
    memberships_list = memberships["destinyMemberships"]
    membership = next(
        (item for item in memberships_list if item["membershipId"] == primary),
        memberships_list[0],
    )
    membership_type, membership_id = membership["membershipType"], membership["membershipId"]
    profile = api(
        cfg,
        f"/Destiny2/{membership_type}/Profile/{membership_id}/",
        params={"components": 200},
    )
    character_id = next(iter(profile["characters"]["data"]))
    return membership_type, membership_id, character_id


def name_of(cfg, kind, definition_hash):
    key = f"{kind}:{definition_hash}"
    if key not in cache:
        definition = api(cfg, f"/Destiny2/Manifest/{kind}/{definition_hash}/", auth=False)
        cache[key] = definition["displayProperties"]["name"] or f"Unknown {definition_hash}"
    return cache[key]


def item_definition(cfg, item_hash):
    key = str(item_hash)
    if key not in item_cache:
        item_cache[key] = api(
            cfg,
            f"/Destiny2/Manifest/DestinyInventoryItemDefinition/{item_hash}/",
            auth=False,
        )
    return item_cache[key]


def is_bundle(definition):
    return (
        definition.get("itemType") == 25
        or (definition.get("itemTypeDisplayName") or "").casefold() == "package"
    )


def get_dust_sales(cfg):
    """Return Tess Everis Bright Dust sales, excluding bundles and decryption items."""
    membership_type, membership_id, character_id = find_character(cfg)
    data = api(
        cfg,
        f"/Destiny2/{membership_type}/Profile/{membership_id}/Character/{character_id}/Vendors/",
        params={"components": 402},
    )
    sales = []
    for vendor_hash, vendor in data.get("sales", {}).get("data", {}).items():
        vendor_name = name_of(cfg, "DestinyVendorDefinition", vendor_hash)
        if vendor_name.casefold() != "tess everis":
            continue
        for sale in vendor.get("saleItems", {}).values():
            cost = next(
                (entry["quantity"] for entry in sale.get("costs", []) if entry["itemHash"] == BRIGHT_DUST),
                None,
            )
            if cost is None or cost <= 0:
                continue
            definition = item_definition(cfg, sale["itemHash"])
            if is_bundle(definition):
                continue
            properties = definition.get("displayProperties", {})
            item_name = properties.get("name") or f"Unknown {sale['itemHash']}"
            if "decryption" in item_name.casefold():
                continue
            sales.append(
                {
                    "vendor": vendor_name,
                    "item": item_name,
                    "cost": cost,
                    "icon": properties.get("icon", ""),
                    "description": properties.get("description", ""),
                }
            )
    save_cache()
    save_item_cache()
    return sales


# ---------- notifications ----------
def notify(cfg, title, message):
    if not cfg.get("ntfy_topic"):
        raise RuntimeError("Missing ntfy_topic in config.json.")
    response = requests.post(
        f"https://ntfy.sh/{cfg['ntfy_topic']}",
        data=message.encode("utf-8"),
        headers={"Title": title},
    )
    response.raise_for_status()


def load_watchlist():
    if not WATCHLIST.exists():
        return []
    return [
        line.strip().casefold()
        for line in WATCHLIST.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.startswith("#")
    ]


# ---------- commands ----------
def cmd_list():
    sales = get_dust_sales(load_config())
    if not sales:
        print("Nothing found for Bright Dust at Tess Everis right now.")
        return
    for sale in sorted(sales, key=lambda entry: entry["item"]):
        print(f"{sale['item']}: {sale['cost']} Bright Dust")


def cmd_check():
    cfg = load_config()
    watchlist = load_watchlist()
    seen = set(json.loads(SEEN.read_text())) if SEEN.exists() else set()
    sales = get_dust_sales(cfg)
    matches = [sale for sale in sales if any(term in sale["item"].casefold() for term in watchlist)]
    new_matches = [sale for sale in matches if f"{sale['vendor']}|{sale['item']}" not in seen]
    for sale in new_matches:
        notify(
            cfg,
            "Bright Dust sale",
            f"{sale['item']} is for sale at {sale['vendor']} for {sale['cost']} Bright Dust",
        )
        print(f"Notified: {sale['item']} ({sale['cost']} Bright Dust)")
    SEEN.write_text(json.dumps([f"{sale['vendor']}|{sale['item']}" for sale in matches]))
    if not new_matches:
        print(f"Checked {len(sales)} eligible items, no new watchlist matches.")


class TrackerHandler(BaseHTTPRequestHandler):
    def _is_authorized(self):
        username = os.getenv("DUST_WEB_USER")
        password = os.getenv("DUST_WEB_PASSWORD")
        if not username and not password:
            return True
        if not username or not password:
            return False
        try:
            scheme, encoded = self.headers.get("Authorization", "").split(" ", 1)
            if scheme.casefold() != "basic":
                return False
            provided = b64decode(encoded, validate=True).decode("utf-8")
            provided_user, provided_password = provided.split(":", 1)
        except (ValueError, UnicodeDecodeError):
            return False
        return hmac.compare_digest(provided_user, username) and hmac.compare_digest(
            provided_password, password
        )

    def do_GET(self):
        if not self._is_authorized():
            self.send_response(401)
            self.send_header("WWW-Authenticate", 'Basic realm="Bright Dust dashboard"')
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            return
        path = urlsplit(self.path).path
        if path == "/":
            content = (HERE / "index.html").read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.write(content)
            return
        if path != "/api/sales":
            self.send_error(404)
            return
        try:
            result = {
                "items": get_dust_sales(load_config()),
                "refreshed_at": datetime.now(timezone.utc).isoformat(),
            }
            payload = json.dumps(result).encode("utf-8")
            self.send_response(200)
        except Exception as exc:
            print(f"Unable to load Bright Dust sales: {exc}", file=sys.stderr)
            payload = json.dumps(
                {"error": "Unable to load current sales. Check the server logs."}
            ).encode("utf-8")
            self.send_response(502)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, format, *args):
        print(f"[web] {self.address_string()} - {format % args}")


def cmd_web():
    host = os.getenv("DUST_WEB_HOST", "127.0.0.1")
    port = int(os.getenv("DUST_WEB_PORT", "8765"))
    local_hosts = ("127.0.0.1", "localhost", "::1")
    if host not in local_hosts and not (
        os.getenv("DUST_WEB_USER") and os.getenv("DUST_WEB_PASSWORD")
    ):
        raise RuntimeError(
            "Remote dashboard binding requires DUST_WEB_USER and DUST_WEB_PASSWORD."
        )
    server = ThreadingHTTPServer((host, port), TrackerHandler)
    url = f"http://{host}:{port}"
    print(f"Bright Dust dashboard: {url}")
    print("Press Ctrl+C to stop the server.")
    if host in local_hosts:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nDashboard stopped.")
    finally:
        server.server_close()


def cmd_loop():
    while True:
        try:
            cmd_check()
        except Exception as exc:
            print("Error:", exc)
        time.sleep(60 * 60)


if __name__ == "__main__":
    commands = {
        "setup": setup,
        "list": cmd_list,
        "check": cmd_check,
        "loop": cmd_loop,
        "web": cmd_web,
    }
    if len(sys.argv) < 2 or sys.argv[1] not in commands:
        sys.exit(__doc__)
    commands[sys.argv[1]]()
