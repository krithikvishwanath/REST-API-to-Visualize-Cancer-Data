# test/test_worker.py

import json
from unittest.mock import patch
from src import worker

dummy_job = {
    "job_id": "test-job-123",
    "x_field": "BMI",
    "y_field": "TumorSize"
}

sample_data = [
    {"PatientID": 1, "BMI": "24", "TumorSize": "2.5"},
    {"PatientID": 2, "BMI": "30", "TumorSize": "4.2"}
]

@patch('src.worker.r')
@patch('src.worker.generate_plot')
def test_process_job_success(mock_plot, mock_redis):
    mock_plot.return_value = "mock_base64_string"
    mock_redis.get.return_value = json.dumps(sample_data)

    worker.process_job(dummy_job)

    mock_redis.hset.assert_any_call(worker.JOB_STATUS, "test-job-123", "processing")
    mock_redis.hset.assert_any_call(worker.JOB_RESULT, "test-job-123", "mock_base64_string")
    mock_redis.hset.assert_any_call(worker.JOB_STATUS, "test-job-123", "completed")
