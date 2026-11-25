import os
from typing import Any
from urllib.parse import quote

import requests


DEFAULT_API_URL = os.getenv("CLINIQ_API_URL") or os.getenv("API_BASE_URL") or "http://127.0.0.1:8000"


class CliniqApiClient:
    """Thin HTTP client for communicating with the CLINIQ-AI FastAPI backend."""

    def __init__(self, base_url: str | None = None, timeout: int = 12):
        raw_url = (base_url or DEFAULT_API_URL).strip()
        self.base_url = raw_url.rstrip("/")
        self.timeout = timeout
        self._session = requests.Session()

    def _request(
        self,
        method: str,
        path: str,
        timeout: int | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        url = f"{self.base_url}{path}"
        try:
            response = self._session.request(
                method=method,
                url=url,
                timeout=timeout or self.timeout,
                **kwargs,
            )
            try:
                payload = response.json()
            except ValueError:
                payload = None

            if response.ok:
                return {
                    "ok": True,
                    "status_code": response.status_code,
                    "data": payload if payload is not None else {},
                    "error": None,
                }

            detail = (
                payload.get("detail")
                if isinstance(payload, dict) and payload.get("detail")
                else response.text or f"HTTP {response.status_code}"
            )
            return {
                "ok": False,
                "status_code": response.status_code,
                "data": payload,
                "error": f"Backend returned {response.status_code}: {detail}",
            }

        except requests.exceptions.ConnectionError:
            return {
                "ok": False,
                "status_code": None,
                "data": None,
                "error": (
                    f"Cannot connect to FastAPI backend at {self.base_url}. "
                    "Make sure uvicorn is running."
                ),
            }
        except requests.exceptions.Timeout:
            return {
                "ok": False,
                "status_code": None,
                "data": None,
                "error": f"Request to {self.base_url}{path} timed out.",
            }
        except requests.exceptions.RequestException as exc:
            return {
                "ok": False,
                "status_code": None,
                "data": None,
                "error": f"Request failed: {exc}",
            }

    def check_health(self) -> dict[str, Any]:
        return self._request("GET", "/health", timeout=4)

    def get_dashboard_overview(self) -> dict[str, Any]:
        return self._request("GET", "/dashboard/overview")

    def list_patients(self) -> dict[str, Any]:
        return self._request("GET", "/patients")

    def get_patient(self, patient_id: str) -> dict[str, Any]:
        return self._request("GET", f"/patients/{quote(patient_id, safe='')}")

    def get_patient_reports(
        self,
        patient_id: str,
        order: str = "asc",
        include_pages: bool = False,
    ) -> dict[str, Any]:
        return self._request(
            "GET",
            f"/patients/{quote(patient_id, safe='')}/reports",
            params={"order": order, "include_pages": str(include_pages).lower()},
        )

    def get_patient_timeline(self, patient_id: str) -> dict[str, Any]:
        return self._request("GET", f"/patients/{quote(patient_id, safe='')}/timeline")

    def compare_patient_reports(self, patient_id: str) -> dict[str, Any]:
        return self._request("GET", f"/patients/{quote(patient_id, safe='')}/compare")

    def get_patient_analysis(self, patient_id: str) -> dict[str, Any]:
        return self._request("GET", f"/patients/{quote(patient_id, safe='')}/analysis")

    def get_report(self, report_id: int) -> dict[str, Any]:
        return self._request("GET", f"/reports/{int(report_id)}")

    def get_report_analysis(self, report_id: int) -> dict[str, Any]:
        return self._request("GET", f"/reports/{int(report_id)}/analysis")

    def upload_pdfs(
        self,
        uploaded_files: list[tuple[str, bytes]],
        patient_id: str | None = None,
    ) -> dict[str, Any]:
        multipart_files = [
            ("files", (filename, file_bytes, "application/pdf"))
            for filename, file_bytes in uploaded_files
        ]
        form_data = {}
        if patient_id and patient_id.strip():
            form_data["patient_id"] = patient_id.strip()

        return self._request(
            "POST",
            "/upload-pdfs",
            files=multipart_files,
            data=form_data or None,
            timeout=90,
        )
