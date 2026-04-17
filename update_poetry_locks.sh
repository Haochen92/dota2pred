#!/bin/bash

# Script to update all poetry.lock files in the repository
# This will run 'poetry lock --no-update' in each directory with a pyproject.toml file

set -e

echo "🔄 Updating all poetry lock files in the repository..."

# --- ADD THESE TWO LINES FOR DEBUGGING ---
echo "Script is using this poetry executable: $(which poetry)"
echo "Version reported by script: $(poetry --version)"
# -----------------------------------------

# Array of directories containing pyproject.toml files (excluding .venv)
POETRY_DIRS=(
    "."
    "live_orchestrator_app"
    "dota_oracle_schedules"
    "packages/dota_oracle_common"
    "packages/dota_oracle_pipeline"
    "services/inference_service"
    "services/api_service"
    "model_factory"
)

# Function to update poetry lock in a directory
update_poetry_lock() {
    local dir="$1"
    echo "📁 Updating poetry lock in: $dir"

    if [ -f "$dir/pyproject.toml" ]; then
        cd "$dir"

        # Check if poetry.lock exists
        if [ -f "poetry.lock" ]; then
            echo "  ↻ Updating existing poetry.lock"
            poetry lock
        else
            echo "  ✨ Creating new poetry.lock"
            poetry lock
        fi

        echo "  ✅ Done"
        cd - > /dev/null
    else
        echo "  ⚠️  No pyproject.toml found in $dir, skipping"
    fi
}

# Get the repository root directory
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$REPO_ROOT"

# Update poetry locks in all directories
for dir in "${POETRY_DIRS[@]}"; do
    update_poetry_lock "$dir"
    echo
done

echo "🎉 All poetry lock files have been updated!"
