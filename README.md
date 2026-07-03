# CloudBridge

CloudBridge Sprint 1 establishes a production-ready full-stack foundation:

- Flask 3 backend using an application factory, blueprints, SQLAlchemy, Alembic, CORS, environment-based config, structured logging, and a health API.
- React + Vite + TypeScript frontend using Tailwind CSS, shadcn/ui-style components, Framer Motion, React Router, TanStack Query, Axios, dark mode, and a protected dashboard shell.
- Cognito-ready authentication boundaries without configuring Cognito or implementing AWS orchestration.

No migration workflow, AWS Lambda, Step Functions, SQS, DynamoDB, or AWS orchestration is implemented in Sprint 1.

## Run Backend

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
python run.py
```

Health check:

```powershell
Invoke-RestMethod http://localhost:5000/health
```

## Run Frontend

```powershell
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`.

## Project Structure

```text
CloudBridge/
├── backend/
├── frontend/
├── infrastructure/
├── docs/
├── diagrams/
├── research/
├── scripts/
├── assets/
└── tests/
```
