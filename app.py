"""
CancerScreen AI – Main Flask Application
"""
import os
import json
from datetime import datetime
from flask import (Flask, render_template, request, redirect,
                   url_for, flash, jsonify, abort, session)
from werkzeug.utils import secure_filename

import csv
import io
import config
from models import db, Patient, Analysis
from document_processor import extract_text
from medgemma_service import (analyze_report, chat as medgemma_chat,
                               chat_with_report, calculate_risk, check_symptoms)

# ──────────────────────────── App Setup ──────────────────────────────
app = Flask(__name__)
app.config.from_object(config)
app.config["SQLALCHEMY_DATABASE_URI"] = config.SQLALCHEMY_DATABASE_URI
app.config["SECRET_KEY"]              = config.SECRET_KEY
app.config["UPLOAD_FOLDER"]          = config.UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"]     = config.MAX_CONTENT_LENGTH

db.init_app(app)

os.makedirs(config.UPLOAD_FOLDER, exist_ok=True)
os.makedirs(os.path.join(os.path.dirname(__file__), "instance"), exist_ok=True)

with app.app_context():
    db.create_all()
    # Migrate existing DB — add new columns if missing
    from sqlalchemy import text
    with db.engine.connect() as _conn:
        for _tbl, _col, _type in [
            ("patients",  "family_history",  "TEXT"),
            ("analyses",  "doctor_questions","TEXT"),
        ]:
            try:
                _conn.execute(text(f"ALTER TABLE {_tbl} ADD COLUMN {_col} {_type}"))
                _conn.commit()
            except Exception:
                pass  # column already exists


def allowed_file(filename: str) -> bool:
    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower() in config.ALLOWED_EXTENSIONS
    )


# ──────────────────────────── Web Routes ─────────────────────────────

@app.route("/")
def index():
    total   = Analysis.query.count()
    high    = Analysis.query.filter(Analysis.risk_level.in_(["High", "Critical"])).count()
    patients = Patient.query.count()
    return render_template("index.html", total=total, high=high, patients=patients)


@app.route("/dashboard")
def dashboard():
    analyses = [a.to_dict() for a in Analysis.query.order_by(Analysis.analyzed_at.desc()).limit(10).all()]
    total    = Analysis.query.count()
    risk_counts = {
        "Low":      Analysis.query.filter_by(risk_level="Low").count(),
        "Medium":   Analysis.query.filter_by(risk_level="Medium").count(),
        "High":     Analysis.query.filter_by(risk_level="High").count(),
        "Critical": Analysis.query.filter_by(risk_level="Critical").count(),
    }
    # Cancer type distribution (top 6)
    from sqlalchemy import func
    type_rows = (
        db.session.query(Analysis.cancer_type, func.count(Analysis.id).label("cnt"))
        .group_by(Analysis.cancer_type)
        .order_by(func.count(Analysis.id).desc())
        .limit(6)
        .all()
    )
    cancer_labels = [r.cancer_type for r in type_rows]
    cancer_counts = [r.cnt for r in type_rows]
    return render_template(
        "dashboard.html",
        analyses=analyses,
        total=total,
        risk_counts=risk_counts,
        cancer_labels=json.dumps(cancer_labels),
        cancer_counts=json.dumps(cancer_counts),
        risk_levels=config.RISK_LEVELS,
    )


@app.route("/upload", methods=["GET", "POST"])
def upload():
    if request.method == "POST":
        # Validate patient info
        name   = request.form.get("name", "").strip()
        age    = request.form.get("age", 0)
        gender = request.form.get("gender", "Not specified")
        email  = request.form.get("email", "").strip()

        if not name:
            flash("Patient name is required.", "error")
            return redirect(url_for("upload"))

        file = request.files.get("report")
        if not file or file.filename == "":
            flash("Please select a report file to upload.", "error")
            return redirect(url_for("upload"))

        if not allowed_file(file.filename):
            flash("Unsupported file type. Please upload PDF, TXT, PNG, or JPG.", "error")
            return redirect(url_for("upload"))

        # Save file
        filename  = secure_filename(file.filename)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_")
        filename  = timestamp + filename
        filepath  = os.path.join(app.config["UPLOAD_FOLDER"], filename)
        file.save(filepath)

        # Extract text
        report_text = extract_text(filepath)
        if not report_text.strip():
            report_text = (
                "Medical report document submitted for cancer screening. "
                "Content extraction was limited; performing general cancer screening analysis."
            )

        # Family history from form
        fh_cancer_types = request.form.getlist("fh_cancer_type")
        fh_relations    = request.form.getlist("fh_relation")
        fh_smoking      = request.form.get("fh_smoking", "Never")
        family_history  = {
            "cancer_types": fh_cancer_types,
            "relations":    fh_relations,
            "smoking":      fh_smoking,
        }

        # Create patient record
        patient = Patient(name=name, age=int(age) if age else 0,
                          gender=gender, email=email,
                          family_history=json.dumps(family_history))
        db.session.add(patient)
        db.session.flush()

        # AI Analysis via MedGemma
        result = analyze_report(
            report_text=report_text,
            patient_name=name,
            patient_age=int(age) if age else 0,
            patient_gender=gender,
            family_history=family_history,
        )

        # Save analysis
        analysis = Analysis(
            patient_id       = patient.id,
            filename         = filename,
            report_text      = report_text[:5000],
            cancer_type      = result.get("cancer_type", "Unknown"),
            risk_level       = result.get("risk_level", "Medium"),
            confidence_score = float(result.get("confidence_score", 0)),
            findings         = json.dumps(result.get("findings", [])),
            biomarkers       = json.dumps(result.get("biomarkers", [])),
            recommendations  = json.dumps(result.get("recommendations", [])),
            doctor_questions = json.dumps(result.get("doctor_questions", [])),
            summary          = result.get("summary", ""),
            status           = "completed",
        )
        db.session.add(analysis)
        db.session.commit()

        return redirect(url_for("results", analysis_id=analysis.id))

    return render_template("upload.html")


@app.route("/results/<int:analysis_id>")
def results(analysis_id: int):
    analysis  = Analysis.query.get_or_404(analysis_id)
    data      = analysis.to_dict()
    risk_info = config.RISK_LEVELS.get(data["risk_level"], config.RISK_LEVELS["Medium"])
    patient   = Patient.query.get(data["patient_id"])
    # Count how many reports this patient has (for compare button)
    report_count = Analysis.query.filter_by(patient_id=data["patient_id"]).count()
    return render_template(
        "results.html",
        analysis=data,
        risk_info=risk_info,
        risk_levels=config.RISK_LEVELS,
        biomarker_explanations=json.dumps(config.BIOMARKER_EXPLANATIONS),
        patient_id=data["patient_id"],
        report_count=report_count,
    )


@app.route("/history")
def history():
    page     = request.args.get("page", 1, type=int)
    per_page = 12
    query    = Analysis.query.order_by(Analysis.analyzed_at.desc())
    search   = request.args.get("q", "").strip()
    risk_f   = request.args.get("risk", "").strip()
    if search:
        query = query.join(Patient).filter(
            Patient.name.ilike(f"%{search}%") |
            Analysis.cancer_type.ilike(f"%{search}%")
        )
    if risk_f:
        query = query.filter_by(risk_level=risk_f)

    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    analyses   = [a.to_dict() for a in pagination.items]
    return render_template("history.html", analyses=analyses,
                           pagination=pagination, risk_levels=config.RISK_LEVELS,
                           search=search, risk_f=risk_f)


@app.route("/compare/<int:patient_id>")
def compare(patient_id: int):
    patient  = Patient.query.get_or_404(patient_id)
    analyses = (Analysis.query
                .filter_by(patient_id=patient_id)
                .order_by(Analysis.analyzed_at.asc())
                .all())
    analyses_data = [a.to_dict() for a in analyses]
    dates  = json.dumps([a["analyzed_at"] for a in analyses_data])
    scores = json.dumps([a["confidence_score"] for a in analyses_data])
    return render_template(
        "compare.html",
        patient=patient.to_dict(),
        analyses=analyses_data,
        dates=dates,
        scores=scores,
        risk_levels=config.RISK_LEVELS,
    )


@app.route("/find-specialists")
def find_specialists():
    return render_template("specialists.html")


# ──────────────────────────── API Routes ─────────────────────────────

@app.route("/api/stats")
def api_stats():
    total   = Analysis.query.count()
    risk_counts = {
        "Low":      Analysis.query.filter_by(risk_level="Low").count(),
        "Medium":   Analysis.query.filter_by(risk_level="Medium").count(),
        "High":     Analysis.query.filter_by(risk_level="High").count(),
        "Critical": Analysis.query.filter_by(risk_level="Critical").count(),
    }
    return jsonify({"total": total, "risk_distribution": risk_counts})


@app.route("/api/analysis/<int:analysis_id>")
def api_analysis(analysis_id: int):
    analysis = Analysis.query.get_or_404(analysis_id)
    return jsonify(analysis.to_dict())


@app.route("/api/delete/<int:analysis_id>", methods=["DELETE"])
def api_delete(analysis_id: int):
    analysis = Analysis.query.get_or_404(analysis_id)
    db.session.delete(analysis)
    db.session.commit()
    return jsonify({"message": "Analysis deleted successfully."})


# ──────────────────────────── Chat Routes ────────────────────────────

@app.route("/chat")
def chat_page():
    """Render the MedGemma conversational chat interface."""
    return render_template("chat.html")


@app.route("/api/chat", methods=["POST"])
def api_chat():
    """
    POST JSON: { "message": "...", "history": [...] }
    Returns: { "reply": "..." }
    """
    data     = request.get_json(silent=True) or {}
    message  = (data.get("message") or "").strip()
    history  = data.get("history") or []
    language = data.get("language", "en") or "en"

    if not message:
        return jsonify({"error": "Message is required."}), 400

    clean_history = [
        h for h in history
        if isinstance(h, dict) and h.get("role") in ("user", "assistant")
    ]

    analysis_id = data.get("analysis_id")
    if analysis_id:
        analysis_obj = Analysis.query.get(int(analysis_id))
        if analysis_obj:
            reply = chat_with_report(message, clean_history, analysis_obj.to_dict(), language=language)
        else:
            reply = medgemma_chat(message, clean_history, language=language)
    else:
        reply = medgemma_chat(message, clean_history, language=language)

    return jsonify({"reply": reply})


@app.route("/api/chat/clear", methods=["POST"])
def api_chat_clear():
    return jsonify({"message": "Chat cleared."})


# ──────────────────────────── Risk Calculator ────────────────────────

@app.route("/risk-calculator", methods=["GET", "POST"])
def risk_calculator():
    return render_template("risk_calculator.html")


@app.route("/api/risk-calculate", methods=["POST"])
def api_risk_calculate():
    data     = request.get_json(silent=True) or {}
    language = data.get("language", "en")
    result   = calculate_risk(data, language=language)
    return jsonify(result)


# ──────────────────────────── Symptom Checker ────────────────────────

@app.route("/symptom-checker")
def symptom_checker():
    return render_template("symptom_checker.html")


@app.route("/api/symptom-check", methods=["POST"])
def api_symptom_check():
    data     = request.get_json(silent=True) or {}
    symptoms = data.get("symptoms", [])
    age      = int(data.get("age", 35))
    gender   = data.get("gender", "Not specified")
    language = data.get("language", "en")
    result   = check_symptoms(symptoms, age, gender, language=language)
    return jsonify(result)


# ──────────────────────────── Prevention Page ────────────────────────

@app.route("/prevention")
def prevention():
    return render_template("prevention.html")


# ──────────────────────────── Admin Dashboard ────────────────────────

@app.route("/admin", methods=["GET", "POST"])
def admin():
    if request.method == "POST":
        pwd = request.form.get("password", "")
        if pwd == config.ADMIN_PASSWORD:
            session["admin"] = True
        else:
            flash("Incorrect admin password.", "error")
        return redirect(url_for("admin"))

    if not session.get("admin"):
        return render_template("admin_login.html")

    analyses = Analysis.query.order_by(Analysis.analyzed_at.desc()).all()
    patients = Patient.query.count()
    total    = Analysis.query.count()
    risk_counts = {
        "Low":      Analysis.query.filter_by(risk_level="Low").count(),
        "Medium":   Analysis.query.filter_by(risk_level="Medium").count(),
        "High":     Analysis.query.filter_by(risk_level="High").count(),
        "Critical": Analysis.query.filter_by(risk_level="Critical").count(),
    }
    return render_template("admin.html", analyses=[a.to_dict() for a in analyses],
                           patients=patients, total=total, risk_counts=risk_counts,
                           risk_levels=config.RISK_LEVELS)


@app.route("/admin/logout")
def admin_logout():
    session.pop("admin", None)
    return redirect(url_for("index"))


@app.route("/api/admin/csv")
def api_admin_csv():
    if not session.get("admin"):
        return jsonify({"error": "Unauthorized"}), 401
    analyses = Analysis.query.order_by(Analysis.analyzed_at.desc()).all()
    output   = io.StringIO()
    writer   = csv.writer(output)
    writer.writerow(["ID", "Patient Name", "Age", "Gender", "Cancer Type", "Risk Level",
                     "Confidence Score", "Summary", "Analyzed At"])
    for a in analyses:
        writer.writerow([
            a.id,
            a.patient.name if a.patient else "",
            a.patient.age if a.patient else "",
            a.patient.gender if a.patient else "",
            a.cancer_type,
            a.risk_level,
            a.confidence_score,
            a.summary,
            a.analyzed_at.strftime("%Y-%m-%d %H:%M"),
        ])
    output.seek(0)
    from flask import Response
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=cancerscreen_data.csv"}
    )


# ──────────────────────────── Email Report ───────────────────────────

@app.route("/api/send-email/<int:analysis_id>", methods=["POST"])
def api_send_email(analysis_id: int):
    if not config.GMAIL_USER or config.GMAIL_USER.startswith("your_"):
        return jsonify({"error": "Email not configured. Add GMAIL_USER and GMAIL_PASS to .env"}), 400

    analysis = Analysis.query.get_or_404(analysis_id)
    data     = request.get_json(silent=True) or {}
    to_email = data.get("email", "").strip()

    if not to_email or "@" not in to_email:
        return jsonify({"error": "Please enter a valid email address."}), 400

    patient = analysis.patient
    name    = patient.name if patient else "Patient"
    rl      = analysis.risk_level
    ct      = analysis.cancer_type
    conf    = int(analysis.confidence_score)

    risk_color = {"Low": "#059669", "Medium": "#d97706", "High": "#dc2626", "Critical": "#9f1239"}.get(rl, "#0ea5e9")

    import json as _json
    def safe_list(val):
        try:    return _json.loads(val) if val else []
        except: return []

    findings        = safe_list(analysis.findings)
    biomarkers      = safe_list(analysis.biomarkers)
    recommendations = safe_list(analysis.recommendations)
    dq              = safe_list(analysis.doctor_questions)

    findings_html    = "".join(f"<li>{f}</li>" for f in findings) or "<li>None recorded</li>"
    biomarkers_html  = "".join(f"<li>{b}</li>" for b in biomarkers) or "<li>None recorded</li>"
    recs_html        = "".join(f"<li>{r}</li>" for r in recommendations) or "<li>None recorded</li>"
    dq_html          = "".join(f"<li>Q{i+1}: {q}</li>" for i, q in enumerate(dq)) or "<li>Ask your doctor about your specific findings.</li>"

    html_body = f"""
<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"></head>
<body style="font-family:Arial,sans-serif;background:#f0f4f8;margin:0;padding:20px">
  <div style="max-width:600px;margin:0 auto;background:#fff;border-radius:16px;overflow:hidden;box-shadow:0 4px 20px rgba(0,0,0,0.1)">
    <!-- Header -->
    <div style="background:linear-gradient(135deg,#0ea5e9,#0d9488);padding:28px 32px">
      <div style="font-size:22px;font-weight:900;color:#fff">🧬 CancerScreen AI</div>
      <div style="font-size:13px;color:rgba(255,255,255,0.8);margin-top:4px">Powered by MedGemma AI</div>
    </div>

    <!-- Risk Banner -->
    <div style="background:{risk_color}18;border-left:5px solid {risk_color};margin:24px;padding:16px 20px;border-radius:8px">
      <div style="font-size:12px;color:#666;font-weight:700;text-transform:uppercase;letter-spacing:1px">Cancer Risk Level</div>
      <div style="font-size:28px;font-weight:900;color:{risk_color};margin:4px 0">{rl} Risk</div>
      <div style="font-size:14px;color:#333">{ct} · {conf}% AI Confidence</div>
    </div>

    <div style="padding:0 24px 24px">
      <!-- Patient Info -->
      <div style="background:#f8fafc;border-radius:10px;padding:14px 18px;margin-bottom:20px">
        <div style="font-weight:700;color:#0f172a;margin-bottom:6px">Patient: {name}</div>
        <div style="font-size:13px;color:#64748b">Report analyzed on {analysis.analyzed_at.strftime('%d %b %Y, %I:%M %p')}</div>
      </div>

      <!-- Summary -->
      <h3 style="color:#0f172a;font-size:15px;margin-bottom:8px">📋 Clinical Summary</h3>
      <p style="color:#475569;font-size:14px;line-height:1.7;margin-bottom:20px">{analysis.summary or 'No summary available.'}</p>

      <!-- Findings -->
      <h3 style="color:#0f172a;font-size:15px;margin-bottom:8px">🔍 Key Findings</h3>
      <ul style="color:#475569;font-size:14px;line-height:1.8;margin-bottom:20px;padding-left:20px">{findings_html}</ul>

      <!-- Biomarkers -->
      <h3 style="color:#0f172a;font-size:15px;margin-bottom:8px">🧪 Biomarkers Identified</h3>
      <ul style="color:#475569;font-size:14px;line-height:1.8;margin-bottom:20px;padding-left:20px">{biomarkers_html}</ul>

      <!-- Recommendations -->
      <h3 style="color:#0f172a;font-size:15px;margin-bottom:8px">✅ Clinical Recommendations</h3>
      <ul style="color:#475569;font-size:14px;line-height:1.8;margin-bottom:20px;padding-left:20px">{recs_html}</ul>

      <!-- Doctor Questions -->
      <div style="background:#f0fdfa;border:1px solid #99f6e4;border-radius:10px;padding:16px 18px;margin-bottom:20px">
        <h3 style="color:#0d9488;font-size:15px;margin:0 0 10px">🩺 Questions to Ask Your Doctor</h3>
        <ul style="color:#475569;font-size:14px;line-height:1.8;padding-left:20px;margin:0">{dq_html}</ul>
      </div>

      <!-- Disclaimer -->
      <div style="background:#fef3c7;border-radius:8px;padding:12px 16px;font-size:12px;color:#92400e;margin-bottom:20px">
        ⚠️ <strong>Disclaimer:</strong> This report is generated by AI for educational and research purposes only.
        It is NOT a substitute for professional medical advice. Always consult a qualified doctor.
      </div>

      <!-- Footer -->
      <div style="text-align:center;font-size:12px;color:#94a3b8;border-top:1px solid #e2e8f0;padding-top:16px">
        Generated by CancerScreen AI · Powered by MedGemma
      </div>
    </div>
  </div>
</body>
</html>"""

    import smtplib
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart

    try:
        msg_obj = MIMEMultipart("alternative")
        msg_obj["Subject"] = f"CancerScreen AI Report — {name} — {rl} Risk"
        msg_obj["From"]    = f"CancerScreen AI <{config.GMAIL_USER}>"
        msg_obj["To"]      = to_email
        msg_obj.attach(MIMEText(html_body, "html"))

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(config.GMAIL_USER, config.GMAIL_PASS)
            server.sendmail(config.GMAIL_USER, to_email, msg_obj.as_string())

        return jsonify({"message": f"Report emailed to {to_email}"})
    except smtplib.SMTPAuthenticationError:
        return jsonify({"error": "Gmail authentication failed. Check GMAIL_USER and GMAIL_PASS in .env"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ──────────────────────────── Error Handlers ─────────────────────────

@app.errorhandler(404)
def not_found(e):
    return render_template("index.html"), 404


@app.errorhandler(413)
def too_large(e):
    flash("File too large. Maximum size is 16 MB.", "error")
    return redirect(url_for("upload"))


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
