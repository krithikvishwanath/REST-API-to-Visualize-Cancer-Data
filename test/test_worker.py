import json
from unittest.mock import patch
from src import worker

DUMMY_JOB = {"job_id": "jjj‑123", "x_field": "BMI", "y_field": "TumorSize"}
SAMPLE_DATA = [
    {"PatientID": 1, "BMI": "24", "TumorSize": "2.5"},
    {"PatientID": 2, "BMI": "30", "TumorSize": "4.2"},
]


@patch("src.worker.r")
@patch("src.worker.generate_plot")
def test_process_job_success(mock_plot, mock_redis):
    mock_plot.return_value = "image‑b64"
    mock_redis.get.return_value = json.dumps(SAMPLE_DATA)

    worker.process_job(DUMMY_JOB)

    mock_redis.hset.assert_any_call(worker.JOB_STATUS, "jjj‑123", "processing")
    mock_redis.hset.assert_any_call(worker.JOB_RESULT, "jjj‑123", "image‑b64")
    mock_redis.hset.assert_any_call(worker.JOB_STATUS, "jjj‑123", "completed")
