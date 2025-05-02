import os, io, json, base64, redis
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt


r = redis.Redis(
    host=os.getenv("REDIS_HOST", "localhost"),
    port=int(os.getenv("REDIS_PORT", 6379)),
    db=int(os.getenv("REDIS_DB", 0)),
    decode_responses=True,
)
RAW_DATA = "raw_data"
J_QUEUE, J_STAT, J_RES = "job_queue", "job_status", "job_result"
RAW_DATA_KEY = RAW_DATA       # tests import this name
JOB_QUEUE     = J_QUEUE
JOB_STATUS    = J_STAT
JOB_RESULT    = J_RES


def _safe_float(v):
    try: return float(v)
    except (TypeError, ValueError): return None


def generate_plot(x_f, y_f):
    blob = r.get(RAW_DATA)
    if blob is None:
        raise RuntimeError("Dataset not loaded.")
    data = json.loads(blob)

    xs, ys = [], []
    for row in data:
        x, y = _safe_float(row.get(x_f)), _safe_float(row.get(y_f))
        if x is not None and y is not None:
            xs.append(x); ys.append(y)
    if not xs:
        raise ValueError("No valid points to plot.")

    fig, ax = plt.subplots()
    ax.scatter(xs, ys, alpha=0.7)
    ax.set(xlabel=x_f, ylabel=y_f, title=f"{y_f} vs {x_f}")
    buf = io.BytesIO()
    fig.savefig(buf, format="png"); plt.close(fig); buf.seek(0)
    return base64.b64encode(buf.read()).decode()


def process_job(job):
    jid, x_f, y_f = job.get("job_id"), job.get("x_field"), job.get("y_field")
    if not all([jid, x_f, y_f]):
        r.hset(J_STAT, jid, "failed: missing fields"); return
    r.hset(J_STAT, jid, "processing")
    try:
        img_b64 = generate_plot(x_f, y_f)
        r.hset(J_RES, jid, img_b64)
        r.hset(J_STAT, jid, "completed")
    except Exception as exc:
        r.hset(J_STAT, jid, f"failed: {exc}")


def main():
    print("Worker ready.")
    while True:
        _, raw = r.blpop(J_QUEUE)
        try:
            process_job(json.loads(raw))
        except Exception as e:
            print(f"Uncaught worker error: {e}")


if __name__ == "__main__":
    main()
