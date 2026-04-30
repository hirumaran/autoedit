#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

output=$(npm run build 2>&1) || true

if echo "$output" | grep -qiE "warning|not bundled|error"; then
    echo "Build NOT clean — found warnings or errors:"
    echo "$output" | grep -iE "warning|not bundled|error"
    exit 1
fi

echo "Build clean."
exit 0
