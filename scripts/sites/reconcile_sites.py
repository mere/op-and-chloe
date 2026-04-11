#!/usr/bin/env python3
"""Render Caddy site blocks from Chloe workspace sites registry."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from tempfile import NamedTemporaryFile


SUBDOMAIN_RE = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$")
# Modular-crypt bcrypt (e.g. from `caddy hash-password`); 22-char salt + 31-char digest after cost.
# $2a/$2b/$2y are common; $2x is legacy but same length.
BCRYPT_HASH_RE = re.compile(r"^\$2[abxy]\$\d{2}\$[./A-Za-z0-9]{53}$")
BASICAUTH_KEYS = frozenset({"user", "bcrypt"})


@dataclass(frozen=True)
class PublishedSite:
    name: str
    subdomain: str
    domain: str
    root: Path
    basicauth: tuple[str, str] | None = None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build Caddy config from workspace sites/sites.json."
    )
    parser.add_argument(
        "--workspace",
        required=True,
        help="Mounted Chloe workspace path inside the reconciler container.",
    )
    parser.add_argument(
        "--output",
        required=True,
        help="Output path for generated Caddyfile fragments.",
    )
    parser.add_argument(
        "--base-domain",
        default=os.environ.get("SITES_BASE_DOMAIN", "").strip(),
        help="Base domain appended to each site subdomain.",
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=0,
        help="Polling interval in seconds. Use 0 for one-shot generation.",
    )
    return parser.parse_args()


def read_manifest(manifest_path: Path) -> dict[str, object]:
    try:
        data = json.loads(manifest_path.read_text())
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid JSON: {exc.msg}") from exc
    if not isinstance(data, dict):
        raise ValueError("manifest must be a JSON object")
    return data


def validate_relative_dir(sites_dir: Path, value: object) -> Path:
    if not isinstance(value, str) or not value.strip():
        raise ValueError('"root" must be a non-empty string')
    root_value = value.strip()
    root_path = Path(root_value)
    if root_path.is_absolute():
        raise ValueError('"root" must be relative to the sites directory')
    if root_path == Path("."):
        raise ValueError('"root" must point to a subdirectory inside sites/')
    if any(part in {"..", ".", ""} for part in root_path.parts):
        raise ValueError('"root" must stay inside the sites directory')
    resolved = (sites_dir / root_path).resolve()
    sites_root = sites_dir.resolve()
    try:
        resolved.relative_to(sites_root)
    except ValueError as exc:
        raise ValueError('"root" must stay inside the sites directory') from exc
    if resolved == sites_root:
        raise ValueError('"root" must point to a subdirectory inside sites/')
    if not resolved.is_dir():
        raise ValueError(f'"root" directory does not exist: {root_value}')
    return resolved


def parse_basicauth(entry: dict[str, object]) -> tuple[str, str] | None:
    """Return (username, bcrypt_hash) or None if the site has no basic_auth block."""
    raw = entry.get("basicauth")
    if raw is None:
        return None
    if not isinstance(raw, dict):
        raise ValueError('"basicauth" must be a JSON object with "user" and "bcrypt"')
    unknown = set(raw) - BASICAUTH_KEYS
    if unknown:
        bad = ", ".join(sorted(unknown))
        raise ValueError(f'"basicauth" has unknown keys: {bad}')
    user = raw.get("user")
    bcrypt_hash = raw.get("bcrypt")
    if not isinstance(user, str) or not user.strip():
        raise ValueError('"basicauth.user" must be a non-empty string')
    if not isinstance(bcrypt_hash, str) or not bcrypt_hash.strip():
        raise ValueError('"basicauth.bcrypt" must be a non-empty string')
    user = user.strip()
    bcrypt_hash = bcrypt_hash.strip()
    if not BCRYPT_HASH_RE.fullmatch(bcrypt_hash):
        raise ValueError(
            '"basicauth.bcrypt" must be a bcrypt hash (run `caddy hash-password` on the proxy host)'
        )
    if len(user) > 256:
        raise ValueError('"basicauth.user" is too long')
    return (user, bcrypt_hash)


def validate_no_symlinks(root: Path) -> None:
    if root.is_symlink():
        raise ValueError(f'"root" must not be a symlink: {root.name}')

    for current_root, dirnames, filenames in os.walk(root, followlinks=False):
        current_path = Path(current_root)
        for dirname in list(dirnames):
            candidate = current_path / dirname
            if candidate.is_symlink():
                raise ValueError(f'published tree must not contain symlinks: {candidate}')
        for filename in filenames:
            candidate = current_path / filename
            if candidate.is_symlink():
                raise ValueError(f'published tree must not contain symlinks: {candidate}')


def validate_site(entry: object, sites_dir: Path, base_domain: str) -> PublishedSite:
    if not isinstance(entry, dict):
        raise ValueError("site entry must be a JSON object")

    name = entry.get("name")
    if not isinstance(name, str) or not name.strip():
        raise ValueError('"name" must be a non-empty string')
    name = name.strip()

    subdomain = entry.get("subdomain")
    if not isinstance(subdomain, str) or not SUBDOMAIN_RE.fullmatch(subdomain.strip()):
        raise ValueError(
            '"subdomain" must match lowercase letters, numbers, and hyphens'
        )
    subdomain = subdomain.strip()

    root = validate_relative_dir(sites_dir, entry.get("root"))
    validate_no_symlinks(root)
    domain = f"{subdomain}.{base_domain}"
    basicauth = parse_basicauth(entry)

    return PublishedSite(
        name=name,
        subdomain=subdomain,
        domain=domain,
        root=root,
        basicauth=basicauth,
    )


def scan_sites(workspace: Path, base_domain: str) -> tuple[list[PublishedSite], list[str]]:
    sites_dir = workspace / "sites"
    registry_path = sites_dir / "sites.json"
    published: list[PublishedSite] = []
    notes: list[str] = []

    if not base_domain:
        notes.append("base domain is not configured; set SITES_BASE_DOMAIN to publish sites")
        return published, notes

    if not sites_dir.exists():
        notes.append(f"workspace sites directory not found: {sites_dir}")
        return published, notes

    if not registry_path.exists():
        notes.append(f"sites registry not found: {registry_path}")
        return published, notes

    try:
        registry = read_manifest(registry_path)
    except ValueError as exc:
        notes.append(f"invalid sites registry: {exc}")
        return published, notes

    entries = registry.get("sites")
    if not isinstance(entries, list):
        notes.append('invalid sites registry: "sites" must be an array')
        return published, notes

    seen_subdomains: dict[str, str] = {}
    for index, entry in enumerate(entries, start=1):
        try:
            site = validate_site(entry, sites_dir, base_domain)
        except ValueError as exc:
            notes.append(f"skipping sites[{index}]: {exc}")
            continue

        previous = seen_subdomains.get(site.subdomain)
        if previous:
            notes.append(
                f"skipping {site.name}: subdomain '{site.subdomain}' already used by {previous}"
            )
            continue
        seen_subdomains[site.subdomain] = site.name
        published.append(site)

    if not published:
        notes.append("no published sites found in workspace/sites/sites.json")

    return published, notes


def quote(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def render_sites(published: list[PublishedSite], notes: list[str], base_domain: str) -> str:
    lines = [
        "# Generated by scripts/sites/reconcile_sites.py",
        "http://127.0.0.1:9080 {",
        '  respond "sites proxy ready" 200',
        "}",
        "",
    ]

    if base_domain:
        lines.extend(
            [
                f"# Base domain: {base_domain}",
                "",
            ]
        )

    for note in notes:
        lines.append(f"# {note}")
    if notes:
        lines.append("")

    for site in published:
        lines.append(f"{site.domain} {{")
        lines.append(f"  root * {quote(str(site.root))}")
        lines.append("  encode zstd gzip")
        if site.basicauth is not None:
            user, bcrypt_hash = site.basicauth
            lines.append("  basic_auth {")
            lines.append(f"    {quote(user)} {quote(bcrypt_hash)}")
            lines.append("  }")
        # Strip trailing slash (except bare /) so /blog/ becomes /blog and {path}.html finds blog.html.
        lines.append("  @strip_slash path_regexp trailing ^/(.+)/$")
        lines.append("  uri @strip_slash strip_suffix /")
        # One chain: real files, extensionless .html, directory index, SPA fallback to /index.html.
        lines.append(
            "  try_files {path} {path}.html {path}/index.html {path}/ /index.html"
        )
        lines.append("  file_server")
        lines.append("}")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def write_if_changed(output_path: Path, content: str) -> bool:
    existing = output_path.read_text() if output_path.exists() else None
    if existing == content:
        return False

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile("w", dir=output_path.parent, delete=False) as tmp:
        tmp.write(content)
        tmp_path = Path(tmp.name)
    tmp_path.replace(output_path)
    return True


def reconcile_once(workspace: Path, output_path: Path, base_domain: str) -> bool:
    published, notes = scan_sites(workspace, base_domain.strip().lower())
    rendered = render_sites(published, notes, base_domain.strip().lower())
    changed = write_if_changed(output_path, rendered)
    summary = f"published={len(published)} notes={len(notes)} changed={'yes' if changed else 'no'}"
    print(f"[sites] {summary}", flush=True)
    return changed


def main() -> int:
    args = parse_args()
    workspace = Path(args.workspace).resolve()
    output_path = Path(args.output).resolve()
    base_domain = args.base_domain.strip().lower()

    if args.interval <= 0:
        reconcile_once(workspace, output_path, base_domain)
        return 0

    print(
        f"[sites] watching {workspace / 'sites'} for publish manifests every {args.interval:g}s",
        flush=True,
    )
    while True:
        try:
            reconcile_once(workspace, output_path, base_domain)
        except Exception as exc:  # noqa: BLE001
            print(f"[sites] reconcile failed: {exc}", file=sys.stderr, flush=True)
        time.sleep(args.interval)


if __name__ == "__main__":
    raise SystemExit(main())
