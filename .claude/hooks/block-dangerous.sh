#!/usr/bin/env bash
# PreToolUse hook: block destructive Bash commands. Reads tool input JSON on stdin.
# Exit 2 = block with message. Exit 0 = allow.
input=$(cat)
if echo "$input" | grep -qE 'rm[[:space:]]+(-[a-z]*r[a-z]*f|-[a-z]*f[a-z]*r)|:\(\)\{[[:space:]]*:[|:][^}]*\}&|mkfs|dd[[:space:]]+if=|DROP[[:space:]]+(TABLE|DATABASE)|DELETE[[:space:]]+FROM[[:space:]]+financial_facts'; then
  echo "Blocked: destructive command pattern detected. Confirm explicitly with the user before running." >&2
  exit 2
fi
exit 0
