# op-and-chloe

<p align="center">
  <img src="assets/logo.png" alt="Op and Chloe" width="400">
</p>

`op-and-chloe` ("openclaw-ey") is a two-instance OpenClaw stack for any VPS.

- **🐕 Op**: admin instance with SSH access — fix Chloe, restarts, large architectural changes
- **🐯 Chloe**: day-to-day instance — create all agents here; has Bitwarden, email, M365, webtop
- 🖥️ Webtop Chromium + CDP for shared browser (you + Chloe)
- 🔐 Passwordless: Bitwarden in Chloe; login/unlock interactive only, no secrets in files
- ❤️ Healthcheck + watchdog

> 🚀 Easiest setup ever: just run `sudo ./setup.sh` and you’re on your way! 🎉

## But why?

Why do you need this?  
Why not just use OpenClaw as it is?  

You can - and you should. OpenClaw is awesome.

Setting it up from start to finish can be very tedious, though. How do you securely share credentials? How do you give OpenClaw browser access - especially on a headless server? Should you use Browserless or run headless Chromium? If you can't see the browser, how do you log in? How do you troubleshoot or fix things from your phone? And how do you help someone set up OpenClaw if they're not comfortable with SSH or the command line?

I created `op-and-chloe` to make this process easier.  
It's not a framework, not a lock-in, **it's a simple wizard** to pre-configure your stack to get you started. **Once up and running, you can change it completely**.

It looks like this:

<p align="center">
  <img src="assets/wizard.png" alt="OpenClaw Setup Wizard" width="600">
</p>


**What you get out of the box:**

- **☁️ A working stack on any VPS.** I use [Hetzner](https://www.hetzner.com), it's **~$4.70/month** and runs the full stack really well - but you can use any VPS provider. See [HETZNER.md](./HETZNER.md).

- **📱 Two Telegram chats.** One for Op (admin, fixing Chloe, restarts); one for Chloe (day-to-day — create all agents here).

- **🔒 Private access via Tailscale.** Guard, worker, and Webtop are on your Tailscale network with optional HTTPS - no public ports. Use them from your phone or laptop.

- **🌐 Static site publishing from Chloe.** Publish multiple sites from `workspace/sites/` using a single validated registry picked up by the proxy.

- **❤️ Health Check.** Scripts to configure, verify and keep your stack healthy.

- **🔑 Passwordless credentials** Bitwarden runs in Chloe’s container. Login and unlock are interactive only; no secrets stored in files.


---


## Quick start

After purchasing your VPS from a provider, SSH into your server and follow the setup wizard step-by-step. No advanced technical skills required - just run each guided step **in order**. The wizard makes it easy: after each action, you’ll return to the menu so you can check your progress before moving on.

```bash
git clone https://github.com/mere/op-and-chloe.git
cd op-and-chloe
sudo ./setup.sh
```

That's it!
<p align="center">
  <img src="assets/highfive.png" alt="OpenClaw Setup Wizard" height="300">
</p>
It takes about 20 minutes to follow the steps and your `AI personal assistant` is ready! ✨

## How to update

To update your op-and-chloe stack: run `git pull`, then run the setup again. The wizard will show you if anything needs updating.

```bash
cd op-and-chloe   # or wherever you cloned the repo
git pull
sudo ./setup.sh
```

# Components

The stack consists of:
- **Three Docker containers:**
  - **🐕 Op**: admin instance with SSH access. For fixing Chloe, restarts, and large architectural changes.
  - **🐯 Chloe**: day-to-day instance. Create all agents here. Has Bitwarden, email (Himalaya, M365), and webtop.
  - **🖥️ Webtop**: shared browser for you and Chloe (co-working, automation).

---

<p align="center">
  <img src="assets/chloe.png" alt="OpenClaw Setup Wizard" height="200">
</p>

### 1. Chloe

**Chloe** *(claw-y)* is your first OpenClaw instance.  
(You can name her/him/they/it anything; it will ask for a name once it's up and running. 😊)

This is your day-to-day instance. Create all agents here. You get Bitwarden, email (Himalaya, M365), and webtop — standard OpenClaw; add skills and agents as you like.

Chloe can also publish static sites from her workspace. Put the built outputs under `sites/`, register them in `sites/sites.json`, and the proxy will pick them up automatically.

When things break or you need restarts or big changes, talk to Op (admin with SSH access). Talk to Chloe for daily work.

**Bun (optional):** Chloe’s worker image ships with [Bun](https://bun.sh). The stack does not require it for a minimal setup. **`bun` and `bunx` are symlinked into `/usr/local/bin`** so OpenClaw’s agent shell (short allowlist `PATH` with `/usr/local/bin`, not Bun’s install dir) can run them.

**QMD (OpenClaw memory):** The worker image installs **`@tobilu/qmd`** with Bun and symlinks **`qmd` → `/usr/local/bin/qmd`**, so the gateway finds the same binary as agent shells. The worker entrypoint creates **`~/.openclaw/agents/<agent>/qmd/xdg-cache/qmd`** (including `main`) on the mounted state volume so SQLite can open the index. After rebuilding the worker image, run **`openclaw memory index --force`** once if a previous run left a bad or missing index.

---
<p align="center">
  <img src="assets/op.png" alt="OpenClaw Setup Wizard" height="200">
</p>

### 2. Op

**Op** is the admin instance with **SSH access**. Op’s job is to:
- fix Chloe when she breaks,
- do restarts, Docker, repo, and host changes,
- handle large architectural changes (whatever you’d otherwise SSH in to do).

You talk to Chloe for day-to-day work (create all agents there). You talk to Op when you need admin. 

---

<p align="center">
  <img src="assets/browser.png" alt="OpenClaw Setup Wizard" height="200">
</p>

### 3. Browser access

On a Mac mini, you can easily give OpenClaw access to a browser. On a headless VPS that's harder: headless browsers or services like Browserless can be detected by some sites, and you can't easily *see* what the agent is doing. Ideally you want to **co-work**: you log in to LinkedIn, ask the agent to check messages and draft replies; the agent fills a form, you review and submit.

op-and-chloe gives you that: a small Docker image with a browser that both you and Chloe share. You log in once; Chloe uses the same session.

---
<p align="center">
  <img src="assets/bitwarden.png" alt="OpenClaw Setup Wizard" height="200">
</p>

### 4. Credentials

All secrets, tokens, and passwords are stored securely in Bitwarden — never on the server itself. During setup, you'll connect your Bitwarden vault to Chloe (worker) and unlock it interactively when needed; only the vault URL and session key are stored in worker state. Chloe uses the **`bw`** script to read from the vault for email setup, O365 config, and other tools. 


---
<p align="center">
  <img src="assets/cli.png" alt="OpenClaw Setup Wizard" height="200">
</p>

## CLI Commands

Run the setup wizard:
```bash
sudo ./setup.sh
```

Is your AI about to take over the world? Stop the containers with:
```bash
sudo ./stop.sh
```

False alarm, it was just ordering cat food? Start it with:  
> Note: This also rebuilds the containers, so it's a good way to reset if things go wrong!
```bash
sudo ./start.sh
```


Run full health check on the stack:
```bash
sudo ./healthcheck.sh
```

Run a manual backup now:
```bash
sudo ./scripts/host/daily-backup.sh --force
```

To run any `openclaw` command, use:
```bash
./openclaw-guard some command
# or
./openclaw-worker some command
```

## Daily backups

Use setup step `16. daily backups` to toggle scheduled backups, run a one-off backup immediately, and choose where the compressed archives are stored.

- Default: disabled
- Schedule: once per day at `03:17` server time via `/etc/cron.d/openclaw-daily-backup`
- Default backup directory: a sibling `backups/` folder next to the stack checkout, for example `/opt/backups/op-and-chloe`
- Default retention: keep the last `30` backups
- Retention `0` means keep all backups with no pruning
- Archive contents: `/etc/openclaw`, Chloe's `state`, and Chloe's `workspace`
- Manual run: `sudo ./scripts/host/daily-backup.sh --force`

## Sites publishing

Use setup step `17. sites publishing` to enable or disable public site publishing without editing env files by hand.

- Default: disabled
- When enabled, the setup wizard asks for `SITES_BASE_DOMAIN` such as `sites.example.com`
- The wizard creates `workspace/sites/sites.json` automatically if it is missing
- Chloe publishes by adding entries to `workspace/sites/sites.json`
- Existing published site files are kept when you disable the feature


## System diagram

```mermaid
flowchart LR
  U[User]
  BW[(Bitwarden)]
  subgraph VPS["VPS"]
 
    subgraph Chloe["OpenClaw Docker"]
      A[Agents 🤖 🤖 🤖]
    end
    subgraph OPD["OpenClaw Docker"]
      Op["🐕 Op (Admin)"]
    end
    
    subgraph Docker[Webtop Docker]
      B["🖥️  Webtop"]
    end
    D[Docker / Host / Repo access]
  end

  U --> Chloe
  Op --> D
  A --> B
  A --> BW
  A --> E[💌 Email<br />📆 Calendar]
  U --> Op
  B --> S[🔷 Linkedin<br /> 💎 Social Media]
  
```

## Architecture

See the **System diagram** and **Components** section above for topology and roles.


## Bitwarden in Chloe

Chloe has **Bitwarden** in her container. She uses **`bw`** (e.g. `bw list items`, `bw get item <id>`) to read from the vault; session lives in worker state. One-time setup: scripts/worker/email-setup.py, scripts/worker/fetch-o365-config.py.

```bash
# In Chloe: Bitwarden runs locally
bw list items
bw get item <id>

# Email and M365 (after one-time setup)
himalaya envelope list -a icloud -s 20 -o json
m365 mail list --top 20
```

## Docs

- **OpenClaw Web (Control UI, bind modes, Tailscale):** [https://docs.openclaw.ai/web](https://docs.openclaw.ai/web)

## Publishing sites

Published sites live in Chloe's workspace under `sites/`, with one registry file at `sites/sites.json`.

Use setup step `17. sites publishing` to turn the proxy on or off and set the base domain.

Example:

```text
sites/
  sites.json
  hello/
    dist/
      index.html
  docs/
    build/
      index.html
```

`sites/sites.json`:

```json
{
  "sites": [
    {
      "name": "hello",
      "subdomain": "hello",
      "root": "hello/dist",
      "spa": true
    },
    {
      "name": "docs",
      "subdomain": "docs",
      "root": "docs/build"
    }
  ]
}
```

- Set `SITES_BASE_DOMAIN` in `/etc/openclaw/stack.env`, for example `sites.example.com`.
- Point wildcard DNS such as `*.sites.example.com` at the VPS.
- Restart the stack after changing env or proxy settings: `sudo ./start.sh`
- All `root` paths are relative to `workspace/sites/`.
- Each `root` must point to a subdirectory inside `workspace/sites/`, not `workspace/sites/` itself.
- Published trees must not contain symlinks.
- Chloe should only write the registry and site files under `workspace/sites/`; she should not write raw proxy config.

### Public access and passwords

Published URLs are **world-readable** by default: anyone who knows `https://<subdomain>.<your-base-domain>` can load the static files. That is appropriate for marketing pages, demos, and shareable tools.

To limit who can view a site:

1. **Leave sites publishing disabled** in setup until you are ready to go public, or remove the entry from `sites/sites.json` to take a site down without disabling the whole feature.
2. **App-level auth** — For SPAs and mini-apps, add your own sign-in (OAuth, magic links, etc.) in the front end or a small backend you deploy separately. The stack only serves static files from `sites/`.
3. **HTTP Basic Auth (per site)** — Optional `basicauth` on each entry in `sites/sites.json`: set `user` and `bcrypt` (a modular-crypt hash from `caddy hash-password`, e.g. on the host: `docker compose --profile sites exec site-proxy caddy hash-password`). Only the hash is stored in the registry — never a plaintext password.

## Troubleshooting

**`./openclaw-guard devices list` (or worker) shows "device token mismatch":**
- The container was started with an old gateway token. Recreate so they pick up the current env file: `sudo ./stop.sh && sudo ./start.sh` (wait ~90s for gateways to be ready, then try again).

**Dashboard URLs (Guard/Worker) return HTTP 502 after `stop.sh` / `start.sh`:**
- The gateways can take 60–90 seconds to start listening. `start.sh` now waits for them before applying Tailscale serve. If you still see 502, wait a minute and refresh, or re-run: `sudo ./scripts/host/apply-tailscale-serve.sh`

**Chloe's browser tool shows wrong URL or cdpReady: false:**
- The worker state must point at the browser container's CDP endpoint. On every `start.sh` we refresh it automatically. To fix immediately: `sudo ./scripts/host/update-webtop-cdp-url.sh` (then use the worker dashboard or reconnect so Chloe picks up the new config).

**Webtop URL (https://hostname:445/) not working:**
1. Ensure the browser container is running: `docker ps | grep browser`
2. Ensure Tailscale serve is configured: `tailscale serve status`  -  you should see port 445 → 127.0.0.1:6080
3. Re-apply serve config: `sudo ./scripts/host/apply-tailscale-serve.sh`
4. For HTTPS to work, enable [HTTPS certificates](https://tailscale.com/kb/1153/enabling-https) in the admin console and run `sudo tailscale cert` on the VPS

**Published site not appearing on its subdomain:**
1. Ensure `SITES_BASE_DOMAIN` is set in `/etc/openclaw/stack.env`
2. Ensure wildcard DNS for `*.your-base-domain` points at the VPS
3. Ensure `workspace/sites/sites.json` exists and contains the site entry
4. Ensure `root` points to an existing directory inside `workspace/sites/`
5. Ensure the published tree does not contain symlinks
6. Check the `site-proxy` and `sites-reconciler` containers with `docker compose ps`

**`site-proxy` fails to start: `bind ... 0.0.0.0:443: address already in use` (or nothing listens on public :80/:443):**
- Tailscale often binds HTTPS on the tailnet interface (`tailscaled` on `100.x.x.x:443`). That blocks Docker from publishing `0.0.0.0:443` for Caddy even though your public IP looks free.
- Set `SITES_HTTP_HOST` and `SITES_HTTPS_HOST` in `/etc/openclaw/stack.env` to your VPS’s **public IPv4** (the address wildcard DNS should use), then recreate the proxy:  
  `docker compose --env-file /etc/openclaw/stack.env -f compose.yml --profile sites up -d site-proxy`  
  (from your stack directory, e.g. where you cloned this repo).

**`site-proxy` logs `Import file is empty`, or HTTPS only works after restarting `site-proxy`:**  
If `sites.generated.caddy` on the host has content but Caddy inside the container sees an empty file, you likely have an old **single-file** bind mount. The reconciler replaces that file atomically; Docker can leave the container on a stale inode. Use the current `compose.yml` (directory mount at `/etc/caddy/sites-registry/`) and recreate:  
`docker compose --env-file /etc/openclaw/stack.env -f compose.yml --profile sites up -d --force-recreate site-proxy`

## Security model

- **No master password on disk:** In setup step 6 you log in and unlock once; only `BW_SERVER` and the session key are saved (worker state: `state/secrets/bitwarden.env`, `state/secrets/bw-session`). Chloe uses that session via **`bw`**; re-run step 6 if the vault is locked.
- Bitwarden runs in Chloe’s container; she has `bw` in PATH.

## License

This project is licensed under the [MIT License](LICENSE).

## Contributing

Contributions are welcome. See [CONTRIBUTING.md](CONTRIBUTING.md) for how to get started.
