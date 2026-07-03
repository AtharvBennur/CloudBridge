# CloudBridge Frontend

React SaaS dashboard foundation for CloudBridge Sprint 1.

## Stack

- React
- Vite
- TypeScript
- Tailwind CSS
- shadcn/ui-style primitives
- Framer Motion
- React Router
- TanStack Query
- Axios

## Local Setup

```powershell
npm install
copy .env.example .env
npm run dev
```

Open `http://localhost:5173`.

## Scripts

```powershell
npm run dev
npm run build
npm run lint
npm run preview
```

## Authentication

The app includes an auth context, protected routes, and an auth service boundary prepared for Amazon Cognito. Cognito is not configured in Sprint 1.

## Sprint Boundary

No migration pages, AWS orchestration, Lambda, Step Functions, SQS, or DynamoDB functionality is implemented.
