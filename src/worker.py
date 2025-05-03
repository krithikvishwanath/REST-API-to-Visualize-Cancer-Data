import os, io, json, base64, redis
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns          
import numpy as np 

r = redis.Redis(
    host=os.getenv("REDIS_HOST", "localhost"),
    port=int(os.getenv("REDIS_PORT", 6379)),
    db=int(os.getenv("REDIS_DB", 0)),
    decode_responses=True,
)
RAW_DATA = "raw_data"
J_QUEUE, J_STAT, J_RES = "job_queue", "job_status", "job_result"
RAW_DATA_KEY = RAW_DATA       
JOB_QUEUE     = J_QUEUE
JOB_STATUS    = J_STAT
JOB_RESULT    = J_RES


def _safe_float(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def generate_plot(x_f: str, y_f: str, plot_type: str | None = None) -> str:
    """Return base‑64 PNG of either a scatter (numeric) or bar (categorical)."""
    blob = r.get(RAW_DATA)
    if blob is None:
        raise RuntimeError("Dataset not loaded.")

    df = pd.DataFrame(json.loads(blob))
    if x_f not in df.columns or y_f not in df.columns:
        raise ValueError("Field not found in dataset.")

    # Decide plot style
    x_is_num = pd.api.types.is_numeric_dtype(df[x_f].dropna())
    y_is_num = pd.api.types.is_numeric_dtype(df[y_f].dropna())

    if plot_type == "scatter" or (plot_type is None and x_is_num and y_is_num):
        xs = df[x_f].apply(_safe_float)
        ys = df[y_f].apply(_safe_float)
        mask = xs.notna() & ys.notna()
        if not mask.any():
            raise ValueError("No valid numeric points to plot.")
        xs, ys = xs[mask], ys[mask]

        plt.figure(figsize=(6, 4))
        plt.scatter(xs, ys, s=8, alpha=0.25, linewidths=0)
        plt.xlabel(x_f); plt.ylabel(y_f); plt.title(f"{y_f} vs {x_f}")

    else:
        if not y_is_num:
            raise ValueError("Bar plot needs numeric y_field.")
        tmp = df[[x_f, y_f]].dropna()
        if tmp.empty:
            raise ValueError("No data after dropping NaNs.")
        summary = (
            tmp.groupby(x_f, observed=True)[y_f]
            .mean()
            .sort_values(ascending=False)
        )

        plt.figure(figsize=(7, 4))
        sns.barplot(x=summary.index, y=summary.values, color="#599ad3")
        plt.ylabel(f"Mean {y_f}")
        plt.xlabel(x_f)
        plt.title(f"Mean {y_f} by {x_f}")
        plt.xticks(rotation=45, ha="right")
        
        for idx, val in enumerate(summary.values):
            plt.text(idx, val, f"{val:.1f}", ha="center", va="bottom", fontsize=8)

    plt.tight_layout()
    buf = io.BytesIO()
    plt.savefig(buf, format="png", dpi=150)
    plt.close()
    buf.seek(0)
    return base64.b64encode(buf.read()).decode()


def process_job(job: dict):
    jid   = job.get("job_id")
    x_f   = job.get("x_field")
    y_f   = job.get("y_field")
    ptype = job.get("plot_type")      

    if not all([jid, x_f, y_f]):
        r.hset(J_STAT, jid, "failed: missing fields")
        return

    r.hset(J_STAT, jid, "processing")
    try:
        img_b64 = generate_plot(x_f, y_f, ptype)
        r.hset(J_RES,  jid, img_b64)
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
