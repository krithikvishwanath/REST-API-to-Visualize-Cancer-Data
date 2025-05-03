import os, io, uuid, json, base64, subprocess, tempfile, zipfile
from datetime import datetime
import pandas as pd
from flask import Flask, request, jsonify, send_file
import redis
import matplotlib          # ensure head‑less on the server
matplotlib.use("Agg")


# ─────────────── helper utilities ────────────────
def _error(msg: str, code: int = 400):
    return jsonify({"error": msg}), code


def _fetch_csv_as_records(dataset: str, csv_name: str) -> list[dict]:
    """
    Download <dataset> from Kaggle, extract <csv_name>, return list‑of‑dicts.
    Requires KAGGLE_USERNAME / KAGGLE_KEY env‑vars *or* ~/.kaggle/kaggle.json.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        subprocess.run(
            ["kaggle", "datasets", "download", "-p", tmpdir, "-d", dataset],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        zips = list(os.scandir(tmpdir))
        if not zips:
            raise RuntimeError("Kaggle download produced no files.")
        zip_path = zips[0].path
        with zipfile.ZipFile(zip_path) as zf, zf.open(csv_name) as fh:
            df = pd.read_csv(io.BytesIO(fh.read()))
    return json.loads(df.to_json(orient="records"))


# ──────────────── factory ────────────────────────
def create_app() -> Flask:
    app = Flask(__name__)

    r = redis.Redis(
        host=os.getenv("REDIS_HOST", "localhost"),
        port=int(os.getenv("REDIS_PORT", 6379)),
        db=int(os.getenv("REDIS_DB", 0)),
        decode_responses=True,
    )
    app.config["REDIS_CONN"] = r

    RAW_DATA, J_QUEUE, J_STAT, J_RES = (
        "raw_data",
        "job_queue",
        "job_status",
        "job_result",
    )

    # ── Help ──────────────────────────────────────
    @app.route("/help")
    def help_page():
        return jsonify(
            routes={
                "/help": "GET   – list routes",
                "/data": "POST/GET/DELETE – upload / list / delete dataset",
                "/data/<id>": "GET   – single record by PatientID",
                "/data/load": "POST  – pull CSV from Kaggle (dataset,file)",
                "/job": "POST  – submit job {'x_field','y_field'}",
                "/job/<job_id>": "GET   – poll status",
                "/result/<job_id>": "GET   – fetch PNG result",
                "/admin/backup": "POST  – trigger an immediate Redis snapshot",
            }
        )

    # ── DATA CRUD ─────────────────────────────────
    @app.route("/data", methods=["POST"])
    def upload_data():
        body = request.get_json(silent=True)
        if not isinstance(body, list):
            return _error("Expected JSON list of records.")
        r.set(RAW_DATA, json.dumps(body))
        return jsonify(message=f"Uploaded {len(body)} records.")

    @app.route("/data/load", methods=["POST"])
    def load_from_kaggle():
        info = request.get_json(silent=True) or {}
        dataset, csv = info.get("dataset"), info.get("file")
        if not (dataset and csv):
            return _error("'dataset' and 'file' required.")
        try:
            records = _fetch_csv_as_records(dataset, csv)
        except Exception as e:
            return _error(f"Download failed: {e}", 500)
        r.set(RAW_DATA, json.dumps(records))
        return jsonify(
            message=f"Loaded {len(records)} rows from {dataset}/{csv}."
        )

    @app.route("/data", methods=["GET"])
    def list_data():
        blob = r.get(RAW_DATA)
        return jsonify(json.loads(blob)) if blob else jsonify([])

    @app.route("/data/<patient_id>")
    def single_record(patient_id):
        blob = r.get(RAW_DATA)
        if blob is None:
            return _error("No dataset loaded.", 404)
        for rec in json.loads(blob):
            if str(rec.get("PatientID")) == str(patient_id):
                return jsonify(rec)
        return _error("Record not found.", 404)

    @app.route("/data", methods=["DELETE"])
    def delete_data():
        r.delete(RAW_DATA)
        return jsonify(message="Dataset deleted.")

    # ── JOBS ──────────────────────────────────────
    @app.route("/job", methods=["POST"])
    def submit_job():
        body = request.get_json(silent=True) or {}
        if not {"x_field", "y_field"} <= body.keys():
            return _error("Need 'x_field' and 'y_field'.")
        jid = str(uuid.uuid4())
        body["job_id"] = jid
        r.hset(J_STAT, jid, "queued")
        r.rpush(J_QUEUE, json.dumps(body))
        return jsonify(job_id=jid, status="queued"), 202

    @app.route("/job/<job_id>")
    def job_status(job_id):
        stat = r.hget(J_STAT, job_id)
        return (
            _error("Job not found.", 404)
            if stat is None
            else jsonify(job_id=job_id, status=stat)
        )

    @app.route("/result/<job_id>")
    def job_result(job_id):
        img_b64 = r.hget(J_RES, job_id)
        if img_b64 is None:
            return _error("Result not ready.", 404)
        img_bytes = base64.b64decode(img_b64)
        return send_file(
            io.BytesIO(img_bytes),
            mimetype="image/png",
            download_name=f"result_{job_id}.png",
        )

    # ── ADMIN / BACKUP ────────────────────────────
    @app.route("/admin/backup", methods=["POST"])
    def manual_backup():
        """
        Trigger a background RDB snapshot (BGSAVE).  The main Redis container
        writes it to /data/dump.rdb, after which the side‑car copy process
        (defined in the Kubernetes manifest) archives the file.
        """
        try:
            r.bgsave()
        except redis.ResponseError as exc:
            # Ignore "Background save already in progress"
            if "in progress" in str(exc):
                return _error("Backup already running – try later.", 409)
            return _error(f"Backup failed: {exc}", 500)

        ts = datetime.utcnow().isoformat(timespec="seconds") + "Z"
        return jsonify(message=f"BGSAVE started at {ts}"), 202

    return app


app = create_app()
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)))
