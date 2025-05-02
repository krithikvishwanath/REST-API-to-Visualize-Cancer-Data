from src import jobs


def test_extract_fields_valid():
    data = [
        {"PatientID": 1, "BMI": "23.5", "TumorSize": "2.1"},
        {"PatientID": 2, "BMI": "25.0", "TumorSize": "3.8"},
        {"PatientID": 3, "BMI": "27.3", "TumorSize": "4.5"},
    ]
    xs, ys = jobs.extract_fields(data, "BMI", "TumorSize")
    assert len(xs) == len(ys) == 3


def test_generate_scatter_plot_returns_base64():
    b64 = jobs.generate_scatter([1, 2], [3, 4], "x", "y")
    # A Base‑64 PNG is typically a few KB, so > 100 chars is a safe sanity check
    assert isinstance(b64, str) and len(b64) > 100
