# src/flask_api.py

from flask import Flask, request, jsonify, send_file
import redis
import json
import uuid
import io
import base64

app = Flask(__name__)
r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)

# Keys for redis "tables"
RAW_DATA_KEY = "raw_data"
JOB_QUEUE = "job_queue"
JOB_STATUS = "job_status"
JOB_RESULT = "job_result"

@app.route('/help', methods=['GET'])
def help():
    return jsonify({
        "routes": {
            "/help": "GET - Show available routes",
            "/data": "POST/GET/DELETE - Manage dataset",
            "/data/<PatientID>": "GET - Get single record",
            "/job": "POST - Submit analysis job",
            "/job/<job_id>": "GET - Get job status",
            "/result/<job_id>": "GET - Get image result"
        }
    })

@app.route('/data', methods=['POST'])
def upload_data():
    try:
        data = request.get_json()
        if not isinstance(data, list):
            return jsonify({"error": "Expected a list of records"}), 400
        r.set(RAW_DATA_KEY, json.dumps(data))
        return jsonify({"message": f"Uploaded {len(data)} records."}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/data', methods=['GET'])
def get_data():
    data = r.get(RAW_DATA_KEY)
    return jsonify(json.loads(data)) if data else jsonify([])

@app.route('/data/<patient_id>', methods=['GET'])
def get_record(patient_id):
    data = r.get(RAW_DATA_KEY)
    if not data:
        return jsonify({"error": "No data found."}), 404
    records = json.loads(data)
    for record in records:
        if str(record.get("PatientID")) == str(patient_id):
            return jsonify(record)
    return jsonify({"error": "Record not found."}), 404

@app.route('/data', methods=['DELETE'])
def delete_data():
    r.delete(RAW_DATA_KEY)
    return jsonify({"message": "Dataset deleted."}), 200

@app.route('/job', methods=['POST'])
def submit_job():
    try:
        job_details = request.get_json()
        job_id = str(uuid.uuid4())
        job_details['job_id'] = job_id

        # Store job status and queue it
        r.hset(JOB_STATUS, job_id, "queued")
        r.rpush(JOB_QUEUE, json.dumps(job_details))
        return jsonify({"message": "Job submitted", "job_id": job_id}), 202
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/job/<job_id>', methods=['GET'])
def job_status(job_id):
    status = r.hget(JOB_STATUS, job_id)
    return jsonify({"job_id": job_id, "status": status}) if status else jsonify({"error": "Job not found"}), 404

@app.route('/result/<job_id>', methods=['GET'])
def get_result(job_id):
    img_base64 = r.hget(JOB_RESULT, job_id)
    if not img_base64:
        return jsonify({"error": "Result not found or job not completed"}), 404

    # Decode and send image
    image_data = base64.b64decode(img_base64)
    return send_file(io.BytesIO(image_data), mimetype='image/png', download_name=f'result_{job_id}.png')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
