from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health():
    assert client.get("/health").json() == {"status": "ok"}


def test_analyze_flags_and_summary():
    body = {"rows": [
        {"raw_name": "Hb", "value": 11.2, "unit": "g/dL", "reference_range": "13.0 - 17.0"},
        {"raw_name": "LDL-C", "value": 130, "unit": "mg/dL", "reference_range": "< 100"},
        {"raw_name": "SGPT", "value": "30", "unit": "U/L", "reference_range": "7 - 56"},
        {"raw_name": "Mystery Test", "value": 5, "reference_range": "1 - 10"},
        {"raw_name": "TSH", "value": 2.0},
    ]}
    data = client.post("/api/v1/analyze", json=body).json()
    flags = [r["flag"] for r in data["results"]]
    assert flags == ["low", "high", "normal", "normal", "unknown"]
    assert data["results"][4]["range_source"] == "unavailable"
    assert data["summary"] == {"total": 5, "low": 1, "normal": 2, "high": 1, "unknown": 1, "unmatched": 1}
    assert "does not diagnose" in data["disclaimer"]


def test_analyze_rejects_empty_and_bad_input():
    assert client.post("/api/v1/analyze", json={"rows": []}).status_code == 422
    assert client.post("/api/v1/analyze", json={"rows": [{"raw_name": "", "value": 1}]}).status_code == 422
    too_many = {"rows": [{"raw_name": "Hb", "value": 1}] * 201}
    assert client.post("/api/v1/analyze", json=too_many).status_code == 422
