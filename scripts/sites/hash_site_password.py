#!/usr/bin/env python3
"""Emit a bcrypt modular-crypt hash for sites.json basicauth (Caddy basic_auth compatible).

Reads the password from the first argument or, if omitted, from stdin (no echo in terminal;
prefer stdin or a here-doc so the secret is not visible in `ps`).

Example:
  printf '%s' 'your-password' | python3 scripts/sites/hash_site_password.py
  python3 scripts/sites/hash_site_password.py   # then type password and press Ctrl-D
"""

from __future__ import annotations

import argparse
import sys

import bcrypt


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "password",
        nargs="?",
        help="Plaintext password (omit to read stdin until EOF)",
    )
    parser.add_argument(
        "--rounds",
        type=int,
        default=12,
        metavar="N",
        help="bcrypt cost (default: 12; Caddy often uses 14 — both are fine)",
    )
    args = parser.parse_args()
    if args.password is None:
        raw = sys.stdin.read()
        password = raw.rstrip("\r\n")
    else:
        password = args.password
    if not password:
        print("hash_site_password: need a non-empty password", file=sys.stderr)
        return 1
    if not (4 <= args.rounds <= 31):
        print("hash_site_password: --rounds must be between 4 and 31", file=sys.stderr)
        return 1
    digest = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(rounds=args.rounds))
    sys.stdout.write(digest.decode("ascii") + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
