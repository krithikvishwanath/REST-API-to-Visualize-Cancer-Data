import pytest
import json
from src.flask_api import create_app

app = create_app()
r = app.config["REDIS_CONN"]
RAW_DATA_KEY = "raw_data"


@pytest.fixture
def client():
    with app.test_client() as c:
        yield c
    r.flushdb()          # clean slate after each test


def test_help_endpoint(client):
    res = client.get("/help")
    assert res.status_code == 200
    assert "/data" in res.get_json()["routes"]


def test_post_and_get_data(client):
    dummy = [{"PatientID": 1, "BMI": 22.5, "TumorSize": 3.1}]
    assert client.post("/data", json=dummy).status_code == 200
    res = client.get("/data")
    assert res.status_code == 200
    assert res.get_json()[0]["PatientID"] == 1


def test_get_single_record(client):
    client.post("/data", json=[{"PatientID": 42, "BMI": 20}])
    res = client.get("/data/42")
    assert res.status_code == 200
    assert res.get_json()["BMI"] == 20


def test_delete_data(client):
    client.post("/data", json=[{"PatientID": 99}])
    assert client.delete("/data").status_code == 200
    assert r.get(RAW_DATA_KEY) is None
