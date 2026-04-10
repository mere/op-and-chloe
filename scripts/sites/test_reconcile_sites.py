#!/usr/bin/env python3
"""Focused tests for sites registry validation."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import reconcile_sites


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


if __name__ == "__main__":
    unittest.main()
