#!/bin/bash

version="${${{ github.event.pull_request.title }}##* }"
changelog="https://github.com/snakemake/snakemake-executor-plugin-slurm/releases/tag/v${version}"

read -d '\n' message << EndOfText
Beep, Beepi - I am the #Snakemake release bot

I have a new release in for the Snakemake executor for #SLURM on #HPC systems. The version now is '${version}'.

See ${changelog} for details.

Get the latest release from #Bioconda or #Pypi. Be sure to give it some time to be released there, too.

#OpenScience #ReproducibleResearch #ReproducibleComputing

EndOfText

curl -X POST -H "Authorization: Bearer ${{ secrets.MASTODONBOT }}" \
                     -F "status=${message}" \
                     https://fediscience.org/api/v1/statuses \
                     -w "\nResponse code: %{http_code}\n" \
                     -f || {
                       echo "Failed to post to Mastodon"
                       exit 1
                     }
