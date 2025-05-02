# test/test_flask_api.py

import pytest
import json
from src.flask_api import app, r, RAW_DATA_KEY

@pytest.fixture
def client():
    with app.test_client() as client:
        yield client

def test_help_endpoint(client):
    res = client.get('/help')
    assert res.status_code == 200
    assert "/data" in res.get_json()["routes"]

def test_post_and_get_data(client):
    dummy_data = [{"PatientID": 1, "BMI": 22.5, "TumorSize": 3.1}]
    res = client.post('/data', json=dummy_data)
    assert res.status_code == 200

    res = client.get('/data')
    assert res.status_code == 200
    assert res.get_json()[0]["PatientID"] == 1

def test_get_single_record(client):
    res = client.get('/data/1')
    assert res.status_code == 200
    assert res.get_json()["BMI"] == 22.5

def test_delete_data(client):
    res = client.delete('/data')
    assert res.status_code == 200
    assert r.get(RAW_DATA_KEY) is None
