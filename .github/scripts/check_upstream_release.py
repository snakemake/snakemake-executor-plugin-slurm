import requests
import toml
import sys
from packaging.version import Version, InvalidVersion

PYPROJECT = "pyproject.toml"
UPSTREAM_REPO = "snakemake/snakemake-executor-plugin-slurm"

def get_latest_upstream_version():
    url = f"https://api.github.com/repos/{UPSTREAM_REPO}/releases/latest"
    headers = {"Accept": "application/vnd.github+json"}
    r = requests.get(url, headers=headers)

    if r.status_code != 200:
        print(f"ERROR: Failed to fetch upstream release info: {r.status_code}")
        sys.exit(1)

    tag = r.json()["tag_name"]
    version_str = tag.lstrip("v")
    print(f"Latest upstream release: {version_str}")
    return Version(version_str)

def get_current_main_version_from_pyproject():
    with open(PYPROJECT) as f:
        data = toml.load(f)

    version_str = data["tool"]["poetry"]["version"]
    try:
        version = Version(version_str)
    except InvalidVersion:
        print(f"ERROR: Invalid version format: {version_str}")
        sys.exit(1)

    # Split out the "main" portion (e.g., 1.2.1 from 1.2.1.post3)
    main_version_parts = version.base_version  # str: "1.2.1"
    print(f"Fork is currently synced to upstream version: {main_version_parts}")
    return Version(main_version_parts)

def main():
    upstream_version = get_latest_upstream_version()
    current_main_version = get_current_main_version_from_pyproject()

    if upstream_version > current_main_version:
        print(f"New upstream release: {upstream_version}")
        print(f"Fork is behind — consider syncing and bumping.")
        sys.exit(1)
    else:
        print("Up-to-date with upstream release.")

if __name__ == "__main__":
    main()