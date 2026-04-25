#!/usr/bin/env python3
"""Run ./openclaw.mjs in the worker container with a hard wall-clock timeout.

Usage:
  openclaw_docker_exec.py <container_name> <timeout_seconds> -- <mjs subcommand args...>

Examples:
  openclaw_docker_exec.py op-and-chloe-openclaw-gateway 5 -- --version
  openclaw_docker_exec.py op-and-chloe-openclaw-gateway 8 -- update status --json
"""
import subprocess
import sys


def main() -> int:
    if len(sys.argv) < 5 or "--" not in sys.argv:
        return 2
    i = sys.argv.index("--")
    container = sys.argv[1]
    timeout = float(sys.argv[2])
    mjs_args = sys.argv[i + 1 :]
    cmd = ["docker", "exec", "-i", container, "./openclaw.mjs"] + mjs_args
    try:
        p = subprocess.run(
            cmd,
            timeout=timeout,
            capture_output=True,
            text=True,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        return 0
    if p.stdout:
        print(p.stdout, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
