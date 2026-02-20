# Dockerfile for InsightPilot (Streamlit + FastAPI)

# Use official Python image
FROM python:3.12-slim

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y build-essential libpq-dev && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the code
COPY . .

# Expose Streamlit and FastAPI ports
EXPOSE 8501 8100

# Default command: run both Streamlit and FastAPI
CMD ["sh", "-c", "streamlit run app.py & uvicorn api.server:app --host 0.0.0.0 --port 8100"]
