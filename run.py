"""
CancerScreen AI – Quick Start
Run: python run.py
Then open: http://localhost:5000
"""
from app import app

if __name__ == "__main__":
    print("\n" + "="*55)
    print("  CancerScreen AI  |  Powered by MedGemma")
    print("="*55)
    print("  Open in browser: http://localhost:5000")
    print("  Set API key in .env file: MEDGEMMA_API_KEY=...")
    print("="*55 + "\n")
    app.run(debug=True, host="0.0.0.0", port=5000)
