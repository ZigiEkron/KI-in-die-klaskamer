# Boer War Personas Bot 🇿🇦

### Run locally with FastAPI + OpenAI API + Afrikaans voice + avatar hooks

#### Setup (Windows PowerShell)
```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
Copy-Item .env.example .env
notepad .env   # paste your API key
uvicorn app.main:app --reload
```
Then open [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
