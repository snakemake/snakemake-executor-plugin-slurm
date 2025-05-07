import requests
import toml
import sys
from packaging.version import Version, InvalidVersion

UPSTREAM_REPO = "snakemake/snakemake-executor-plugin-slurm-jobstep"
PYPROJECT = "pyproject.toml"

EXIT_OK = 0         # no changes
EXIT_ERROR = 1      # script failure
EXIT_NEW_RELEASE = 42  # desired trigger

def error(msg):
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(EXIT_ERROR)

def get_latest_upstream_version():
    url = f"https://api.github.com/repos/{UPSTREAM_REPO}/releases/latest"
    headers = {"Accept": "application/vnd.github+json"}

    r = requests.get(url, headers=headers)
    if r.status_code != 200:
        error(f"Failed to fetch upstream release info: {r.status_code}")

    try:
        version_str = r.json()["tag_name"].lstrip("v")
        return Version(version_str)
    except Exception:
        error("Failed to parse upstream version from tag")

def get_local_main_version():
    try:
        data = toml.load(PYPROJECT)
        version_str = data["tool"]["poetry"]["version"]

        # Split out base version (e.g. 1.2.1 from 1.2.1.post2)
        return Version(version_str).base_version
    except Exception as e:
        error(f"Could not parse pyproject.toml version: {e}")

def main():
    upstream = get_latest_upstream_version()
    local = get_local_main_version()

    print(f"Local main version = {local}")
    print(f"Upstream version    = {upstream}")

    if upstream > local:
        print("New upstream release detected!")
        sys.exit(EXIT_NEW_RELEASE)
    else:
        print("No new release")
        sys.exit(EXIT_OK)

if __name__ == "__main__":
    main()