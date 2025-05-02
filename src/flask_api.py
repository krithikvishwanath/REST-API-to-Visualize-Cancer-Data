import os
import io
import uuid
import json
import base64
from flask import Flask, request, jsonify, send_file
import redis


# ────────────────────────────────────────────────────────────── #
#  Application‑factory pattern keeps tests isolated & configurable
# ────────────────────────────────────────────────────────────── #
def create_app() -> Flask:
    app = Flask(__name__)

    # ---- Redis connection ------------------------------------
    REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
    REDIS_DB   = int(os.getenv("REDIS_DB", 0))
    r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB,
                    decode_responses=True)
    app.config["REDIS_CONN"] = r     # expose for tests

    # ---- Logical table / key names ---------------------------
    RAW_DATA_KEY = "raw_data"
    JOB_QUEUE    = "job_queue"
    JOB_STATUS   = "job_status"
    JOB_RESULT   = "job_result"

    # ---- Helpers ---------------------------------------------
    def _error(msg: str, code: int = 400):
        return jsonify({"error": msg}), code

    # ---- Routes ----------------------------------------------
    @app.route("/help", methods=["GET"])
    def help_page():
        return jsonify({
            "routes": {
                "/help"             : "GET  – describe all routes",
                "/data"             : "POST/GET/DELETE – upload, list or delete dataset",
                "/data/<PatientID>" : "GET  – fetch a single record",
                "/job"              : "POST – submit analysis job (x_field, y_field)",
                "/job/<job_id>"     : "GET  – poll job status",
                "/result/<job_id>"  : "GET  – download generated PNG"
            }
        })

    # ── Dataset ------------------------------------------------
    @app.route("/data", methods=["POST"])
    def upload_data():
        # Accept “proper” JSON or try a best‑effort parse if header is missing
        if request.is_json:
            payload = request.get_json()
        else:
            try:
                payload = json.loads(request.data)
            except Exception:
                return _error("Expected JSON list of records in body.")

        if not isinstance(payload, list):
            return _error("Expected a list[dict] representing the dataset.")

        r.set(RAW_DATA_KEY, json.dumps(payload))
        return jsonify({"message": f"Uploaded {len(payload)} records."})

    @app.route("/data", methods=["GET"])
    def get_all_data():
        data = r.get(RAW_DATA_KEY)
        return jsonify(json.loads(data)) if data else jsonify([])

    @app.route("/data/<patient_id>", methods=["GET"])
    def get_single_record(patient_id):
        data_raw = r.get(RAW_DATA_KEY)
        if not data_raw:
            return _error("No dataset loaded.", 404)
        for rec in json.loads(data_raw):
            if str(rec.get("PatientID")) == str(patient_id):
                return jsonify(rec)
        return _error("Record not found.", 404)

    @app.route("/data", methods=["DELETE"])
    def delete_dataset():
        r.delete(RAW_DATA_KEY)
        return jsonify({"message": "Dataset deleted."})

    # ── Jobs ---------------------------------------------------
    @app.route("/job", methods=["POST"])
    def submit_job():
        payload = request.get_json(silent=True) or {}
        if not {"x_field", "y_field"} <= payload.keys():
            return _error("Fields 'x_field' and 'y_field' are required.")
        job_id = str(uuid.uuid4())
        payload["job_id"] = job_id

        r.hset(JOB_STATUS, job_id, "queued")
        r.rpush(JOB_QUEUE, json.dumps(payload))
        return jsonify({"job_id": job_id, "status": "queued"}), 202

    @app.route("/job/<job_id>", methods=["GET"])
    def poll_job(job_id):
        status = r.hget(JOB_STATUS, job_id)
        if status is None:
            return _error("Job not found.", 404)
        return jsonify({"job_id": job_id, "status": status})

    @app.route("/result/<job_id>", methods=["GET"])
    def download_result(job_id):
        img_b64 = r.hget(JOB_RESULT, job_id)
        if img_b64 is None:
            return _error("Result not available (job still running?)", 404)
        img_bytes = base64.b64decode(img_b64)
        return send_file(io.BytesIO(img_bytes),
                         mimetype="image/png",
                         download_name=f"result_{job_id}.png")

    return app


# ── Allow “python src/flask_api.py” for local dev ──────────────
app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)))
