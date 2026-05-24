#!/bin/bash

# Estrai la prima versione dal CHANGELOG
VERSION=$(grep -oP '^## \[\K[^\]]+' CHANGELOG.md | head -1)

# Estrai solo quella sezione (dal titolo ## [X.Y.Z] fino al prossimo ## [)
NOTES=$(awk -v v="$VERSION" '
  $0 ~ "^## \\[" v "\\]" { in_section=1; next }
  in_section && /^## \[/ { exit }
  in_section { print }
' CHANGELOG.md)

gh release create "v$VERSION" --notes "$NOTES"
