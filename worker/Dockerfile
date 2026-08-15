FROM python:3.12-slim

# Force rebuild - version 2.0.0 - 2026-08-15
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Force rebuild - version 2.0.0 - 2026-08-15
COPY run.py .

ENTRYPOINT ["python", "run.py"]
