# Destiny 2 Bright Dust Checker

A local-first Bright Dust tracker and private-shareable dashboard for Tess Everis sales. It excludes bundles and any item with "Decryption" in its name.

## Setup

1. Create a Bungie application at https://www.bungie.net/en/Application with a confidential OAuth client, `https://localhost` redirect URL, and Vendors/Advisors scope.
2. Copy `config.example.json` to `config.json` and fill in your API key, OAuth client ID, OAuth client secret, and optional ntfy topic. **Never commit `config.json`.**
3. Install Python 3 and `requests`: `python -m pip install requests`
4. Sign in once: `python destiny_dust.py setup`. The private OAuth tokens are saved locally in `tokens.json`; do not share or commit this file.

## Commands

- `python destiny_dust.py list` — list Tess Everis items sold for Bright Dust.
- `python destiny_dust.py check` — notify for new watchlist matches.
- `python destiny_dust.py loop` — check every hour.
- `python destiny_dust.py web` — start the local dashboard at http://127.0.0.1:8765.

Create `watchlist.txt` (or copy `watchlist.example.txt`) with one partial item name per line. The local dashboard has item search.

## Private hosted dashboard

The app binds to localhost by default. To make it reachable through a hosting provider, set `DUST_WEB_HOST=0.0.0.0`, `DUST_WEB_PORT` to the port assigned by the provider, and set both `DUST_WEB_USER` and a strong `DUST_WEB_PASSWORD`. The dashboard enforces HTTP Basic authentication when those credentials are set and refuses non-local binding without them.

Use a provider that terminates HTTPS and keep Bungie and dashboard credentials in its secret/environment-variable settings. The host also needs the authorized Bungie `tokens.json` in private persistent storage; never place it in the repository or a public image. Keep the token store private and persistent so refresh tokens survive restarts. Do not share the dashboard password in the public repository.

### Deploying to Render

Use the included `render.yaml` Blueprint. It creates a paid Starter web service and a private persistent disk at `/var/data`; persistent disks require a paid Render service. In Render's environment settings, provide `BUNGIE_API_KEY`, `BUNGIE_CLIENT_ID`, `BUNGIE_CLIENT_SECRET`, `DUST_WEB_USER`, and a strong `DUST_WEB_PASSWORD`. `NTFY_TOPIC` is optional.

After deploy, open the service Shell and run `python destiny_dust.py setup`. Open the printed Bungie authorization URL in your own browser, approve it, and paste the returned code into the Shell prompt. This stores `tokens.json` on the private disk. The service URL then prompts for the dashboard username and password.

## Private files

`.gitignore` excludes `config.json`, `tokens.json`, `.env`, caches, and personal watchlist/state files. Publish only the example config and example watchlist, never real account data.
