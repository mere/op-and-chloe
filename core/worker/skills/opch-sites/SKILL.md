---
name: opch-sites
description: Publish static sites from Chloe's workspace under `sites/` using a single `sites/sites.json` registry. Use when the user asks Chloe to create, update, publish, or expose one or more websites, especially from a monorepo.
metadata: { "openclaw": { "emoji": "🌐" } }
---

# Sites publishing (worker)

Chloe can publish static sites from her workspace. Every published site must live under `sites/` in the worker workspace, and publishing is controlled by one registry file: `sites/sites.json`.

## Directory layout

Use this structure:

```text
sites/
  sites.json
  marketing/
    dist/
      index.html
  docs/
    build/
      index.html
```

- All published output must stay inside `sites/`.
- Each site's `root` is a path relative to `sites/`.
- Do not publish files from outside `sites/`.

## Registry

Create `sites/sites.json`:

```json
{
  "sites": [
    {
      "name": "marketing",
      "subdomain": "marketing",
      "root": "marketing/dist"
    },
    {
      "name": "docs",
      "subdomain": "docs",
      "root": "docs/build",
      "basicauth": {
        "user": "preview",
        "bcrypt": "$2a$14$Zkx19XLiW6VYouLHR5NmfOFU0z2GTNmpkT/5qqR7hx4IjWJPDhjvG"
      }
    }
  ]
}
```

Fields per entry:

- `name`: required, human-readable unique label for the site entry.
- `subdomain`: required, lowercase letters/numbers/hyphens only. The public hostname becomes `<subdomain>.<base-domain>`.
- `root`: required, directory path relative to `sites/`. It must point to a subdirectory, not `sites/` itself.
- `basicauth`: optional. When set, the proxy requires HTTP Basic Auth for that site only. Must be an object with `user` (login name) and `bcrypt` (bcrypt modular-crypt hash). Generate the hash **inside the worker** with Python — no Docker or Caddy required:  
  `printf '%s' 'YOUR_PASSWORD' | python3 /opt/op-and-chloe/scripts/sites/hash_site_password.py`  
  Paste the printed line into `bcrypt`. Prefer stdin so the password does not appear in shell history or `ps`. Never put a plaintext password in `sites.json`.

**URL resolution (no extra flags):** The proxy always applies a single `try_files` chain: exact path, then `{path}.html`, then `{path}/index.html`, then `{path}/`, then `/index.html`. That covers Next.js `out/`-style pages, folder indexes, and SPAs that need a root `index.html` fallback. Legacy `spa` / `html_paths` keys in JSON are ignored.

## Workflow

When asked to publish a site:

1. Create or update the site under `sites/<site-name>/` or another nested folder inside `sites/`.
2. Put the built static output in a directory inside `sites/`, such as `marketing/dist` or `docs/build`.
3. Update `sites/sites.json` with a unique `name`, `subdomain`, and `root`.
4. If the user wants a shared login for that site only, add `basicauth` with `user` and `bcrypt`. Generate `bcrypt` with `python3 /opt/op-and-chloe/scripts/sites/hash_site_password.py` (pipe the password on stdin; see script docstring). Never write a plaintext password into the registry.
5. Tell the user the expected URL: `https://<subdomain>.<base-domain>`.

## Access and authentication

Published sites are **public by default** (anyone with the link). For private or sensitive work: keep publishing off, unpublish by removing the registry entry, add optional **`basicauth`** on that site’s registry entry (bcrypt hash only), or build login inside the app (OAuth, magic links, etc.).

## Rules

- Only publish static files from `sites/` in Chloe's workspace.
- Do not write raw proxy config.
- Do not use absolute paths or `..` in `root`.
- Do not point `root` at `sites/` itself.
- Do not publish trees containing symlinks.
- If the project is not built yet, build it into a folder inside `sites/` before publishing.
- If the user asks for a site to stop being published, remove its entry from `sites/sites.json`.
