#!/usr/bin/env python3
"""Parse `openclaw.mjs update status` (JSON or text) for menu display.

argv1: running version (e.g. 2026.3.25) from `openclaw.mjs --version` (required).
stdin: output of `openclaw.mjs update status` or `update status --json`.

Print: LATEST<tab>NEEDS(0|1)  (no newline if not desired — caller can add)
"""
import json
import re
import sys
from typing import List, Optional, Tuple

VER = re.compile(r"(?<!\d)(\d{4}\.\d{1,2}\.\d{1,2})(?!\d)")


def norm(ver: str) -> Optional[Tuple[int, int, int]]:
    m = re.fullmatch(r"(\d{4})\.(\d{1,2})\.(\d{1,2})", ver.strip())
    if not m:
        return None
    return (int(m.group(1)), int(m.group(2)), int(m.group(3)))


def all_versions_in_string(s: str) -> List[str]:
    if s.lstrip().startswith("{"):
        try:
            s = json.dumps(json.loads(s), sort_keys=True)
        except json.JSONDecodeError:
            pass
    return list(dict.fromkeys(VER.findall(s)))


def main() -> None:
    run = (sys.argv[1] or "").strip() if len(sys.argv) > 1 else ""
    raw = sys.stdin.read()
    n_run = norm(run) if run else None
    vers = all_versions_in_string(raw) if raw.strip() else []
    need = 0
    latest = ""

    if n_run and vers:
        newer = []
        for v in vers:
            nv = norm(v)
            if nv is not None and n_run < nv:
                newer.append(v)
        if newer:
            latest = max(newer, key=lambda v: norm(v) or (0, 0, 0))  # type: ignore[arg-type, return-value]
            need = 1
        else:
            # No higher version in output — up to date or only current published
            latest = run
            m_all = [v for v in vers if norm(v)]
            if m_all:
                mx = max(m_all, key=lambda v: norm(v) or (0, 0, 0))  # type: ignore[arg-type, return-value]
                if norm(mx) == n_run or mx == run:
                    latest = run
    elif vers:
        latest = max(vers, key=lambda v: norm(v) or (0, 0, 0))  # type: ignore[arg-type, return-value]
    else:
        latest = run

    if not latest:
        latest = run
    print(f"{latest}\t{need}", end="")


if __name__ == "__main__":
    main()
