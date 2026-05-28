#!/bin/sh
set -eu

output_file="$1"
signal_file="${output_file}.signal"

trap 'printf "SIGUSR1\n" > "$signal_file"' USR1

count=0
while [ "$count" -lt 45 ]; do
    sleep 1
    count=$((count + 1))
done

printf "shell-finished\n" > "$output_file"