from datetime import datetime, timezone

from sqlalchemy import Column, Date, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from backend.database import Base


def utc_now():
    return datetime.now(timezone.utc)


class Patient(Base):
    __tablename__ = "patients"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(String(128), unique=True, index=True, nullable=False)
    name = Column(String(255), nullable=True)
    age = Column(String(64), nullable=True)
    sex = Column(String(64), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    reports = relationship(
        "MedicalReport",
        back_populates="patient",
        cascade="all, delete-orphan",
    )


class MedicalReport(Base):
    __tablename__ = "medical_reports"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(
        String(128),
        ForeignKey("patients.patient_id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    filename = Column(String(255), nullable=False)
    page_count = Column(Integer, nullable=False, default=0)
    raw_text = Column(Text, nullable=False, default="")
    pages_json = Column(Text, nullable=True)

    patient_name = Column(String(255), nullable=True)
    patient_age = Column(String(64), nullable=True)
    patient_sex = Column(String(64), nullable=True)
    study_name = Column(String(255), nullable=True)
    study_date = Column(String(128), nullable=True)
    study_date_parsed = Column(Date, index=True, nullable=True)
    findings = Column(Text, nullable=True)
    impression = Column(Text, nullable=True)

    clinical_summary = Column(Text, nullable=True)
    abnormal_flags_json = Column(Text, nullable=True)
    severity = Column(String(64), nullable=True, default="normal")

    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    patient = relationship("Patient", back_populates="reports")
