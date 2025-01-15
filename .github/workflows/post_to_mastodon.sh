#!/bin/bash

# Extract version from PR title passed as environment variable
version="${PR_TITLE##* }"

# Validate version format
if ! [[ $version =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
    echo "Error: Invalid version format in PR title: $version"
    exit 1
fi

# Construct changelog URL with proper quoting
changelog="https://github.com/snakemake/snakemake-executor-plugin-slurm/releases/tag/v${version}"

# Maximum character limit for Mastodon posts (on Fediscience: 1500 characters)
MAX_TOOT_LENGTH=500


read -d '\n' message << EndOfText
Beep, Beepi - I am the #Snakemake release bot

I have a new release in for the Snakemake executor for #SLURM on #HPC systems. The version now is '${version}'.

See ${changelog//\'/\\\'}for details.

Get the latest release from #Bioconda or #Pypi. Be sure to give it some time to be released there, too.

#OpenScience #ReproducibleResearch #ReproducibleComputing

EndOfText

# Validate message length
if [ ${#message} -gt $MAX_TOOT_LENGTH ]; then
    echo "Error: Message exceeds Fediscience's character limit"
    exit 1
fi

# Validate Mastodon token
if [ -z "${MASTODONBOT}" ]; then
    echo "Error: MASTODONBOT secret is not set"
    exit 1
fi

# Send post to Mastodon with proper quoting and error handling
response=$(curl -s -w "\n%{http_code}" -X POST \
    -H "Authorization: Bearer ${MASTODONBOT}" \
    -F "status=${message}" \
    "https://fediscience.org/api/v1/statuses")

status_code=$(echo "$response" | tail -n1)
response_body=$(echo "$response" | sed '$d')

if [ "$status_code" -ne 200 ]; then
    echo "Error: Failed to post to Mastodon (HTTP ${status_code})"
    echo "Response: ${response_body}"
    exit 1
fi

echo "Successfully posted to Mastodon"
