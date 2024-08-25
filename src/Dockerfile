FROM python:3.10.11-slim

# Combine the update and install commands, and clean up to reduce image size
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    libreoffice \
    openjdk-11-jre \
    fonts-dejavu \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

# Create a user to avoid running as root
# RUN useradd -m acai 
# USER acai

WORKDIR /app

COPY src/nltk_data /usr/share/nltk_data
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

