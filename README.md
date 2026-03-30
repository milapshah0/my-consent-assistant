# Consent Dashboard

An AI-powered internal developer tool for consent engineering. It surfaces Aha ideas, Confluence documentation, Cosmos DB diagnostics, and public API references in a single unified workspace — so engineers spend less time hunting context and more time building.

## What it does

- **Flow tab** — interactive visualization of the end-to-end consent receipt pipeline (Creation → Kafka → Ingestion → Cosmos/SQL → Query APIs) with an AI assistant grounded in the pipeline docs
- **Insights** — Aha ideas synced from the product board, AI-categorized by engineering domain (Storage & Database, Consent API, Performance, etc.), with category filtering and pagination
- **Confluence feed** — auto-synced pages from configured spaces, full-text searchable
- **Cosmos Diagnostics** — run queries against Cosmos DB containers; AI assistant explains results, prepares optimized queries, and suggests improvements
- **Developer Chatbot** — Q&A grounded in Confluence pages and Aha ideas with source attribution

## Prerequisites

| Tool | Version |
|---|---|
| Python | 3.13 |
| Poetry | latest |
| Node.js | 20+ |
| PostgreSQL | 15+ |

## Quick Start

### 1. Clone and configure

```bash
git clone <repo-url>
cd my-consent-assistant
```

### 2. Backend

```bash
cd backend
poetry install
cp .env.example .env   # fill in credentials (see below)
poetry run alembic upgrade head
poetry run uvicorn app.main:app --reload --port 8000
```

### 3. Frontend

```bash
cd frontend
npm install
cp .env.example .env
npm run dev
```

- Frontend: http://localhost:5173
- Backend API: http://localhost:8000
- API docs: http://localhost:8000/docs

## Environment Variables

Copy `backend/.env.example` to `backend/.env` and fill in:

```env
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/consent_dashboard

# Confluence (Basic auth)
CONFLUENCE_EMAIL=you@company.com
CONFLUENCE_API_TOKEN=your-api-token
CONFLUENCE_BASE_URL=https://your-org.atlassian.net/wiki
CONFLUENCE_SPACE_KEYS=SPACE1,SPACE2

# Aha
AHA_API_TOKEN=your-aha-token
AHA_BASE_URL=https://your-org.aha.io/api/v1

# Azure OpenAI (optional — enables AI features)
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_API_KEY=your-key
AZURE_OPENAI_CHAT_DEPLOYMENT=gpt-4
AZURE_OPENAI_EMBEDDING_DEPLOYMENT=text-embedding-ada-002
```

> Azure OpenAI is optional. All features degrade gracefully to keyword search if not configured.
 
```
