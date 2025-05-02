FROM python:3.10-slim

WORKDIR /app
COPY . .

RUN apt-get update && \
    apt-get install -y --no-install-recommends git gcc g++ && \
    rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir -r requirements.txt
CMD ["python", "src/flask_api.py"]
