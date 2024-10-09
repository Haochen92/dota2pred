# Use a lightweight Python base image
FROM python:3.10-slim

# Set the working directory in the container
WORKDIR /app

# Install Git and other necessary dependencies
RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

# Upgrade pip and install required dependencies
RUN pip install --upgrade pip

# Copy the requirements.txt first and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of your application code into the container (including entrypoint.sh)
COPY . .

# Ensure that entrypoint.sh is executable
RUN chmod +x /app/entrypoint.sh

# Expose the port your app runs on (8000 in this case)
EXPOSE 8000

# Run the entrypoint script
ENTRYPOINT ["/app/entrypoint.sh"]
