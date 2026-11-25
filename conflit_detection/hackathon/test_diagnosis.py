def check_diagnosis(admission_diagnosis, lab_result):
    if admission_diagnosis != lab_result:
        return {"status": "CONFLICT", "needs_human": True}
    return {"status": "SAFE", "needs_human": False}

def test_diagnosis_conflict():
    result = check_diagnosis("Diabetes", "No Diabetes")
    assert result["status"] == "CONFLICT"
    assert result["needs_human"] == True

def test_diagnosis_safe():
    result = check_diagnosis("Diabetes", "Diabetes")
    assert result["status"] == "SAFE"
    assert result["needs_human"] == False