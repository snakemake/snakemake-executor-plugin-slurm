cat <<EOF | sed 's/^[[:space:]]*//' > issue_body.md
  #### Sync with upstream vTEST

  This issue was auto-generated on detection of a new upstream version. Perform the following to manually sync:

  ```bash
  git fetch upstream
  git checkout main
  git merge upstream/main
  #
  # Resolve any conflicts, if necessary
  #
  git add -A
  git commit -m "Merge remote-tracking branch 'upstream/main'"
  git push origin main
  ```

  Or using VS Code's command palette (Ctrl+Shift+P):

  1. Git: Fetch from… → choose upstream.
  2. Git: Merge Branch… → pick upstream/main.
  3. If there are conflicts, VS Code will show them in the editor; resolve, then commit and push. 
EOF
