# 🧠 SmartPlex
### The Autonomous, AI-Powered Plex Server Ecosystem

SmartPlex is a hybrid **cloud + local** platform that intelligently manages Plex media servers, automates cleanup, and delivers personalized AI recommendations and analytics — both through the SmartPlex dashboard **and directly inside Plex itself**.

---

## 🌟 Core Vision

> **“A self-driving media server.”**
>
> SmartPlex learns what your users actually watch, automatically prunes stale content, and surfaces intelligent suggestions — all while integrating seamlessly with Plex, Overseerr, Sonarr, Radarr, Tautulli, Trakt, and Rotten Tomatoes.

---

## 🧱 Architecture Overview

| Layer | Role | Tech / Hosting |
|-------|------|----------------|
| **Frontend (Web + AI Chat)** | User & Admin dashboards, AI interface | Next.js 14 + TypeScript → Vercel |
| **Backend API / Workers** | Long-running jobs, sync, AI logic | FastAPI (Python) → Railway |
| **Database + Auth** | Multi-tenant data, Plex OAuth | Supabase (Postgres + Auth + Storage) |
| **Local Agent** | On-server automation (cleanup, sync) | FastAPI Docker container on Plex host |
| **Cache / Queue** | Background AI tasks, cron | Upstash Redis |
| **AI Engine** | LLM + Embeddings for insights & chat | OpenAI / Claude / local Llama |
| **Browser Extension (coming soon)** | Inject SmartPlex buttons + AI into Plex Web | Manifest v3 Extension |

---

## 🧩 Features

### 🎬 For Users
- **Plex OAuth Login** — instant sign-in with your Plex account  
- **Personal Dashboard** — watch stats, trends, unwatched gems  
- **AI Watch Advisor** — “What should I watch next?”  
- **Smart Recommendations in Plex** — via browser extension sidebar  
- **In-Plex Request Button** — request missing titles directly to Overseerr  
- **Community Leaderboards** — requester impact (RVI Score), top watchers  

### ⚙️ For Admins
- **Server Manager Dashboard** — link Plex/Tautulli/Overseerr/Sonarr/Radarr  
- **Storage Intelligence** — auto-tighten retention when disks fill  
- **Predictive Cleanup Engine** — delete/quarantine inactive media safely  
- **Smart Notifications** — AI summaries (“Saved 128 GB by removing old titles”)  
- **Dynamic Thresholds** — 90 days → 60 days when > 85% full  
- **RVI Analytics** — rate users by how popular their requests become  

---

## 🗂️ Repository Structure
/apps
/web → Next.js 14 (frontend + AI chat)
/api → FastAPI backend (API + cron + AI)
/agent → Local FastAPI Docker service (on Plex host)
/packages
/ui → shared React components
/db → Supabase schema & types
/lib → shared utils / API clients
/extensions
/plex-web → Manifest v3 browser extension (Request + AI sidebar)
/infra
docker-compose.dev.yml
vercel.json
railway.json

yaml
Copy code

---

## ⚙️ Tech Stack
- **Frontend:** Next.js 14 (App Router, TypeScript, Tailwind, Recharts)
- **Backend:** FastAPI (Python 3.11, Pydantic v2)
- **Database/Auth:** Supabase (Postgres + RLS + Auth)
- **Agent:** Python FastAPI Docker container
- **Queue/Cache:** Upstash Redis
- **AI:** OpenAI / Claude / local Llama for chat & recommendations
- **Integrations:** Plex, Tautulli, Overseerr, Sonarr, Radarr, Trakt, OMDb (Rotten Tomatoes)

---

## 🧠 Intelligent Automation

| Engine | Function |
|--------|-----------|
| **Cleanup AI** | Detects inactive media > X days, deletes or quarantines files |
| **Storage AI** | Monitors free space, tightens retention thresholds |
| **Recommendation AI** | Generates personal watch lists using Trakt + RT scores |
| **Chat AI** | Conversational assistant for users and admins |
| **Policy AI** | Suggests rule changes (“Shorten anime retention to 60 days”) |

---

## 🔐 Auth & Roles

| Role | Capabilities |
|------|---------------|
| **Admin** | Connect services, manage cleanup rules, view analytics |
| **Moderator** | Approve requests, edit thresholds |
| **User** | Personal dashboard, AI chat, request content |
| **Guest** | Read-only public stats |

All roles authenticated via **Plex OAuth through Supabase Auth**.

---

## 🧮 Database Schema (Initial)

| Table | Purpose |
|--------|----------|
| `users` | Plex users + roles |
| `servers` | Linked Plex servers |
| `integrations` | API keys for Tautulli/Overseerr/etc. |
| `media_items` | Library metadata + RT/Trakt scores |
| `user_stats` | Plays, hours, unique viewers, RVI score |
| `cleanup_log` | Deleted or quarantined items |

---

## 🧰 Local Development

### Prerequisites
- **Node.js 18+** with **pnpm** (`npm install -g pnpm`)
- **Python 3.11+** with **Poetry** (`curl -sSL https://install.python-poetry.org | python3 -`)
- **Supabase CLI** (`npm install -g supabase`)
- **Docker Desktop** (for agent + services)
- **Git** for version control

### Quick Start

```bash
# 1. Clone the repository
git clone https://github.com/rbradshaw9/smartplex.git
cd smartplex

# 2. Install dependencies
pnpm install

# 3. Setup Supabase (local development)
supabase start
pnpm supabase:types  # Generate TypeScript types

# 4. Configure environment variables
cp .env.example .env
cp apps/web/.env.example apps/web/.env.local
cp apps/api/.env.example apps/api/.env
cp apps/agent/.env.example apps/agent/.env

# Edit the .env files with your Supabase credentials and API keys

# 5. Initialize database with schema
supabase db reset

# 6. Start development servers
pnpm dev  # Starts both web and api in parallel
```

### Environment Configuration

#### Required: Supabase Setup
1. Create a new project at [supabase.com](https://supabase.com)
2. Go to Settings → API to get your keys
3. Update the `.env` files with your Supabase credentials:

```env
# Your Supabase project URL
SUPABASE_URL=https://your-project-id.supabase.co

# Your Supabase anon/public key
SUPABASE_ANON_KEY=your-anon-key-here

# Your Supabase service role key (keep this secret!)
SUPABASE_SERVICE_KEY=your-service-role-key
```

#### Optional: AI Integration
For AI chat and recommendations, add API keys:

```env
# OpenAI (recommended)
OPENAI_API_KEY=sk-your-openai-api-key

# Or Anthropic Claude
ANTHROPIC_API_KEY=your-anthropic-api-key
```

#### Optional: Plex Integration
For full Plex integration, get your Plex token:

1. Visit [plex.tv/claim](https://www.plex.tv/claim) while logged in
2. Copy the claim token
3. Add to your environment:

```env
PLEX_URL=http://your-plex-server:32400
PLEX_TOKEN=your-plex-token
```

### Development Commands

```bash
# Start all services
pnpm dev                    # Web + API
pnpm dev:web               # Frontend only
pnpm dev:api               # Backend only
pnpm dev:agent             # Agent only

# Database operations
pnpm supabase:start        # Start local Supabase
pnpm supabase:stop         # Stop local Supabase
pnpm supabase:reset        # Reset database with fresh schema
pnpm supabase:types        # Regenerate TypeScript types

# Docker operations
pnpm docker:dev            # Start services with Docker
pnpm docker:down           # Stop Docker services
pnpm docker:logs           # View Docker logs

# Code quality
pnpm lint                  # Lint all projects
pnpm lint:fix              # Fix linting issues
pnpm type-check            # TypeScript type checking
pnpm test                  # Run tests

# Build for production
pnpm build                 # Build all projects
pnpm build:web            # Build frontend
pnpm build:api            # Build backend
```

### Project Structure

```
smartplex/
├── apps/
│   ├── web/              # Next.js frontend
│   ├── api/              # FastAPI backend
│   └── agent/            # Docker agent
├── packages/
│   ├── ui/               # Shared React components
│   ├── db/               # Database types & schema
│   └── lib/              # Shared utilities
├── infra/
│   ├── docker-compose.dev.yml
│   └── docker-compose.prod.yml
└── supabase/
    ├── migrations/
    └── seed.sql
```
---

## 🚀 Deployment

### Frontend (Vercel)
1. Connect your GitHub repo to [Vercel](https://vercel.com)
2. Set environment variables in Vercel dashboard:
   ```
   NEXT_PUBLIC_SUPABASE_URL=https://your-project.supabase.co
   NEXT_PUBLIC_SUPABASE_ANON_KEY=your-anon-key
   NEXT_PUBLIC_API_URL=https://your-api-domain.com
   ```
3. Deploy automatically on git push

### Backend (Railway)
1. Connect your repo to [Railway](https://railway.app)
2. Deploy from `apps/api` directory
3. Add environment variables:
   ```
   SUPABASE_URL=https://your-project.supabase.co
   SUPABASE_SERVICE_KEY=your-service-key
   OPENAI_API_KEY=your-openai-key
   SMARTPLEX_ENV=production
   ```

### Agent (Docker on Your Plex Server)

#### Option 1: Docker Run
```bash
# Pull the latest agent image
docker pull smartplex/agent:latest

# Run the agent with your configuration
docker run -d \
  --name smartplex-agent \
  -p 9000:9000 \
  -v /path/to/your/plex/media:/data/media:ro \
  -v smartplex-agent-config:/app/config \
  --env-file .env \
  --restart unless-stopped \
  smartplex/agent:latest
```

#### Option 2: Docker Compose
```yaml
# docker-compose.yml on your Plex server
version: '3.8'
services:
  smartplex-agent:
    image: smartplex/agent:latest
    container_name: smartplex-agent
    ports:
      - "9000:9000"
    volumes:
      - /path/to/your/plex/media:/data/media:ro
      - smartplex-agent-config:/app/config
    environment:
      - PLEX_URL=http://localhost:32400
      - PLEX_TOKEN=your-plex-token
      - SMARTPLEX_API_URL=https://your-api-domain.com
      - AGENT_ID=agent-your-server-name
    restart: unless-stopped

volumes:
  smartplex-agent-config:
```

#### Option 3: Build from Source
```bash
# On your Plex server
git clone https://github.com/rbradshaw9/smartplex.git
cd smartplex/apps/agent
cp .env.example .env
# Edit .env with your configuration
docker build -t smartplex-agent .
docker run -d --name smartplex-agent -p 9000:9000 smartplex-agent
```

---

## ⚙️ Configuration Guide

### Plex Token Setup
1. Log into your Plex server web interface
2. Open browser developer tools (F12)
3. Go to Network tab, reload page
4. Look for requests with `X-Plex-Token` header
5. Copy the token value (starts with `plex-`)

### Supabase Database Setup
1. Create new Supabase project
2. Go to SQL Editor
3. Run the schema from `packages/db/schema.sql`
4. Run the RLS policies from `packages/db/rls.sql`
5. Optionally run seed data from `packages/db/seed.sql`

### AI Service Setup
- **OpenAI**: Get API key from [platform.openai.com](https://platform.openai.com)
- **Anthropic**: Get API key from [console.anthropic.com](https://console.anthropic.com)

### Agent Configuration Options

| Variable | Description | Default |
|----------|-------------|---------|
| `PLEX_URL` | Your Plex server URL | `http://localhost:32400` |
| `PLEX_TOKEN` | Plex authentication token | Required |
| `PLEX_LIBRARY_PATHS` | Comma-separated paths to scan | `/data/media` |
| `CLEANUP_ENABLED` | Enable automated cleanup | `false` |
| `CLEANUP_DRY_RUN` | Test mode (no actual deletion) | `true` |
| `STORAGE_THRESHOLD_WARNING` | Warning threshold (%) | `85` |
| `STORAGE_THRESHOLD_CRITICAL` | Critical threshold (%) | `95` |
| `HEARTBEAT_INTERVAL_SECONDS` | Heartbeat frequency | `300` (5 min) |

---

## 🔧 Advanced Usage

### Custom Cleanup Rules
```python
# In agent configuration, add custom cleanup logic
CLEANUP_RULES = {
    "min_age_days": 90,
    "min_size_mb": 100,
    "preserve_recent_downloads": True,
    "skip_high_rated": True,
    "rating_threshold": 8.0
}
```

### API Integration
```typescript
// Using the SmartPlex API client
import { createApiClient } from '@smartplex/lib'

const api = createApiClient(userToken)

// Sync Plex library
const syncResult = await api.post('/sync/plex', {
  name: 'My Plex Server',
  url: 'http://192.168.1.100:32400',
  token: 'plex-token'
})

// Get AI recommendations
const recs = await api.get('/ai/recommendations', { limit: 10 })

// Chat with AI
const chat = await api.post('/ai/chat', {
  message: 'What should I watch tonight?'
})
```

### Webhook Integration
SmartPlex can receive webhooks from Tautulli, Overseerr, and other services:

```bash
# Tautulli webhook URL
https://your-api-domain.com/webhooks/tautulli

# Overseerr webhook URL
https://your-api-domain.com/webhooks/overseerr
```

🤝 Contributing
Fork this repo

Create a feature branch feature/your-idea

Commit + push

Open a pull request

🧾 License
MIT © 2025 Ryan Bradshaw / SmartPlex Team