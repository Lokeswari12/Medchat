# CancerScreen AI 🩺

> AI-powered cancer screening platform built with Python, Flask, and Google's MedGemma model via OpenRouter.

Upload a cancer report (PDF, TXT, or image) and get an instant AI analysis — risk level, biomarkers, findings, clinical recommendations — plus an **interactive chatbot that reads your specific report and answers any question about it**.

---

## Features

- **Report Analysis** — Upload PDF, TXT, or image medical reports
- **MedGemma AI** — Google's medical AI model analyzes every report
- **Report Chatbot** — Ask questions about your specific report in plain language
- **12+ Cancer Types** — Breast, Lung, Colorectal, Prostate, Cervical, Skin, Leukemia, Liver, Pancreatic, Ovarian, Thyroid, Bladder
- **Biomarker Detection** — Identifies CEA, CA-125, PSA, AFP, HER2, CA 15-3, and more
- **Risk Levels** — Low / Medium / High / Critical with confidence scoring
- **Dashboard** — Charts and analytics for all analyses
- **Patient History** — Searchable and filterable analysis history
- **General AI Chat** — Ask any oncology or medical question
- **Light UI** — Clean, professional medical interface

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.x, Flask |
| AI Model | Google MedGemma via OpenRouter API |
| Database | SQLite + SQLAlchemy |
| Frontend | HTML5, CSS3, JavaScript |
| Charts | Chart.js |
| PDF Parsing | PyPDF2 |
| Fonts & Icons | Inter (Google Fonts), Font Awesome 6 |

---

## Project Structure

```
CancerScreen Using Python/
├── app.py                  # Flask app — all routes
├── config.py               # Configuration & settings
├── models.py               # SQLAlchemy models (Patient, Analysis)
├── medgemma_service.py     # MedGemma AI — report analysis + chat
├── document_processor.py  # PDF/TXT/Image text extraction
├── run.py                  # Quick-start launcher
├── requirements.txt        # Python dependencies
├── .env                    # API key (not committed)
├── templates/
│   ├── base.html           # Base layout + navbar
│   ├── index.html          # Landing page
│   ├── upload.html         # Report upload form
│   ├── results.html        # Analysis results + report chatbot
│   ├── dashboard.html      # Analytics dashboard
│   ├── history.html        # Analysis history
│   └── chat.html           # General AI chat
├── static/
│   ├── css/style.css       # Full light-theme stylesheet
│   └── js/app.js           # Counter animations, nav, helpers
├── uploads/                # Uploaded report files
└── instance/
    └── cancerscreen.db     # SQLite database
```

---

## Setup & Installation

### Prerequisites
- Python 3.8 or higher
- pip
- An OpenRouter API key — get one free at [openrouter.ai](https://openrouter.ai)

### 1. Clone the Repository

```bash
git clone https://github.com/krupakar-injeti/cancerscreening-using-python.git
cd cancerscreening-using-python
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure the API Key

Create a `.env` file in the project root:

```
MEDGEMMA_API_KEY=your_openrouter_api_key_here
SECRET_KEY=your_secret_key_here
FLASK_DEBUG=True
MAX_UPLOAD_MB=16
```

### 4. Run the Application

```bash
python run.py
```

Open your browser at **http://localhost:5000**

---

## How It Works

```
1. Enter patient details (name, age, gender)
        ↓
2. Upload cancer report (PDF / TXT / Image)
        ↓
3. MedGemma AI reads and analyzes the report
        ↓
4. View full results — risk level, findings, biomarkers, recommendations
        ↓
5. Chat with the AI about YOUR specific report — ask anything
```

---

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| GET | `/` | Landing page |
| GET/POST | `/upload` | Upload and analyze report |
| GET | `/results/<id>` | View analysis results |
| GET | `/dashboard` | Analytics dashboard |
| GET | `/history` | Analysis history |
| GET | `/chat` | General AI chat |
| POST | `/api/chat` | Chat API (supports `analysis_id` for report-aware chat) |
| GET | `/api/stats` | Statistics API |
| GET | `/api/analysis/<id>` | Single analysis JSON |
| DELETE | `/api/delete/<id>` | Delete an analysis |

---

## Supported Report Formats

- **PDF** — Pathology reports, lab results, clinical notes
- **TXT** — Plain text medical reports
- **PNG / JPG / JPEG** — Scanned documents, medical images

---

## Disclaimer

This project is built for **educational and research purposes only**.  
It is **not** a substitute for professional medical advice, diagnosis, or treatment.  
Always consult a qualified healthcare professional.

---

## License

MIT License — free to use, modify, and distribute.

---

## Author

**Krupakar**  
Built with Python, Flask, and Google MedGemma AI
