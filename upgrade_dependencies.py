#!/usr/bin/env python3
"""
Upgrade pyproject.toml dependencies to sensible ranges after poetry update.

This script converts resolved versions to >= min, < next_major constraints
for all main and dev dependencies, allowing flexibility while preventing
unexpected major version breaks.

Usage:
    python3 upgrade_dependencies.py --dry-run    # preview changes
    python3 upgrade_dependencies.py               # apply changes
"""

import re
import shlex
import subprocess
import sys
import json
import tomllib
from pathlib import Path


def main():
    dry_run = "--dry-run" in sys.argv or "-n" in sys.argv

    pyproject_path = Path("pyproject.toml")
    if not pyproject_path.exists():
        print("Error: pyproject.toml not found in current directory")
        sys.exit(1)

    with open(pyproject_path, "rb") as f:
        data = tomllib.load(f)

    sections = [
        ("main", data["tool"]["poetry"]["dependencies"], None),
        ("dev", data["tool"]["poetry"]["group"]["dev"]["dependencies"], "dev"),
    ]

    def resolved_version(pkg):
        """Get the resolved version of a package from poetry show."""
        try:
            out = subprocess.check_output(
                ["poetry", "show", pkg, "--format=json"],
                text=True,
                stderr=subprocess.DEVNULL,
            )
            data = json.loads(out)
            return data.get("version")
        except (subprocess.CalledProcessError, json.JSONDecodeError, KeyError):
            return None

    def sensible_range(ver):
        """Convert a version string to >= ver, < next_major range."""
        m = re.match(r"^(\d+)\.(\d+)\.(\d+)", ver)
        if not m:
            return None
        major, minor, patch = map(int, m.groups())
        return f">={major}.{minor}.{patch},<{major+1}"

    print("Upgrading pyproject.toml dependencies to sensible ranges...")
    print(f"(dry-run mode: {dry_run})\n")

    upgraded_count = 0

    for section_name, deps, group in sections:
        print(f"--- {section_name.upper()} DEPENDENCIES ---")
        for pkg in sorted(deps.keys()):
            if pkg == "python":
                continue

            v = resolved_version(pkg)
            if not v:
                print(f"  skip {pkg}: cannot resolve version")
                continue

            rng = sensible_range(v)
            if not rng:
                print(f"  skip {pkg}: non-semver resolved version {v}")
                continue

            cmd = ["poetry", "add", f"{pkg}@{rng}"]
            if group:
                cmd += ["--group", group]

            cmd_str = " ".join(shlex.quote(c) for c in cmd)
            print(f"  {pkg}: {v} -> {rng}")
            print(f"    $ {cmd_str}")

            if not dry_run:
                try:
                    subprocess.check_call(cmd, stdout=subprocess.DEVNULL)
                    upgraded_count += 1
                except subprocess.CalledProcessError as e:
                    print(f"    ERROR: {e}")
            else:
                upgraded_count += 1

        print()

    if dry_run:
        print("Dry-run complete. Run without --dry-run to apply changes.")
        print("After applying, run:")
        print("  poetry lock")
        print("  poetry install")
        print("  poetry run pytest -q")
    else:
        print(f"Upgraded {upgraded_count} dependencies. Running poetry lock...")
        subprocess.check_call(["poetry", "lock"])
        print("Complete. Run 'poetry install' to refresh your environment.")


if __name__ == "__main__":
    main()
