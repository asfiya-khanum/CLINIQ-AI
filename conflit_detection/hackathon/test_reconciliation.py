from agent import reconcile
from agent import check_medication_conflict

def test_conflict_is_detected():
    purana = {"diagnosis": "Diabetes", "medicine": "Metformin", "admit_date": "2024-01-01", "discharge_date": "2024-01-05", "hemoglobin": 12}
    naya = {"diagnosis": "No Diabetes", "medicine": "Metformin", "admit_date": "2024-01-01", "discharge_date": "2024-01-05", "hemoglobin": 12}
    result = reconcile(purana, naya)
    assert "CONFLICT" in result["status"]
    assert len(result["conflicts"]) > 0

def test_safe_case():
    purana = {"diagnosis": "Diabetes", "medicine": "Metformin", "admit_date": "2024-01-01", "discharge_date": "2024-01-05", "hemoglobin": 12}
    naya = {"diagnosis": "Diabetes", "medicine": "Metformin", "admit_date": "2024-01-01", "discharge_date": "2024-01-05", "hemoglobin": 12}
    result = reconcile(purana, naya)
    assert result["status"] == "SAFE"
    


def test_medication_conflict():

    old_record = {
        "medication": "Medicine A",
        "status": "active"
    }

    new_record = {
        "medication": "Medicine A",
        "status": "discontinued"
    }

    result = check_medication_conflict(
        old_record,
        new_record
    )

    assert result["status"] == "CONFLICT"
    assert result["needs_human_review"] is True