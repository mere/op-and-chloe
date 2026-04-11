#!/usr/bin/env python3
"""Focused tests for sites registry validation."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import reconcile_sites

# Example bcrypt for "hiccup" from Caddy docs (valid modular-crypt form).
_SAMPLE_BCRYPT = (
    "$2a$14$Zkx19XLiW6VYouLHR5NmfOFU0z2GTNmpkT/5qqR7hx4IjWJPDhjvG"
)


class ReconcileSitesValidationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tempdir.cleanup)
        self.workspace = Path(self.tempdir.name) / "workspace"
        self.sites_dir = self.workspace / "sites"
        self.sites_dir.mkdir(parents=True)

    def make_site_dir(self, relative_path: str) -> Path:
        path = self.sites_dir / relative_path
        path.mkdir(parents=True)
        return path

    def test_rejects_parent_traversal(self) -> None:
        self.make_site_dir("marketing/dist")
        with self.assertRaisesRegex(ValueError, "must stay inside the sites directory"):
            reconcile_sites.validate_relative_dir(self.sites_dir, "../outside")

    def test_rejects_sites_root_itself(self) -> None:
        with self.assertRaisesRegex(ValueError, "subdirectory inside sites/"):
            reconcile_sites.validate_relative_dir(self.sites_dir, ".")

    def test_rejects_symlink_in_published_tree(self) -> None:
        root = self.make_site_dir("marketing/dist")
        target = self.workspace / "secret.txt"
        target.write_text("secret")
        (root / "leak.txt").symlink_to(target)
        with self.assertRaisesRegex(ValueError, "must not contain symlinks"):
            reconcile_sites.validate_no_symlinks(root)

    def test_accepts_normal_site_tree(self) -> None:
        root = self.make_site_dir("marketing/dist/assets")
        (self.sites_dir / "marketing/dist/index.html").write_text("<h1>Hello</h1>")
        (root / "app.js").write_text("console.log('ok');")

        resolved = reconcile_sites.validate_relative_dir(self.sites_dir, "marketing/dist")
        reconcile_sites.validate_no_symlinks(resolved)

    def test_basicauth_accepted_in_registry(self) -> None:
        self.make_site_dir("app/dist")
        (self.sites_dir / "app/dist/index.html").write_text("<h1>x</h1>")
        registry = {
            "sites": [
                {
                    "name": "app",
                    "subdomain": "app",
                    "root": "app/dist",
                    "basicauth": {"user": "demo", "bcrypt": _SAMPLE_BCRYPT},
                }
            ]
        }
        (self.sites_dir / "sites.json").write_text(json.dumps(registry))
        published, notes = reconcile_sites.scan_sites(self.workspace, "example.com")
        self.assertEqual(len(notes), 0, notes)
        self.assertEqual(len(published), 1)
        self.assertEqual(published[0].basicauth, ("demo", _SAMPLE_BCRYPT))

    def test_basicauth_invalid_hash_skips_site(self) -> None:
        self.make_site_dir("app/dist")
        (self.sites_dir / "app/dist/index.html").write_text("<h1>x</h1>")
        registry = {
            "sites": [
                {
                    "name": "app",
                    "subdomain": "app",
                    "root": "app/dist",
                    "basicauth": {"user": "demo", "bcrypt": "not-a-bcrypt-hash"},
                }
            ]
        }
        (self.sites_dir / "sites.json").write_text(json.dumps(registry))
        published, notes = reconcile_sites.scan_sites(self.workspace, "example.com")
        self.assertEqual(published, [])
        self.assertTrue(any("bcrypt" in n for n in notes))

    def test_render_includes_basic_auth_block(self) -> None:
        site = reconcile_sites.PublishedSite(
            name="a",
            subdomain="h",
            domain="h.example.com",
            root=Path("/srv/x"),
            basicauth=("u-ser_1", _SAMPLE_BCRYPT),
        )
        out = reconcile_sites.render_sites([site], [], "example.com")
        self.assertIn("basic_auth", out)
        self.assertIn(_SAMPLE_BCRYPT, out)
        self.assertIn('"u-ser_1"', out)

    def test_render_default_try_files_chain(self) -> None:
        site = reconcile_sites.PublishedSite(
            name="web",
            subdomain="www",
            domain="www.example.com",
            root=Path("/srv/out"),
            basicauth=None,
        )
        out = reconcile_sites.render_sites([site], [], "example.com")
        self.assertIn("route {", out)
        self.assertIn("    @strip_slash path_regexp trailing ^/(.+)/$", out)
        self.assertIn("    uri @strip_slash strip_suffix /", out)
        self.assertIn(
            "    try_files {path} {path}.html {path}/index.html {path}/ /index.html",
            out,
        )
        self.assertIn("    file_server", out)

    def test_legacy_spa_and_html_paths_keys_ignored(self) -> None:
        self.make_site_dir("app/out")
        (self.sites_dir / "app/out/index.html").write_text("<h1>x</h1>")
        registry = {
            "sites": [
                {
                    "name": "app",
                    "subdomain": "app",
                    "root": "app/out",
                    "spa": True,
                    "html_paths": True,
                }
            ]
        }
        (self.sites_dir / "sites.json").write_text(json.dumps(registry))
        published, notes = reconcile_sites.scan_sites(self.workspace, "example.com")
        self.assertEqual(len(notes), 0, notes)
        self.assertEqual(len(published), 1)
        out = reconcile_sites.render_sites(published, [], "example.com")
        self.assertIn("route {", out)
        self.assertIn("    uri @strip_slash strip_suffix /", out)
        self.assertIn(
            "    try_files {path} {path}.html {path}/index.html {path}/ /index.html",
            out,
        )


if __name__ == "__main__":
    unittest.main()
