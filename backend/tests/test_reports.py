import uuid

from sqlalchemy import select

from app.models.report import Report


def test_create_report_authenticated_and_persisted(client, auth_header, db_session):
    headers = auth_header("patient@example.com")
    payload = {
        "title": "Comprehensive Blood & Metabolic Test",
        "rows": [
            {
                "raw_name": "Hemoglobin",
                "value": 11.2,
                "unit": "g/dL",
                "reference_range": "13.0 - 17.0",
            },
            {
                "raw_name": "Fasting Glucose",
                "value": 135,
                "unit": "mg/dL",
                "reference_range": "70 - 99",
            },
            {
                "raw_name": "SGPT",
                "value": 25,
                "unit": "U/L",
                "reference_range": "7 - 56",
            },
        ],
    }

    res = client.post("/api/v1/reports", json=payload, headers=headers)
    assert res.status_code == 201
    data = res.json()

    assert data["title"] == "Comprehensive Blood & Metabolic Test"
    assert len(data["results"]) == 3

    # Verify calculation engine flags
    flags = {r["raw_name"]: r["flag"] for r in data["results"]}
    assert flags["Hemoglobin"] == "low"
    assert flags["Fasting Glucose"] == "high"
    assert flags["SGPT"] == "normal"

    assert data["summary"]["low"] == 1
    assert data["summary"]["high"] == 1
    assert data["summary"]["normal"] == 1

    # Verify report is actually saved in the database
    report_id = uuid.UUID(data["id"])
    saved_report = db_session.scalar(select(Report).where(Report.id == report_id))
    assert saved_report is not None
    assert saved_report.title == "Comprehensive Blood & Metabolic Test"
    assert len(saved_report.results) == 3


def test_reports_require_authentication(client):
    payload = {
        "title": "Test",
        "rows": [{"raw_name": "Hb", "value": 12, "reference_range": "10-15"}],
    }
    res = client.post("/api/v1/reports", json=payload)
    assert res.status_code == 401
    assert res.json()["error"]["code"] == "unauthenticated"


def test_reports_input_validation(client, auth_header):
    headers = auth_header("validator@example.com")

    # Empty rows rejected
    res = client.post("/api/v1/reports", json={"rows": []}, headers=headers)
    assert res.status_code == 422

    # Missing raw_name rejected
    res = client.post(
        "/api/v1/reports",
        json={"rows": [{"raw_name": "", "value": 10}]},
        headers=headers,
    )
    assert res.status_code == 422


def test_list_and_get_reports_multi_tenant_isolation(client, auth_header):
    user1_headers = auth_header("user1@example.com")
    user2_headers = auth_header("user2@example.com")

    payload1 = {
        "title": "User1 Report",
        "rows": [{"raw_name": "Hemoglobin", "value": 14.5, "reference_range": "13.0 - 17.0"}],
    }
    payload2 = {
        "title": "User2 Report",
        "rows": [{"raw_name": "Glucose", "value": 85, "reference_range": "70 - 100"}],
    }

    res1 = client.post("/api/v1/reports", json=payload1, headers=user1_headers)
    assert res1.status_code == 201
    user1_report_id = res1.json()["id"]

    res2 = client.post("/api/v1/reports", json=payload2, headers=user2_headers)
    assert res2.status_code == 201
    user2_report_id = res2.json()["id"]
    assert user2_report_id

    # User 1 list only shows user 1's reports
    list1 = client.get("/api/v1/reports", headers=user1_headers).json()
    assert len(list1) == 1
    assert list1[0]["title"] == "User1 Report"

    # User 2 list only shows user 2's reports
    list2 = client.get("/api/v1/reports", headers=user2_headers).json()
    assert len(list2) == 1
    assert list2[0]["title"] == "User2 Report"

    # User 2 CANNOT access User 1's report (Multi-Tenant Isolation -> 404)
    forbidden_get = client.get(f"/api/v1/reports/{user1_report_id}", headers=user2_headers)
    assert forbidden_get.status_code == 404
    assert forbidden_get.json()["error"]["code"] == "not_found"

    # User 1 CAN access their own report
    ok_get = client.get(f"/api/v1/reports/{user1_report_id}", headers=user1_headers)
    assert ok_get.status_code == 200
    assert ok_get.json()["id"] == user1_report_id


def test_delete_report(client, auth_header):
    headers = auth_header("delete_user@example.com")
    payload = {
        "title": "To Delete",
        "rows": [{"raw_name": "WBC", "value": 6.5, "reference_range": "4.0 - 11.0"}],
    }

    created = client.post("/api/v1/reports", json=payload, headers=headers).json()
    report_id = created["id"]

    del_res = client.delete(f"/api/v1/reports/{report_id}", headers=headers)
    assert del_res.status_code == 204

    # Now verify it's gone
    get_res = client.get(f"/api/v1/reports/{report_id}", headers=headers)
    assert get_res.status_code == 404
