#!/bin/bash
set -e # Exit immediately if a command exits with a non-zero status

# --- CONFIGURATION ---
# A dedicated pool for batch jobs to isolate them from the live orchestrator.
POOL_NAME="dota_oracle_scheduler"

echo "--- Batch Service Entrypoint Script ---"

# Step 1: Ensure the dedicated work pool exists.
echo "[1/3] Ensuring work pool '$POOL_NAME' exists..."
if ! prefect work-pool inspect "$POOL_NAME" > /dev/null 2>&1; then
    echo "      Work pool '$POOL_NAME' not found. Creating..."
    prefect work-pool create "$POOL_NAME" --type process
else
    echo "      Work pool '$POOL_NAME' already exists."
fi

# Step 2: Run all deployment scripts for the batch jobs.
# You will create a separate .py file for each scheduled job.
echo "[2/3] Registering all batch deployments..."
python -m dota_oracle_schedules.deploy_daily
# Add any new deployment scripts here in the future.

# Step 3: Start the worker as the main and final process.
# This worker will listen for jobs in the batch pool.
echo "[3/3] Starting worker for pool '$POOL_NAME'. Handing over control..."
exec prefect worker start --pool "$POOL_NAME"
