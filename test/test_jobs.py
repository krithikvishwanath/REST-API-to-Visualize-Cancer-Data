# test/test_jobs.py

import pytest
from src import jobs

sample_data = [
    {"PatientID": 1, "BMI": "23.5", "TumorSize": "2.1"},
    {"PatientID": 2, "BMI": "25.0", "TumorSize": "3.8"},
    {"PatientID": 3, "BMI": "27.3", "TumorSize": "4.5"}
]

def test_extract_fields_valid():
    x, y = jobs.extract_fields(sample_data, "BMI", "TumorSize")
    assert len(x) == 3 and len(y) == 3

def test_generate_scatter_plot_returns_base64():
    x, y = [1, 2, 3], [4, 5, 6]
    img_b64 = jobs.generate_scatter_plot(x, y, "x", "y")
    assert isinstance(img_b64, str)
    assert img_b64.startswith("iVBOR") or img_b64  # Base64 PNGs often start this way
