# Destiny 2 Bright Dust Checker — Project Handoff

This guide is for anyone taking over the Destiny 2 Bright Dust Checker: a Python app that reads current vendor offers from the Bungie API, filters for Bright Dust purchases, and displays them in a small web dashboard.

## Project status

- The project source is in the public repository: [FormidableForce/bright-dust-checker](https://github.com/FormidableForce/bright-dust-checker).
- The local dashboard has been run successfully at `http://127.0.0.1:8765`.
- No hosted Render deployment or shareable hosted URL has been created yet. The checked-in Render Blueprint is deployment configuration, not a live service.
- The dashboard shows all vendors together, with an item/vendor search field and no vendor dropdown.
- The vendor API may return entries whose names cannot be resolved from the Bungie manifest. Those are shown as `Unknown <vendor hash>`; this is a naming limitation, not an additional filter.

## What the app includes

- Live vendor sale retrieval using the signed-in Bungie account.
- Bright Dust-only filtering (currency hash `2817410917`).
- Exclusion of package/bundle items and item names containing `Decryption`.
- No special exclusion for shaders or emotes; they appear when currently offered for Bright Dust.
- A local web page with current prices, vendor names, item search, and refresh.
- Optional watchlist matching and push notifications through ntfy.sh.

Sales change with Bungie's rotation. An item not appearing today may simply not be for sale now.

## Files

| File | Purpose |
| --- | --- |
| `all_vendors.py` | Main command entry point. Enables the all-vendor filter and dispatches commands. |
| `destiny_dust.py` | Bungie OAuth/API access, shared Bright Dust filtering, notifications, and web server. |
| `index.html` | Dashboard interface served by the Python app. |
| `config.example.json` | Safe template for local Bungie configuration. |
| `watchlist.example.txt` | Safe template for notification watch terms. |
| `render.yaml` | Render Blueprint for a paid web service with a private persistent disk. |
| `.gitignore` | Keeps local credentials, tokens, caches, and user state out of Git. |

Personal `config.json`, `tokens.json`, `watchlist.txt`, cache files, and notification state are private local data; they are intentionally not included in the public project.

## Run locally (Windows PowerShell)

1. Install Python 3.
2. In PowerShell, enter the project directory:

   ```powershell
   Set-Location "D:\path\to\bright-dust-checker"
   ```

   Replace the example path with the folder where the project is checked out.
3. Install the only third-party Python dependency:

   ```powershell
   python -m pip install requests
   ```
4. Create local configuration and edit it with your own Bungie credentials:

   ```powershell
   Copy-Item config.example.json config.json
   notepad config.json
   ```

   Fill in `api_key`, `client_id`, and `client_secret`. `ntfy_topic` is optional. Never send this file to another person or commit it.
5. Authenticate the Bungie account that should supply vendor data:

   ```powershell
   python all_vendors.py setup
   ```

   Follow the printed Bungie authorization URL, approve access, then paste the `code` value from the redirected address bar into the terminal prompt. The resulting `tokens.json` contains private, refreshable account tokens. Keep it private. Re-run setup if the refresh token expires.
6. Start the dashboard:

   ```powershell
   python all_vendors.py web
   ```

   Open `http://127.0.0.1:8765` if it does not open automatically. Stop the server with **Ctrl+C**.

The sample Bungie application setup expects a confidential OAuth client, a `https://localhost` redirect URL, and the Vendors/Advisors scope. Use the Bungie application page at https://www.bungie.net/en/Application. Each operator should authorize their own account; do not transfer someone else's token file.

## Commands

Run these from the project directory:

```text
python all_vendors.py setup   # Bungie OAuth login; saves tokens.json
python all_vendors.py list    # print current eligible sales grouped by vendor
python all_vendors.py check   # notify for new watchlist matches
python all_vendors.py loop    # repeat the notification check hourly
python all_vendors.py web     # run/open the local dashboard
```

For notifications, copy `watchlist.example.txt` to `watchlist.txt` and add one item name or partial name per line. Matching is case-insensitive. Set `ntfy_topic` in `config.json` (or `NTFY_TOPIC` in the environment) to enable ntfy notifications. Without a topic, the `check` command reports a configuration error.

The app can also read Bungie credentials from `BUNGIE_API_KEY`, `BUNGIE_CLIENT_ID`, and `BUNGIE_CLIENT_SECRET` environment variables. Environment values take precedence over corresponding values in `config.json`.

## Deploy privately on Render (not yet completed)

`render.yaml` configures a paid Render Starter web service, starts `python all_vendors.py web`, and mounts a private persistent disk at `/var/data`. Persistent disks require a paid Render service.

1. Connect the public GitHub repository to Render and deploy its Blueprint.
2. In Render's environment settings, set secret values for `BUNGIE_API_KEY`, `BUNGIE_CLIENT_ID`, `BUNGIE_CLIENT_SECRET`, `DUST_WEB_USER`, and a strong `DUST_WEB_PASSWORD`. Set `NTFY_TOPIC` only if notifications are wanted. Do not put secrets in source files, commits, or chat.
3. Confirm the Blueprint's `DUST_WEB_HOST=0.0.0.0` and `DUST_DATA_DIR=/var/data` settings and allow Render to provide the web port through `PORT`.
4. In the Render service Shell, run:

   ```sh
   python all_vendors.py setup
   ```

   Open the authorization URL in your own browser, approve it, and paste the returned code into the Shell prompt. This creates the token file under the persistent data directory so refreshes survive service restarts.
5. Open the HTTPS service URL Render provides and verify that the dashboard prompts for the configured username/password and displays current sales. Share the URL and password separately, not in the repository.

The app refuses to bind to a non-local interface unless both `DUST_WEB_USER` and `DUST_WEB_PASSWORD` are set. Basic authentication does not provide transport encryption by itself; use a host that terminates HTTPS and do not expose the local HTTP server directly to the internet.

## Security and account handoff

- Never publish or share `config.json`, `tokens.json`, `.env` files, OAuth authorization codes, or the dashboard password. The public repository contains only example configuration.
- Before handing over ownership, have the recipient create/use their own Bungie credentials and authorize their own account. Revoke old app access and rotate credentials if they should no longer be trusted.
- Bungie credentials were previously present in source history before being moved to local configuration. Because Git history can retain old values, rotate any Bungie API key or OAuth client secret that may have been exposed; rotation has not been verified here.
- Keep the Render disk private and persistent. Back up account data only through a secure, private method, and remove access when it is no longer needed.
- Review `.gitignore` before adding files or publishing changes. Do not force-add ignored secret or personal-data files.

## Troubleshooting and known limits

- **Missing Bungie configuration:** create `config.json` from `config.example.json`, or set all three required Bungie environment variables.
- **Not logged in / expired login:** run `python all_vendors.py setup` again using the account that should be queried.
- **No listings:** check the Bungie account authorization and try `python all_vendors.py list`. Offers are rotation-dependent.
- **Vendor shown as `Unknown <hash>`:** the manifest lookup did not provide a display name for that vendor. The app can still show its sale entries.
- **Dashboard returns an error:** inspect the terminal or Render service logs; API and manifest errors are logged there.
- **A shader or emote is missing:** the app does not filter those item categories out, but only currently sold Bright Dust entries can appear.
