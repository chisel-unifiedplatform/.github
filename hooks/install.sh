#!/bin/sh
# Install the pre-push hook into every git repo under the given folders.
#   sh install.sh ~/code/vocalix            # all repos in that folder (two levels deep)
#   sh install.sh .                         # just this repo
# Repos that manage hooks with husky or pre-commit get the hook added there instead.
set -e
HOOK_URL="https://raw.githubusercontent.com/chisel-unifiedplatform/.github/main/hooks/pre-push"
SRC="$(cd "$(dirname "$0")" && pwd)/pre-push"
[ -f "$SRC" ] || { SRC="$(mktemp)"; curl -fsSL "$HOOK_URL" -o "$SRC"; }
for root in "${@:-.}"; do
  for git_dir in $(find "$root" -maxdepth 3 -type d -name .git 2>/dev/null); do
    repo="$(dirname "$git_dir")"
    hooks_path="$(git -C "$repo" config --get core.hooksPath || true)"
    if [ -n "$hooks_path" ]; then
      target="$repo/$hooks_path/pre-push"
      if [ -f "$target" ] && grep -q "Push to '.*' blocked" "$target"; then echo "= $repo (already installed in $hooks_path)"; continue; fi
      if [ -f "$target" ]; then
        printf '\n# chisel: block direct pushes to shared branches\n%s\n' "$(sed '1d' "$SRC")" >> "$target"
      else cp "$SRC" "$target"; fi
      chmod +x "$target"; echo "+ $repo ($hooks_path/pre-push — commit this file so the team gets it)"
    else
      cp "$SRC" "$git_dir/hooks/pre-push"; chmod +x "$git_dir/hooks/pre-push"; echo "+ $repo"
    fi
  done
done
