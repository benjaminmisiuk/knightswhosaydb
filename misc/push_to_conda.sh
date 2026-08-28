#!/usr/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"
cd ../ #script is in misc/, go to repo root

# ---------------------------------------------------------------------------
# 1. Read current version from pyproject.toml (single source of truth)
# ---------------------------------------------------------------------------
CURRENT_VERSION=$(grep -m1 '^version' pyproject.toml | sed 's/.*"\(.*\)".*/\1/').devp
echo "Current version: $CURRENT_VERSION"

# ---------------------------------------------------------------------------
# 2. Prompt for new version
# ---------------------------------------------------------------------------
read -rp "New version (leave empty to keep $CURRENT_VERSION): " NEW_VERSION
NEW_VERSION="${NEW_VERSION:-$CURRENT_VERSION}"

if [[ "$NEW_VERSION" != "$CURRENT_VERSION" ]]; then
    # Update pyproject.toml
    sed -i "0,/^version = \".*\"/s//version = \"$NEW_VERSION\"/" pyproject.toml
    echo "Updated pyproject.toml -> $NEW_VERSION"
fi

# Sync version into recipe.yaml (always, in case it drifted)
sed -i "s/version: \".*\"/version: \"$NEW_VERSION\"/" recipe/recipe.yaml
echo "Synced recipe/recipe.yaml -> $NEW_VERSION"

# ---------------------------------------------------------------------------
# 3. Build conda package
# ---------------------------------------------------------------------------
echo ""
echo "Building conda package..."
pixi run -e build rattler-build build \
    --recipe=recipe/recipe.yaml \
    --channel https://conda.anaconda.org/themachinethatgoesping \
    --channel conda-forge \
    --output-dir output

# ---------------------------------------------------------------------------
# 4. Find the built package
# ---------------------------------------------------------------------------
CONDA_FILE=$(find output/noarch -name "knightswhosaydb-${NEW_VERSION}-*.conda" -type f -printf '%T@ %p\n' 2>/dev/null \
    | sort -n | tail -1 | cut -d' ' -f2-)

if [[ -z "${CONDA_FILE:-}" ]]; then
    # Fallback: newest .conda in any output subdirectory
    CONDA_FILE=$(find output -name "knightswhosaydb-*.conda" -type f -printf '%T@ %p\n' 2>/dev/null \
        | sort -n | tail -1 | cut -d' ' -f2-)
fi

if [[ -z "${CONDA_FILE:-}" ]]; then
    echo "ERROR: No .conda file found in output/"
    exit 1
fi

# ---------------------------------------------------------------------------
# 5. Confirm before uploading
# ---------------------------------------------------------------------------
echo ""
echo "Package to upload:"
echo "  $CONDA_FILE"
echo ""
read -rp "Upload to anaconda.org/themachinethatgoesping? [y/N] " CONFIRM
if [[ "${CONFIRM,,}" != "y" && "${CONFIRM,,}" != "yes" ]]; then
    echo "Aborted."
    exit 0
fi

# ---------------------------------------------------------------------------
# 6. Upload
# ---------------------------------------------------------------------------
pixi run -e build rattler-build upload anaconda -o themachinethatgoesping "$CONDA_FILE"
echo ""
echo "Done! Published knightswhosaydb $NEW_VERSION"
