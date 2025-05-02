# src/worker.py

import redis
import json
import time
import matplotlib.pyplot as plt
import base64
import io

# Redis connection
r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)

RAW_DATA_KEY = "raw_data"
JOB_QUEUE = "job_queue"
JOB_STATUS = "job_status"
JOB_RESULT = "job_result"

def generate_plot(x_field, y_field):
    """Generate a plot from the stored dataset."""
    raw_data = r.get(RAW_DATA_KEY)
    if not raw_data:
        raise ValueError("No dataset found.")
    
    data = json.loads(raw_data)

    x_vals = []
    y_vals = []

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
        raise ValueError("No valid data points to plot.")

    fig, ax = plt.subplots()
    ax.scatter(x_vals, y_vals, alpha=0.7)
    ax.set_xlabel(x_field)
    ax.set_ylabel(y_field)
    ax.set_title(f'{y_field} vs {x_field}')

    # Convert image to base64
    img_buf = io.BytesIO()
    plt.savefig(img_buf, format='png')
    plt.close(fig)
    img_buf.seek(0)
    img_base64 = base64.b64encode(img_buf.read()).decode('utf-8')
    return img_base64

def process_job(job_data):
    job_id = job_data.get("job_id")
    x_field = job_data.get("x_field")
    y_field = job_data.get("y_field")

    if not all([job_id, x_field, y_field]):
        r.hset(JOB_STATUS, job_id, "failed: missing job fields")
        return

    try:
        r.hset(JOB_STATUS, job_id, "processing")
        img_base64 = generate_plot(x_field, y_field)
        r.hset(JOB_RESULT, job_id, img_base64)
        r.hset(JOB_STATUS, job_id, "completed")
    except Exception as e:
        r.hset(JOB_STATUS, job_id, f"failed: {str(e)}")

def main():
    print("Worker started. Listening for jobs...")
    while True:
        _, job_raw = r.blpop(JOB_QUEUE)  # blocking pop
        try:
            job_data = json.loads(job_raw)
            process_job(job_data)
        except Exception as e:
            print(f"Job failed to process: {str(e)}")

if __name__ == '__main__':
    main()
