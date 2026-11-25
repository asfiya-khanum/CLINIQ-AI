def reconcile(purana, naya):
    conflicts = []

    for key in purana:
        if purana[key] != naya.get(key):
            conflicts.append(
                f"{key}: purana={purana[key]} naya={naya.get(key)}"
            )

    if conflicts:
        return {
            "status": "CONFLICT",
            "conflicts": conflicts
        }
    else:
        return {
            "status": "SAFE",
            "conflicts": []
        }


def check_medication_conflict(old_record, new_record):
    old_med = old_record.get("medication", "").lower()
    new_med = new_record.get("medication", "").lower()

    old_status = old_record.get("status", "").lower()
    new_status = new_record.get("status", "").lower()

    if old_med == new_med and old_status != new_status:
        return {
            "status": "CONFLICT",
            "type": "MEDICATION_CONFLICT",
            "medication": old_med,
            "old_status": old_status,
            "new_status": new_status,
            "needs_human_review": True
        }

    return {
        "status": "SAFE",
        "needs_human_review": False
    }


def check_missing_information(record):
    missing = []

    if not record.get("diagnosis"):
        missing.append("diagnosis")

    if not record.get("date"):
        missing.append("date")

    if not record.get("source"):
        missing.append("source")

    if missing:
        return {
            "status": "INCOMPLETE",
            "missing_fields": missing,
            "needs_human_review": True
        }

    return {
        "status": "COMPLETE",
        "missing_fields": [],
        "needs_human_review": False
    }
if __name__ == "__main__":
    old_record = {
        "medication": "Medicine A",
        "status": "active"
    }

    new_record = {
        "medication": "Medicine A",
        "status": "stopped"
    }

    result = check_medication_conflict(
        old_record,
        new_record
    )

    print(result)
    record = {
    "diagnosis": "",
    "date": "2026-11-25",
    "source": "Hospital"
}

#missing_result = check_missing_information(record)
record = {
    "diagnosis": "",
    "date": "2026-11-25",
    "source": "Hospital"
}

missing_result = check_missing_information(record)
print(missing_result)







