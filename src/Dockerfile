FROM python:3.10.11-slim

WORKDIR /app

# Combine the update and install commands, and clean up to reduce image size
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy the application code into the container
COPY requirements.txt requirements.txt

# Install Python dependencies
RUN pip3 install -r requirements.txt

# Expose the necessary port
EXPOSE 8501

# Healthcheck to ensure the app is running
HEALTHCHECK CMD curl --fail http://localhost:8501/_stcore/health || exit 1

# Define the entrypoint command to run the Streamlit app
ENTRYPOINT ["streamlit", "run", "streamlit_main.py", "--server.port=8501", "--server.address=0.0.0.0"]

