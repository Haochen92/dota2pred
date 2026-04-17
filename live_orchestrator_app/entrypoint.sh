#!/bin/bash
set -e  # Exit immediately if a command exits with a non-zero status

# Ensure the Prefect work pool exists
echo "Checking for existing work pool..."
if ! prefect work-pool inspect "dota-work-pool"; then
    echo "Work pool does not exist. Creating it now..."
    prefect work-pool create "dota-work-pool" --type process || echo "Failed to create work-pool"
else
    echo "Work pool already exists."
fi

# Start deployment script
echo "Starting service..."
python -m live_orchestrator_app.deploy_service


# Production/Development runtime selection
if [ "$#" -gt 0 ]; then
  # Development mode: Execute custom command (e.g., from docker compose watch)
  exec "$@"
else
  # Production mode: Start the standard Prefect worker
  echo "Starting the Prefect worker for the work pool 'dota-work-pool'..."
  exec prefect worker start -p "dota-work-pool"
fi
