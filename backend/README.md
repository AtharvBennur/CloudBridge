# CloudBridge Backend

Flask API foundation for CloudBridge Sprint 1.

## Stack

- Python 3.12
- Flask application factory
- Blueprints
- Flask SQLAlchemy
- Alembic
- Flask-CORS
- python-dotenv
- Gunicorn
- boto3

## Local Setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
python run.py
```

The API runs on `http://localhost:5000`.

## Health API

```http
GET /health
```

```json
{
  "status": "healthy"
}
```

## Production Run

```powershell
gunicorn --bind 0.0.0.0:5000 run:app
```

## Notes

This sprint prepares the backend foundation only. It does not implement migration workflows, Lambda, Step Functions, SQS, DynamoDB, or AWS orchestration.
