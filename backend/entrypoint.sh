#!/bin/bash
# Create the Prefect work pool if it doesn't exist
prefect work-pool create work-pool || echo "Work-pool already exists"

# Start the Prefect worker
prefect worker start -p "work-pool"

python deploy_flow.py

# Wait for background processes to finish (optional)
wait