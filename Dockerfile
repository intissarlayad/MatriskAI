# Base image
FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Install system dependencies (useful for building C extensions if needed by Prophet/Pandas)
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Expose Streamlit default port
EXPOSE 8501

# Run the Streamlit dashboard
CMD ["streamlit", "run", "Scripts/matrisk_step5_dashboard.py", "--server.port=8501", "--server.address=0.0.0.0"]
