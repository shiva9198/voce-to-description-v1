# Voice Business Onboarding

Flask prototype for converting spoken business and product details into editable structured JSON. It combines Groq-hosted speech transcription and language models with deterministic extraction fallbacks.

This repository contains the backend prototype and small HTML debugging clients. It does not contain the separate product frontend.

## Implemented scope

- Business-detail audio upload and transcription
- Product-detail audio upload and extraction
- Groq-based product extraction with deterministic fallback parsing
- JSON session creation, listing, editing, and deletion
- Render and Gunicorn deployment configuration
- Manual backend and extraction test cases

## Stack

- Python and Flask
- Groq API for transcription and language-model extraction
- Flask-CORS
- Gunicorn and Render
- HTML and browser JavaScript for local debugging

## Local setup

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
cp .env.example .env
python app.py
```

Add your own Groq API key to `.env`. The API starts on `http://localhost:5001` by default.

## API surface

| Method | Route | Purpose |
|---|---|---|
| `POST` | `/upload_business_audio` | Transcribe business audio and create a JSON session |
| `POST` | `/upload_product_audio` | Transcribe product audio and append extracted products |
| `POST` | `/save` | Save edited session data |
| `GET` | `/get_sessions` | List saved JSON sessions |
| `GET` | `/get_session/<filename>` | Read one validated session file |
| `DELETE` | `/delete_session/<filename>` | Delete one validated session file |

See [ARCHITECTURE.md](ARCHITECTURE.md) for the current prototype architecture and [test_cases.md](test_cases.md) for manual extraction cases.

## Verification

```bash
python -m unittest discover -s tests
python -m compileall -q app.py session_paths.py tests
```

The HTML test clients can be used against a locally running API. They are not automated browser tests.

## Current limitations

- Session state is process-local and file-backed; it is not designed for concurrent production traffic.
- Audio files use shared temporary filenames.
- CORS is permissive in the prototype and should be restricted for a production deployment.
- Extraction quality varies with speech quality, phrasing, and external-model behavior. No production accuracy or latency guarantee is claimed.
- Authentication, authorization, rate limiting, persistent database storage, and automated end-to-end tests are not implemented here.

## Security

- Keep `GROQ_API_KEY` in local or deployment environment variables; never commit `.env`.
- Session endpoints accept only simple `.json` filenames within the configured data directory.
- Do not use this prototype for sensitive or regulated data without adding authentication, access controls, retention rules, and encrypted storage.
