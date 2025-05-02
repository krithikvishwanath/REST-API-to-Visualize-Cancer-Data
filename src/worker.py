import os
import io
import json
import base64
import redis
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
REDIS_DB   = int(os.getenv("REDIS_DB", 0))

r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB,
                decode_responses=True)

RAW_DATA_KEY = "raw_data"
JOB_QUEUE    = "job_queue"
JOB_STATUS   = "job_status"
JOB_RESULT   = "job_result"


def _safe_float(val):
    try:
        return float(val)
    except (TypeError, ValueError):
        return None


def generate_plot(x_field, y_field):
    data_raw = r.get(RAW_DATA_KEY)
    if data_raw is None:
        raise RuntimeError("Dataset not loaded.")
    data = json.loads(data_raw)

    xs, ys = [], []
    for row in data:
        x, y = _safe_float(row.get(x_field)), _safe_float(row.get(y_field))
        if x is not None and y is not None:
            xs.append(x)
            ys.append(y)
    if not xs:
        raise ValueError("No valid points to plot.")

    fig, ax = plt.subplots()
    ax.scatter(xs, ys, alpha=0.7)
    ax.set_xlabel(x_field)
    ax.set_ylabel(y_field)
    ax.set_title(f"{y_field} vs {x_field}")
    buf = io.BytesIO()
    fig.savefig(buf, format="png")
    plt.close(fig)
    buf.seek(0)
    return base64.b64encode(buf.read()).decode()


def process_job(job):
    job_id = job.get("job_id")
    x_field = job.get("x_field")
    y_field = job.get("y_field")

    if not all([job_id, x_field, y_field]):
        r.hset(JOB_STATUS, job_id, "failed: missing fields")
        return

    r.hset(JOB_STATUS, job_id, "processing")
    try:
        img_b64 = generate_plot(x_field, y_field)
        r.hset(JOB_RESULT, job_id, img_b64)
        r.hset(JOB_STATUS, job_id, "completed")
    except Exception as exc:
        r.hset(JOB_STATUS, job_id, f"failed: {exc}")


def main():
    print("Worker ready – waiting for jobs.")
    while True:
        _, raw = r.blpop(JOB_QUEUE)        # blocks until job arrives
        try:
            process_job(json.loads(raw))
        except Exception as e:
            print(f"Job processing error: {e}")


if __name__ == "__main__":
    main()
