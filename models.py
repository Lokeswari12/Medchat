from datetime import datetime
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class Patient(db.Model):
    __tablename__ = "patients"
    id             = db.Column(db.Integer, primary_key=True)
    name           = db.Column(db.String(120), nullable=False)
    age            = db.Column(db.Integer)
    gender         = db.Column(db.String(20))
    email          = db.Column(db.String(200))
    family_history = db.Column(db.Text)          # JSON string (new)
    created_at     = db.Column(db.DateTime, default=datetime.utcnow)
    analyses       = db.relationship("Analysis", backref="patient", lazy=True)

    def to_dict(self):
        import json
        def safe_json(val):
            try:
                return json.loads(val) if val else {}
            except Exception:
                return {}
        return {
            "id": self.id,
            "name": self.name,
            "age": self.age,
            "gender": self.gender,
            "email": self.email,
            "family_history": safe_json(self.family_history),
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M"),
        }


class Analysis(db.Model):
    __tablename__ = "analyses"
    id               = db.Column(db.Integer, primary_key=True)
    patient_id       = db.Column(db.Integer, db.ForeignKey("patients.id"), nullable=False)
    filename         = db.Column(db.String(255))
    report_text      = db.Column(db.Text)
    cancer_type      = db.Column(db.String(100))
    risk_level       = db.Column(db.String(20))
    confidence_score = db.Column(db.Float, default=0.0)
    findings         = db.Column(db.Text)        # JSON string
    biomarkers       = db.Column(db.Text)        # JSON string
    recommendations  = db.Column(db.Text)        # JSON string
    doctor_questions = db.Column(db.Text)        # JSON string (new)
    summary          = db.Column(db.Text)
    analyzed_at      = db.Column(db.DateTime, default=datetime.utcnow)
    status           = db.Column(db.String(20), default="completed")

    def to_dict(self):
        import json
        def safe_json(val):
            try:
                return json.loads(val) if val else []
            except Exception:
                return [val] if val else []
        return {
            "id": self.id,
            "patient_id": self.patient_id,
            "patient_name": self.patient.name if self.patient else "Unknown",
            "patient_age": self.patient.age if self.patient else None,
            "patient_gender": self.patient.gender if self.patient else None,
            "filename": self.filename,
            "cancer_type": self.cancer_type,
            "risk_level": self.risk_level,
            "confidence_score": self.confidence_score,
            "findings": safe_json(self.findings),
            "biomarkers": safe_json(self.biomarkers),
            "recommendations": safe_json(self.recommendations),
            "doctor_questions": safe_json(self.doctor_questions),
            "summary": self.summary,
            "analyzed_at": self.analyzed_at.strftime("%Y-%m-%d %H:%M"),
            "status": self.status,
        }
