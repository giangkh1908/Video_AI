#!/usr/bin/env bash
# Stop hook: surgical-change checklist reminder. Always exit 0 (advisory only).
cat <<'EOF'
Surgical checklist: every changed line traces to the request? No unrelated refactors? Orphans from YOUR changes removed? Tests/build run?
EOF
exit 0
