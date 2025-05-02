# Dockerfile

FROM python:3.10-slim

# Set workdir
WORKDIR /app

# Copy everything in
COPY . .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Default to running the Flask API
CMD ["python", "src/flask_api.py"]
