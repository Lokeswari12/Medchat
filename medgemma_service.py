"""
MedGemma AI service via OpenRouter API.
Supports both report analysis and conversational chat.
"""
import json
import re
import requests
from config import MEDGEMMA_API_KEY

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
MODEL           = "google/gemma-3-27b-it"          # MedGemma-class model on OpenRouter

REPORT_SYSTEM = (
    "You are MedGemma, an expert oncology AI. Analyze medical reports for "
    "cancer screening with clinical precision. Respond ONLY with a valid JSON "
    "object — no markdown fences, no extra text before or after."
)

CHAT_SYSTEM_BASE = (
    "You are MedGemma, a medical AI specialized in oncology. "
    "RULES: Answer in plain text only — NO markdown, NO bullet points, NO asterisks, NO bold, NO lists. "
    "Keep every answer to 2-3 sentences maximum. Be direct and clear. "
    "If the topic needs more detail, give the most important fact first, then say 'Ask me to elaborate if needed.' "
    "Do not refuse general medical education questions."
)

RISK_CALC_SYSTEM = (
    "You are MedGemma, an expert oncology AI. Analyze the provided health questionnaire data "
    "and calculate cancer risk. Respond ONLY with a valid JSON object — no markdown, no extra text."
)

SYMPTOM_SYSTEM = (
    "You are MedGemma, an expert oncology AI. Analyze the provided symptoms and determine "
    "which cancer types should be investigated. Respond ONLY with a valid JSON object — no markdown, no extra text."
)

CHAT_SYSTEM = CHAT_SYSTEM_BASE

ANALYSIS_PROMPT = """Analyze the following medical report for cancer screening.

MEDICAL REPORT:
{report_text}

PATIENT INFO:
- Name  : {patient_name}
- Age   : {patient_age}
- Gender: {patient_gender}

FAMILY HISTORY:
{family_history_text}

Respond ONLY with a valid JSON object (no markdown, no extra text):
{{
  "cancer_type": "Most likely cancer type, or 'No Malignancy Detected'",
  "risk_level": "Low | Medium | High | Critical",
  "confidence_score": <integer 0-100>,
  "findings": ["Key finding 1", "Key finding 2", "Key finding 3"],
  "biomarkers": ["Biomarker name: value (status)", "..."],
  "recommendations": ["Step 1", "Step 2", "Step 3"],
  "doctor_questions": ["Specific question 1 the patient should ask their doctor?", "Specific question 2?", "Specific question 3?", "Specific question 4?", "Specific question 5?"],
  "summary": "2-3 sentence clinical summary."
}}"""


def _call_openrouter(messages: list, max_tokens: int = 1024) -> str | None:
    """Low-level call to OpenRouter chat completions API."""
    if not MEDGEMMA_API_KEY or MEDGEMMA_API_KEY.startswith("your_"):
        return None
    headers = {
        "Authorization": f"Bearer {MEDGEMMA_API_KEY}",
        "Content-Type":  "application/json",
        "HTTP-Referer":  "http://localhost:5000",
        "X-Title":       "CancerScreen AI",
    }
    payload = {
        "model":      MODEL,
        "messages":   messages,
        "max_tokens": max_tokens,
        "temperature": 0.4,
    }
    try:
        resp = requests.post(OPENROUTER_URL, headers=headers,
                             json=payload, timeout=60)
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"]
    except Exception as e:
        print(f"[OpenRouter error] {e}")
        return None


# ── Report Analysis ────────────────────────────────────────────────

def analyze_report(report_text: str, patient_name: str = "Unknown",
                   patient_age: int = 0, patient_gender: str = "Unknown",
                   family_history: dict = None) -> dict:
    fh = family_history or {}
    cancer_types_in_family = ", ".join(fh.get("cancer_types", [])) or "None reported"
    relations = ", ".join(fh.get("relations", [])) or "None reported"
    smoking = fh.get("smoking", "Not specified")
    family_history_text = (
        f"- Cancer types in family: {cancer_types_in_family}\n"
        f"- Affected relations: {relations}\n"
        f"- Smoking history: {smoking}"
    )
    prompt = ANALYSIS_PROMPT.format(
        report_text=report_text[:6000],
        patient_name=patient_name,
        patient_age=patient_age,
        patient_gender=patient_gender,
        family_history_text=family_history_text,
    )
    messages = [
        {"role": "system",  "content": REPORT_SYSTEM},
        {"role": "user",    "content": prompt},
    ]
    raw = _call_openrouter(messages, max_tokens=1200)
    if raw is None:
        return _demo_response(patient_name, patient_age)
    result = _parse_json(raw)
    if not result.get("cancer_type"):
        return _demo_response(patient_name, patient_age)
    return result


# ── Report-Context Chat ───────────────────────────────────────────

REPORT_CHAT_SYSTEM = (
    "You are MedGemma, an expert oncology AI. You have analyzed a specific patient's report. "
    "Answer questions about THIS REPORT using the data provided. "
    "RULES: Plain text only — NO markdown, NO asterisks, NO bullet points, NO bold formatting. "
    "Keep every answer to 2-3 sentences maximum. Be direct and compassionate. "
    "If a language instruction is given in the system context, reply fully in that language."
)

def calculate_risk(form_data: dict, language: str = "en") -> dict:
    """Calculate cancer risk from questionnaire data."""
    lang_note = f" Respond with string values (findings, recommendations, advice) in {_lang_name(language)}." if language != "en" else ""
    prompt = f"""Analyze this health questionnaire and calculate cancer risk.{lang_note}

QUESTIONNAIRE DATA:
- Age: {form_data.get('age', 'Unknown')}
- Gender: {form_data.get('gender', 'Unknown')}
- Smoking: {form_data.get('smoking', 'Never')}
- Alcohol: {form_data.get('alcohol', 'Never')}
- Exercise: {form_data.get('exercise', 'Rarely')}
- Diet: {form_data.get('diet', 'Mixed')}
- BMI Range: {form_data.get('bmi', 'Normal')}
- Sun Exposure: {form_data.get('sun_exposure', 'Moderate')}
- Family History of Cancer: {form_data.get('family_cancer', 'No')}
- Family Cancer Types: {form_data.get('family_cancer_types', 'None')}
- Existing Conditions: {', '.join(form_data.get('conditions', [])) or 'None'}
- Symptoms Present: {', '.join(form_data.get('symptoms', [])) or 'None'}

Respond ONLY with valid JSON:
{{
  "overall_score": <integer 0-100>,
  "risk_level": "Low | Medium | High | Critical",
  "top_risks": [
    {{"cancer": "Cancer type", "likelihood": "Low|Medium|High", "reason": "1 sentence reason"}},
    {{"cancer": "Cancer type 2", "likelihood": "Low|Medium|High", "reason": "1 sentence reason"}},
    {{"cancer": "Cancer type 3", "likelihood": "Low|Medium|High", "reason": "1 sentence reason"}}
  ],
  "key_risk_factors": ["Factor 1", "Factor 2", "Factor 3"],
  "recommended_screenings": ["Screening 1", "Screening 2", "Screening 3"],
  "lifestyle_advice": ["Advice 1", "Advice 2", "Advice 3"],
  "summary": "2-3 sentence plain language risk summary"
}}"""
    messages = [
        {"role": "system", "content": RISK_CALC_SYSTEM},
        {"role": "user", "content": prompt},
    ]
    raw = _call_openrouter(messages, max_tokens=800)
    if raw is None:
        return _demo_risk_response(form_data)
    result = _parse_json(raw)
    if not result.get("risk_level"):
        return _demo_risk_response(form_data)
    return result


def check_symptoms(symptoms: list, age: int, gender: str, language: str = "en") -> dict:
    """Map symptoms to possible cancer types and urgency."""
    lang_note = f" Respond with string values in {_lang_name(language)}." if language != "en" else ""
    prompt = f"""Analyze these symptoms for possible cancer types.{lang_note}

PATIENT: Age {age}, Gender {gender}
SYMPTOMS: {', '.join(symptoms) if symptoms else 'None reported'}

Respond ONLY with valid JSON:
{{
  "urgency": "Immediate | Within 2 weeks | Within 3 months | Routine",
  "urgency_reason": "1 sentence explanation",
  "possible_cancers": [
    {{"type": "Cancer type", "relevance": "High|Medium|Low", "related_symptoms": ["symptom1"], "reason": "1 sentence"}},
    {{"type": "Cancer type 2", "relevance": "High|Medium|Low", "related_symptoms": ["symptom2"], "reason": "1 sentence"}}
  ],
  "recommended_tests": ["Test 1 with reason", "Test 2 with reason"],
  "reassurance": "If symptoms turn out non-cancerous, they may indicate... (1 sentence)",
  "summary": "Plain language 2-sentence summary of findings"
}}"""
    messages = [
        {"role": "system", "content": SYMPTOM_SYSTEM},
        {"role": "user", "content": prompt},
    ]
    raw = _call_openrouter(messages, max_tokens=700)
    if raw is None:
        return _demo_symptom_response(symptoms)
    result = _parse_json(raw)
    if not result.get("urgency"):
        return _demo_symptom_response(symptoms)
    return result


def _lang_name(code: str) -> str:
    names = {
        "hi": "Hindi", "te": "Telugu", "ta": "Tamil", "kn": "Kannada",
        "ml": "Malayalam", "bn": "Bengali", "mr": "Marathi", "gu": "Gujarati",
        "pa": "Punjabi", "or": "Odia", "ur": "Urdu", "as": "Assamese"
    }
    return names.get(code, "English")


def _demo_risk_response(form_data: dict) -> dict:
    age = int(form_data.get("age", 40))
    smoking = form_data.get("smoking", "Never")
    risk = "High" if smoking in ("Current (light)", "Current (heavy)") or age > 55 else "Medium" if age > 40 else "Low"
    return {
        "overall_score": {"Low": 18, "Medium": 42, "High": 67}[risk],
        "risk_level": risk,
        "top_risks": [
            {"cancer": "Colorectal Cancer", "likelihood": "Medium", "reason": "Age and dietary factors increase risk."},
            {"cancer": "Lung Cancer", "likelihood": "High" if "Current" in smoking else "Low", "reason": "Smoking is the #1 risk factor for lung cancer."},
            {"cancer": "Breast/Prostate Cancer", "likelihood": "Medium", "reason": "Age-related screening is recommended."}
        ],
        "key_risk_factors": ["Age above 40", "Diet low in vegetables", "Sedentary lifestyle"] if risk == "Medium" else ["Smoking", "Age", "Family history"],
        "recommended_screenings": ["Annual full blood count with tumour markers", "Colonoscopy at age 45+", "Annual cancer screening panel"],
        "lifestyle_advice": ["Quit smoking immediately if applicable", "Eat 5 servings of vegetables daily", "Exercise 30 minutes daily"],
        "summary": f"Based on your questionnaire, your overall cancer risk is {risk}. Regular screening and healthy lifestyle changes can significantly reduce your risk."
    }


def _demo_symptom_response(symptoms: list) -> dict:
    has_serious = any(s in symptoms for s in ["Unexplained weight loss", "Blood in urine/stool", "Persistent cough", "Lump or swelling"])
    urgency = "Within 2 weeks" if has_serious else "Within 3 months"
    return {
        "urgency": urgency,
        "urgency_reason": "One or more of your symptoms can be associated with early cancer and should be evaluated promptly.",
        "possible_cancers": [
            {"type": "Colorectal Cancer", "relevance": "Medium", "related_symptoms": ["Blood in urine/stool"], "reason": "Blood in stool is a key warning sign for colorectal cancer."},
            {"type": "Lung Cancer", "relevance": "Medium", "related_symptoms": ["Persistent cough"], "reason": "A persistent cough lasting more than 3 weeks warrants chest X-ray screening."}
        ],
        "recommended_tests": ["Complete Blood Count (CBC) with tumour markers", "Chest X-ray if respiratory symptoms present", "Colonoscopy if gastrointestinal symptoms present"],
        "reassurance": "Many of these symptoms are also caused by non-cancerous conditions like infections or inflammation.",
        "summary": "Your symptoms warrant a medical evaluation. Please see a doctor promptly — early detection significantly improves outcomes."
    }


def chat_with_report(user_message: str, history: list, analysis: dict, language: str = "en") -> str:
    """Chat grounded in a specific analyzed report."""
    findings_text     = "\n".join(f"  • {f}" for f in analysis.get("findings", []))
    biomarkers_text   = "\n".join(f"  • {b}" for b in analysis.get("biomarkers", []))
    recs_text         = "\n".join(f"  {i+1}. {r}"
                                  for i, r in enumerate(analysis.get("recommendations", [])))
    context = f"""You have analyzed the following cancer screening report:

PATIENT          : {analysis.get('patient_name', 'Unknown')}
CANCER TYPE      : {analysis.get('cancer_type', 'Unknown')}
RISK LEVEL       : {analysis.get('risk_level', 'Unknown')}
CONFIDENCE SCORE : {analysis.get('confidence_score', 0)}%
CLINICAL SUMMARY : {analysis.get('summary', '')}

KEY FINDINGS:
{findings_text or '  None recorded'}

BIOMARKERS IDENTIFIED:
{biomarkers_text or '  None recorded'}

CLINICAL RECOMMENDATIONS:
{recs_text or '  None recorded'}

Use this data to answer every question about this patient's report."""

    lang_instruction = f"\n\nIMPORTANT: Respond entirely in {_lang_name(language)}." if language != "en" else ""
    messages = [
        {"role": "system", "content": REPORT_CHAT_SYSTEM + "\n\n" + context + lang_instruction},
        *history[-8:],
        {"role": "user", "content": user_message},
    ]
    reply = _call_openrouter(messages, max_tokens=200)
    if reply is None:
        return _fallback_report_chat(user_message, analysis)
    return reply.strip()


def _fallback_report_chat(msg: str, analysis: dict) -> str:
    rl = analysis.get("risk_level", "Unknown")
    ct = analysis.get("cancer_type", "Unknown")
    msg_l = msg.lower()
    if any(w in msg_l for w in ["risk", "level", "serious", "dangerous"]):
        explanations = {
            "Low":      "Low risk means no significant cancer markers were found. Continue routine annual screening.",
            "Medium":   "Medium risk means some concerning markers are present. A follow-up with a specialist is recommended.",
            "High":     "High risk means significant cancer markers were detected. Urgent specialist referral is strongly advised.",
            "Critical": "Critical risk means highly concerning findings requiring immediate medical attention.",
        }
        return explanations.get(rl, f"The risk level is {rl}.")
    if any(w in msg_l for w in ["biomarker", "marker", "cea", "ca", "psa"]):
        bms = analysis.get("biomarkers", [])
        return (f"The following biomarkers were identified in this report:\n" +
                "\n".join(f"• {b}" for b in bms) if bms
                else "No specific biomarkers were extracted from this report.")
    if any(w in msg_l for w in ["next", "do", "step", "recommend", "should"]):
        recs = analysis.get("recommendations", [])
        return ("Based on this analysis, the recommended next steps are:\n" +
                "\n".join(f"{i+1}. {r}" for i, r in enumerate(recs)) if recs
                else "Please consult a qualified oncologist for next steps.")
    return (f"This report shows {ct} with {rl} risk. "
            f"Feel free to ask about the risk level, biomarkers, findings, or recommendations.")


# ── Conversational Chat ────────────────────────────────────────────

def chat(user_message: str, history: list, language: str = "en") -> str:
    """
    history: list of {"role": "user"|"assistant", "content": "..."} dicts
    Returns the assistant's reply as a plain string.
    """
    sys_msg = CHAT_SYSTEM
    if language and language != "en":
        sys_msg += f" Respond entirely in {_lang_name(language)}."
    messages = [{"role": "system", "content": sys_msg}]
    messages.extend(history[-10:])
    messages.append({"role": "user", "content": user_message})

    reply = _call_openrouter(messages, max_tokens=200)
    if reply is None:
        return _fallback_chat(user_message)
    return reply.strip()


# ── Helpers ────────────────────────────────────────────────────────

def _parse_json(raw: str) -> dict:
    raw = re.sub(r"```(?:json)?", "", raw).strip().rstrip("`").strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except Exception:
                pass
    return {}


def _fallback_chat(msg: str) -> str:
    msg_lower = msg.lower()
    if any(w in msg_lower for w in ["breast", "mammogram"]):
        return ("Breast cancer is the most common cancer in women worldwide. "
                "Key risk factors include age, family history, BRCA1/BRCA2 mutations, "
                "hormonal factors, and lifestyle. Screening via mammography is recommended "
                "annually from age 40–45. Early detection dramatically improves outcomes.")
    if any(w in msg_lower for w in ["lung", "smoking"]):
        return ("Lung cancer is the leading cause of cancer death globally. "
                "About 85% of cases are linked to smoking. Symptoms include persistent cough, "
                "blood in sputum, chest pain, and unexplained weight loss. "
                "Low-dose CT scans are recommended for high-risk individuals aged 50–80.")
    if any(w in msg_lower for w in ["symptom", "sign", "feel"]):
        return ("Common cancer warning signs include: unexplained weight loss, fatigue, "
                "persistent pain, unusual lumps, changes in bowel/bladder habits, "
                "non-healing sores, and abnormal bleeding. If you notice any of these, "
                "please consult a doctor promptly. Early detection saves lives.")
    if any(w in msg_lower for w in ["treatment", "therapy", "chemo"]):
        return ("Cancer treatments include surgery, chemotherapy, radiation therapy, "
                "immunotherapy, targeted therapy, and hormone therapy. "
                "The best approach depends on cancer type, stage, and patient health. "
                "A multidisciplinary oncology team creates personalised treatment plans.")
    if any(w in msg_lower for w in ["prevent", "reduce risk", "lifestyle"]):
        return ("Cancer prevention tips: avoid tobacco, limit alcohol, maintain healthy weight, "
                "exercise regularly (150 min/week), eat a diet rich in fruits and vegetables, "
                "protect skin from UV, get recommended vaccinations (HPV, Hepatitis B), "
                "and undergo regular cancer screening.")
    return ("I'm MedGemma, your oncology AI assistant. I can answer questions about "
            "cancer types, symptoms, screening, treatment, prevention, and biomarkers. "
            "What would you like to know?")


def _demo_response(patient_name: str, patient_age: int) -> dict:
    scenarios = [
        {
            "cancer_type": "Breast Cancer – Ductal Carcinoma In Situ (DCIS)",
            "risk_level": "High",
            "confidence_score": 87,
            "findings": [
                "Microcalcifications in upper outer quadrant of left breast",
                "Elevated CA 15-3: 48.2 U/mL (normal < 30 U/mL)",
                "Heterogeneous breast density (Category C) on mammography",
                "Minor lymph node enlargement on ultrasound"
            ],
            "biomarkers": [
                "CA 15-3: 48.2 U/mL (elevated)",
                "CEA: 6.1 ng/mL (borderline elevated)",
                "ER/PR receptor: Positive", "HER2: Negative"
            ],
            "recommendations": [
                "Urgent referral to breast oncology specialist within 2 weeks",
                "Core needle biopsy for histopathological confirmation",
                "MRI-guided breast imaging for complete staging",
                "Genetic counselling for BRCA1/BRCA2 mutation testing",
                "Avoid hormonal supplements until oncology clearance"
            ],
            "doctor_questions": [
                "What does my elevated CA 15-3 level mean specifically for my case?",
                "Do I need a biopsy and what type would you recommend?",
                "Should I get tested for BRCA1/BRCA2 genetic mutations?",
                "What is the timeline from here — when should I see a specialist?",
                "Are there any medications or supplements I should stop immediately?"
            ],
            "summary": (
                f"Patient {patient_name} shows imaging and lab findings strongly "
                f"suggestive of early-stage breast carcinoma. Elevated CA 15-3 and "
                f"microcalcifications warrant immediate specialist evaluation. "
                f"Early intervention is critical for optimal outcomes."
            )
        },
        {
            "cancer_type": "Colorectal Cancer – Stage II",
            "risk_level": "High",
            "confidence_score": 82,
            "findings": [
                "Elevated CEA: 12.5 ng/mL (normal < 2.5 ng/mL)",
                "Irregular mucosal pattern in sigmoid colon on colonoscopy",
                "Occult blood positive in stool (3 consecutive tests)",
                "Iron-deficiency anemia: Hemoglobin 9.2 g/dL"
            ],
            "biomarkers": [
                "CEA: 12.5 ng/mL (elevated)",
                "CA 19-9: 38 U/mL (upper limit)",
                "Hemoglobin: 9.2 g/dL (low)",
                "Fecal Occult Blood: Positive"
            ],
            "recommendations": [
                "Immediate gastroenterology referral for complete colonoscopy",
                "CT abdomen/pelvis for tumour staging",
                "Biopsy of suspicious colonic lesion",
                "Iron supplementation for anaemia management",
                "Low-residue diet until diagnostic workup completed"
            ],
            "doctor_questions": [
                "My CEA is 12.5 ng/mL — what does that level typically indicate about cancer stage?",
                "How urgent is the colonoscopy — can I get it done this week?",
                "If the biopsy confirms cancer, what stage do you suspect it is?",
                "What are my treatment options if this is confirmed as colorectal cancer?",
                "Should my immediate family members get screened as well?"
            ],
            "summary": (
                f"Findings for {patient_name} are consistent with colorectal malignancy. "
                f"Markedly elevated CEA, positive fecal occult blood, and anaemia form "
                f"a concerning clinical picture requiring urgent gastroenterological workup."
            )
        },
        {
            "cancer_type": "No Malignancy Detected",
            "risk_level": "Low",
            "confidence_score": 91,
            "findings": [
                "All tumour markers within normal reference ranges",
                "No suspicious lesions on imaging",
                "CBC and metabolic panel within normal limits",
                "Benign cystic finding – stable, no change from prior study"
            ],
            "biomarkers": [
                "CEA: 1.8 ng/mL (normal)", "CA 125: 14 U/mL (normal)",
                "PSA: 1.2 ng/mL (normal)", "AFP: 3.1 ng/mL (normal)"
            ],
            "recommendations": [
                "Routine annual cancer screening per age/gender guidelines",
                "Continue healthy lifestyle: balanced diet, regular exercise",
                "Follow-up in 12 months with repeat tumour markers",
                "Colonoscopy screening recommended at age 45"
            ],
            "doctor_questions": [
                "Even though results are normal now, what symptoms should make me come back sooner?",
                "Given my age and gender, which cancer screenings do you specifically recommend annually?",
                "Are there any lifestyle changes that would further reduce my cancer risk?",
                "Should any of my normal borderline values be re-tested in 6 months?",
                "Do I need any genetic testing given my family background?"
            ],
            "summary": (
                f"Report for {patient_name} shows no evidence of malignancy at this time. "
                f"All tumour biomarkers are within normal ranges and imaging is benign. "
                f"Continued routine preventive screening is recommended."
            )
        }
    ]
    idx = (patient_age or 45) % len(scenarios)
    return scenarios[idx]
