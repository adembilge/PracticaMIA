# PracticaMIA Frontend

The web application uses **Next.js, React and TypeScript** to guide people through authenticated case preparation in English and Italian.

## Features

- Account and saved-case workspace
- Guided scope questions and structured case intake
- Case-aware explanations, approved-source citations and a reviewed checklist
- Persistent read acknowledgments and current next-action guidance
- Document review where separately authorized
- Preparation PDF export and links to official services

The frontend does not decide eligibility or submit an application. AI explanations cannot override the verified case workflow.

## Development

Requires Node.js 22 and npm.

```bash
cd frontend
npm ci
npm run dev
```

Open `http://localhost:3000`.

```bash
npm test
npm run typecheck
npm run build
```

The authenticated workspace needs an Auth0 Regular Web Application and a configured FastAPI backend. Consult [`.env.example`](.env.example) and the [repository README](../README.md) for the complete local setup. Keep authentication secrets server-side.

## Important routes

| Route | Purpose |
| --- | --- |
| `/` | Project introduction |
| `/account` | Account and session |
| `/cases/saved` | Saved cases |
| `/cases/[id]` | Scope, intake, checklist, workflow and package |
| `/privacy/documents` | Private-document processing information |

The Next.js `app/api/` routes authenticate and forward case requests to FastAPI. Browser clients must not receive backend bearer tokens or private file contents.
