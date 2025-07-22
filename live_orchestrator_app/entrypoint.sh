#!/bin/bash
set -e  # Exit immediately if a command exits with a non-zero status

# Ensure the Prefect work pool exists
echo "Checking for existing work pool..."
if ! prefect work-pool inspect "work-pool"; then
    echo "Work pool does not exist. Creating it now..."
    prefect work-pool create "work-pool" --type process || echo "Failed to create work-pool"
else
    echo "Work pool already exists."
fi

# Optional: Add a small delay to ensure work pool is created before continuing
sleep 20  # Adjust the sleep time if necessary

# Start the Prefect worker
echo "Starting the Prefect worker for the work pool 'work-pool'..."
prefect worker start -p "work-pool" &  # Run the worker in the background

# Run the Python deployment script
echo "Deploying the flow..."
python deploy_flow.py

# Wait for background processes to finish (if any)
wait
