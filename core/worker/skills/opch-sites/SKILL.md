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
      "root": "marketing/dist",
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

Fields per entry:

- `name`: required, human-readable unique label for the site entry.
- `subdomain`: required, lowercase letters/numbers/hyphens only. The public hostname becomes `<subdomain>.<base-domain>`.
- `root`: required, directory path relative to `sites/`. It must point to a subdirectory, not `sites/` itself.
- `spa`: optional. Set `true` for single-page apps that should fall back to `index.html`.

## Workflow

When asked to publish a site:

1. Create or update the site under `sites/<site-name>/` or another nested folder inside `sites/`.
2. Put the built static output in a directory inside `sites/`, such as `marketing/dist` or `docs/build`.
3. Update `sites/sites.json` with a unique `name`, `subdomain`, and `root`.
4. Tell the user the expected URL: `https://<subdomain>.<base-domain>`.

## Rules

- Only publish static files from `sites/` in Chloe's workspace.
- Do not write raw proxy config.
- Do not use absolute paths or `..` in `root`.
- Do not point `root` at `sites/` itself.
- Do not publish trees containing symlinks.
- If the project is not built yet, build it into a folder inside `sites/` before publishing.
- If the user asks for a site to stop being published, remove its entry from `sites/sites.json`.
