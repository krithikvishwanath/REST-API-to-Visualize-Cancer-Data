# src/jobs.py

import redis
import json
import matplotlib.pyplot as plt
import base64
import io

# Connect to Redis
r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)

RAW_DATA_KEY = "raw_data"

def load_data():
    """Load the raw data from Redis."""
    raw_data = r.get(RAW_DATA_KEY)
    if not raw_data:
        raise ValueError("No dataset found in Redis.")
    return json.loads(raw_data)

def extract_fields(data, x_field, y_field):
    """Extract x and y values from dataset."""
    x_vals, y_vals = [], []

    for row in data:
        try:
            x = float(row.get(x_field, 'nan'))
            y = float(row.get(y_field, 'nan'))
            if not (x is None or y is None):
                x_vals.append(x)
                y_vals.append(y)
        except:
            continue

    if not x_vals or not y_vals:
        raise ValueError("No valid x/y data points found.")

    return x_vals, y_vals

def generate_scatter_plot(x_vals, y_vals, x_label, y_label, title=None):
    """Generate and return a scatter plot image as base64."""
    fig, ax = plt.subplots()
    ax.scatter(x_vals, y_vals, alpha=0.7)
    ax.set_xlabel(x_label)
    ax.set_ylabel(y_label)
    ax.set_title(title or f"{y_label} vs {x_label}")

    # Encode to base64
    img_buf = io.BytesIO()
    plt.savefig(img_buf, format='png')
    plt.close(fig)
    img_buf.seek(0)
    return base64.b64encode(img_buf.read()).decode('utf-8')

def run_job(x_field, y_field):
    """Main callable for the worker: runs an analysis job."""
    data = load_data()
    x_vals, y_vals = extract_fields(data, x_field, y_field)
    return generate_scatter_plot(x_vals, y_vals, x_field, y_field)
