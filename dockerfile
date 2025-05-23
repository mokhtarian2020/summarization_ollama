# Use official Python image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy requirements first (to leverage Docker cache)
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the code
COPY . .

# Expose port 8002
EXPOSE 8002

# Run the app
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8002"]
