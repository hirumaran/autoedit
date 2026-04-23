#!/bin/bash
set -e

echo "Running frontend build..."
output=$(npm run build 2>&1)

# Fail on the old Vite "can't be bundled" warning
if echo "$output" | grep -q "can't be bundled without type=\"module\" attribute"; then
    echo "ERROR: Build warning about missing type=module detected."
    exit 1
fi

# Fail on any build error
if echo "$output" | grep -qi "^.*error.*:"; then
    echo "ERROR: Build failed with errors."
    echo "$output"
    exit 1
fi

# Verify dist/index.html does NOT reference raw /src/ scripts (must be bundled)
if grep -q 'src="/src/' dist/index.html; then
    echo "ERROR: dist/index.html still references a raw /src/ script — not bundled!"
    exit 1
fi

# Verify dist/index.html references a bundled asset
if ! grep -q 'src="/assets/' dist/index.html; then
    echo "ERROR: dist/index.html has no bundled /assets/ script reference."
    exit 1
fi

# Verify the bundled JS contains critical app logic (API routes)
JS_FILE=$(ls dist/assets/*.js 2>/dev/null | head -1)
if [ -z "$JS_FILE" ]; then
    echo "ERROR: No JS bundle found in dist/assets/"
    exit 1
fi

for MARKER in "/api/upload" "/api/render" "DOMContentLoaded"; do
    if ! grep -q "$MARKER" "$JS_FILE"; then
        echo "ERROR: Bundle missing critical marker: $MARKER"
        exit 1
    fi
done

echo "✅ Build succeeded: no warnings, dist/index.html references bundled assets, app logic confirmed in bundle."
exit 0