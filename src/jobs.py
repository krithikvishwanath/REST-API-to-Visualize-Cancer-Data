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


def _safe_float(v): 
    try: return float(v)
    except (TypeError, ValueError): return None


def load_data():
    blob = r.get(RAW_DATA)
    if blob is None:
        raise RuntimeError("Dataset not loaded.")
    return json.loads(blob)


def extract_fields(data, x_f, y_f):
    xs, ys = [], []
    for row in data:
        x, y = _safe_float(row.get(x_f)), _safe_float(row.get(y_f))
        if x is not None and y is not None:
            xs.append(x); ys.append(y)
    if not xs:
        raise ValueError(f"No numeric data for {x_f}/{y_f}.")
    return xs, ys


def generate_scatter(xs, ys, x_lbl, y_lbl, title=None):
    fig, ax = plt.subplots()
    ax.scatter(xs, ys, alpha=0.7)
    ax.set(xlabel=x_lbl, ylabel=y_lbl, title=title or f"{y_lbl} vs {x_lbl}")
    buf = io.BytesIO()
    fig.savefig(buf, format="png"); plt.close(fig); buf.seek(0)
    return base64.b64encode(buf.read()).decode()


def run_job(x_field, y_field):
    data = load_data()
    xs, ys = extract_fields(data, x_field, y_field)
    return generate_scatter(xs, ys, x_field, y_field)
