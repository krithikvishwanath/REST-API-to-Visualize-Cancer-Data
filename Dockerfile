FROM python:3.10-slim

WORKDIR /app
COPY . .

RUN pip install --no-cache-dir -r requirements.txt

# Matplotlib will default to Agg because we didn't install any GUI libs
CMD ["python", "src/flask_api.py"]
