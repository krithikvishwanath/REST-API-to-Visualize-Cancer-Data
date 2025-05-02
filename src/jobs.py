import os
import io
import json
import base64
import redis
import matplotlib
matplotlib.use("Agg")          # head‑less backend
import matplotlib.pyplot as plt


REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
REDIS_DB   = int(os.getenv("REDIS_DB", 0))

r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB,
                decode_responses=True)

RAW_DATA_KEY = "raw_data"


def _safe_float(value):
    try:
        return float(value)
    except (ValueError, TypeError):
        return None


def load_data():
    data_raw = r.get(RAW_DATA_KEY)
    if data_raw is None:
        raise RuntimeError("Dataset not loaded; POST /data first.")
    return json.loads(data_raw)


def extract_fields(data, x_field, y_field):
    xs, ys = [], []
    for row in data:
        x, y = _safe_float(row.get(x_field)), _safe_float(row.get(y_field))
        if x is not None and y is not None:
            xs.append(x)
            ys.append(y)
    if not xs:
        raise ValueError(f"No numeric data for {x_field}/{y_field}.")
    return xs, ys


def generate_scatter_plot(xs, ys, x_lbl, y_lbl, title=None):
    fig, ax = plt.subplots()
    ax.scatter(xs, ys, alpha=0.7)
    ax.set_xlabel(x_lbl)
    ax.set_ylabel(y_lbl)
    ax.set_title(title or f"{y_lbl} vs {x_lbl}")
    buf = io.BytesIO()
    fig.savefig(buf, format="png")
    plt.close(fig)
    buf.seek(0)
    return base64.b64encode(buf.read()).decode()


def run_job(x_field: str, y_field: str) -> str:
    data = load_data()
    xs, ys = extract_fields(data, x_field, y_field)
    return generate_scatter_plot(xs, ys, x_field, y_field)
