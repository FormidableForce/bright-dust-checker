# Destiny 2 Bright Dust Checker

A local-first Bright Dust tracker and password-protected dashboard showing eligible sales across all vendors. Any sale paid for with Bright Dust is included, including shaders and emotes; packages/bundles and items named "Decryption" are excluded. The dashboard shows all vendors together, with search and no vendor dropdown.

## Setup

1. Create a Bungie app at https://www.bungie.net/en/Application with a confidential OAuth client, `https://localhost` redirect URL, and Vendors/Advisors scope.
2. Copy `config.example.json` to `config.json` and add your Bungie API key, OAuth client ID and secret. `ntfy_topic` is optional. Never commit `config.json`.
3. Install Python 3 and `requests`: `python -m pip install requests`.
4. Run `python all_vendors.py setup`, sign in to Bungie and enter the returned code in your terminal. `tokens.json` is private; never share or commit it.

## Commands

- `python all_vendors.py list` — list eligible Bright Dust sales grouped by vendor.
- `python all_vendors.py check` — send notifications for new watchlist matches.
- `python all_vendors.py loop` — check hourly.
- `python all_vendors.py web` — open the local dashboard at http://127.0.0.1:8765.

Create `watchlist.txt` (copy `watchlist.example.txt`) with one partial item name per line. The dashboard includes all vendors and filters items/vendors with a search box.

## Private Render deployment

The included `render.yaml` Blueprint creates a paid Starter web service and private persistent disk at `/var/data` (Render persistent disks require a paid service). Connect this public repository in Render. Set `BUNGIE_API_KEY`, `BUNGIE_CLIENT_ID`, `BUNGIE_CLIENT_SECRET`, `DUST_WEB_USER`, and a strong `DUST_WEB_PASSWORD` in Render's environment settings—never in this repository. Configure the Bungie application redirect URL if OAuth requires a hosted callback; the current setup flow asks you to paste the code into Render's service Shell.

After deploy, use the Render service Shell to run `python all_vendors.py setup`, open its printed authorization URL, approve the app, and paste the code into the Shell. The OAuth token will be stored on the private disk. Render provides the HTTPS dashboard URL; it asks friends for the dashboard username and password. Share the password separately, not in the public repository.

## Private files

`.gitignore` excludes `config.json`, token files, `.env*`, caches, watchlist and state. Publish only example files, never account data.
