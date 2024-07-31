FROM python:3.10.11-slim

WORKDIR /app

# Combine the update and install commands, and clean up to reduce image size
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements.txt into the container
COPY src/requirements.txt ./

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt


# # Copy the rest of the application code
# COPY . .

# Expose the necessary port
EXPOSE 8501

# Healthcheck to ensure the app is running
HEALTHCHECK CMD curl --fail http://localhost:8501/_stcore/health || exit 1

# Define the entrypoint command to run the Streamlit app
ENTRYPOINT ["streamlit", "run", "home.py", "--server.port=8501", "--server.address=0.0.0.0"]

