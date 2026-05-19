import os
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

MEDGEMMA_API_KEY = os.getenv("MEDGEMMA_API_KEY", "")
SECRET_KEY = os.getenv("SECRET_KEY", "cancerscreen-secret-2025")
SQLALCHEMY_DATABASE_URI = f"sqlite:///{os.path.join(BASE_DIR, 'instance', 'cancerscreen.db')}"
SQLALCHEMY_TRACK_MODIFICATIONS = False
UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
MAX_CONTENT_LENGTH = int(os.getenv("MAX_UPLOAD_MB", 16)) * 1024 * 1024
ALLOWED_EXTENSIONS = {"pdf", "txt", "png", "jpg", "jpeg"}

BIOMARKER_EXPLANATIONS = {
    "CEA": {
        "full_name": "Carcinoembryonic Antigen",
        "normal": "< 2.5 ng/mL (non-smokers), < 5.0 ng/mL (smokers)",
        "simple": "A protein released by some cancer cells into the blood. Think of it as a 'cancer signal'. High levels don't confirm cancer alone but tell doctors to investigate further.",
        "elevated_means": "Possible colorectal, lung, breast, or pancreatic cancer. Further testing needed.",
        "cancers": ["Colorectal", "Lung", "Breast", "Pancreatic"]
    },
    "CA 125": {
        "full_name": "Cancer Antigen 125",
        "normal": "< 35 U/mL",
        "simple": "A protein mainly produced by ovarian tissue. Elevated levels act as a warning signal for ovarian cancer, though benign conditions can also raise it.",
        "elevated_means": "Possible ovarian, endometrial, or fallopian tube cancer. Can also be raised by endometriosis or fibroids.",
        "cancers": ["Ovarian", "Endometrial", "Fallopian Tube"]
    },
    "PSA": {
        "full_name": "Prostate-Specific Antigen",
        "normal": "< 4.0 ng/mL (age-dependent)",
        "simple": "A protein made only by the prostate gland. Higher levels may mean the prostate is enlarged, inflamed, or cancerous. It's the key early-warning test for prostate cancer.",
        "elevated_means": "Possible prostate cancer, prostate enlargement (BPH), or prostatitis.",
        "cancers": ["Prostate"]
    },
    "AFP": {
        "full_name": "Alpha-Fetoprotein",
        "normal": "< 10 ng/mL (adults)",
        "simple": "A protein normally made by a developing baby's liver. In adults, high levels can indicate liver cancer or testicular cancer.",
        "elevated_means": "Possible hepatocellular (liver) carcinoma or testicular germ cell tumour.",
        "cancers": ["Liver", "Testicular"]
    },
    "CA 15-3": {
        "full_name": "Cancer Antigen 15-3",
        "normal": "< 30 U/mL",
        "simple": "A protein shed by breast cancer cells. Used mainly to monitor how breast cancer treatment is working. High levels signal active breast cancer.",
        "elevated_means": "Possible breast cancer or cancer spread (metastasis). Used to monitor treatment response.",
        "cancers": ["Breast"]
    },
    "CA 19-9": {
        "full_name": "Cancer Antigen 19-9",
        "normal": "< 37 U/mL",
        "simple": "A sugar molecule found on the surface of cancer cells. It's like a fingerprint for pancreatic and bile duct cancers.",
        "elevated_means": "Possible pancreatic, bile duct, or colorectal cancer.",
        "cancers": ["Pancreatic", "Bile Duct", "Colorectal"]
    },
    "HER2": {
        "full_name": "Human Epidermal Growth Factor Receptor 2",
        "normal": "Negative (IHC 0 or 1+)",
        "simple": "A protein that promotes cell growth. When HER2 is 'positive', breast cancer cells have too many copies of this protein, making the cancer grow faster — but targeted therapies exist for this.",
        "elevated_means": "HER2-positive breast cancer — aggressive but responds well to targeted drugs like Herceptin.",
        "cancers": ["Breast", "Gastric"]
    },
    "LDH": {
        "full_name": "Lactate Dehydrogenase",
        "normal": "140–280 U/L",
        "simple": "An enzyme released when cells are damaged. High LDH can mean cancer cells are actively multiplying and dying rapidly, causing tissue breakdown.",
        "elevated_means": "Non-specific — can indicate lymphoma, leukemia, or advanced solid tumours.",
        "cancers": ["Lymphoma", "Leukemia", "Melanoma"]
    },
    "NSE": {
        "full_name": "Neuron-Specific Enolase",
        "normal": "< 12.5 ng/mL",
        "simple": "A marker for nerve cell activity. In cancer, high NSE can mean a tumour is growing from nerve or neuroendocrine tissue.",
        "elevated_means": "Possible small-cell lung cancer or neuroblastoma.",
        "cancers": ["Lung (Small Cell)", "Neuroblastoma"]
    },
    "CYFRA 21-1": {
        "full_name": "Cytokeratin Fragment 21-1",
        "normal": "< 3.3 ng/mL",
        "simple": "A fragment from cells lining the lung airways. High levels in the blood often mean damaged or cancerous lung cells are breaking down.",
        "elevated_means": "Possible non-small-cell lung cancer.",
        "cancers": ["Lung"]
    },
    "CA 72-4": {
        "full_name": "Cancer Antigen 72-4",
        "normal": "< 6.9 U/mL",
        "simple": "A marker for stomach (gastric) and ovarian cancers. Think of it as a stomach cancer alarm.",
        "elevated_means": "Possible gastric or ovarian cancer.",
        "cancers": ["Gastric", "Ovarian"]
    },
    "BRCA1": {
        "full_name": "Breast Cancer Gene 1",
        "normal": "No pathogenic variant",
        "simple": "A gene that normally helps repair DNA damage. A mutation in BRCA1 means the repair system is broken, greatly increasing lifetime risk of breast and ovarian cancer.",
        "elevated_means": "Up to 72% lifetime risk of breast cancer and 44% for ovarian cancer.",
        "cancers": ["Breast", "Ovarian"]
    },
    "BRCA2": {
        "full_name": "Breast Cancer Gene 2",
        "normal": "No pathogenic variant",
        "simple": "Similar to BRCA1 — a DNA repair gene. Mutations raise risk for breast, ovarian, and prostate cancers. Knowing this helps plan preventive care.",
        "elevated_means": "Up to 69% lifetime risk of breast cancer; also raises risk for prostate and pancreatic cancers.",
        "cancers": ["Breast", "Ovarian", "Prostate", "Pancreatic"]
    },
    "ER": {
        "full_name": "Estrogen Receptor",
        "normal": "Negative",
        "simple": "Tests if breast cancer cells have receptors for the hormone estrogen. ER-positive cancers are fuelled by estrogen, so hormone-blocking drugs (like Tamoxifen) work well.",
        "elevated_means": "ER-positive breast cancer — responds well to hormone therapy.",
        "cancers": ["Breast"]
    },
    "PR": {
        "full_name": "Progesterone Receptor",
        "normal": "Negative",
        "simple": "Similar to ER — tests if cancer cells respond to progesterone. PR-positive breast cancers also respond well to hormone-blocking treatments.",
        "elevated_means": "PR-positive breast cancer — good prognosis, responds to hormone therapy.",
        "cancers": ["Breast"]
    },
}

CANCER_TYPES = [
    "Breast Cancer", "Lung Cancer", "Colorectal Cancer", "Prostate Cancer",
    "Skin Melanoma", "Cervical Cancer", "Leukemia", "Liver Cancer",
    "Pancreatic Cancer", "Ovarian Cancer", "Thyroid Cancer", "Bladder Cancer"
]

ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123")
GMAIL_USER     = os.getenv("GMAIL_USER", "")
GMAIL_PASS     = os.getenv("GMAIL_PASS", "")

RISK_LEVELS = {
    "Low":      {"color": "#00d4aa", "icon": "✔", "bg": "rgba(0,212,170,0.15)"},
    "Medium":   {"color": "#ffa502", "icon": "⚠", "bg": "rgba(255,165,2,0.15)"},
    "High":     {"color": "#ff6b6b", "icon": "!", "bg": "rgba(255,107,107,0.15)"},
    "Critical": {"color": "#ff0040", "icon": "✖", "bg": "rgba(255,0,64,0.15)"},
}
