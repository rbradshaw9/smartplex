# SmartPlex API

FastAPI backend for SmartPlex - the autonomous, AI-powered Plex server ecosystem.

## Features

- Plex OAuth authentication
- Supabase database integration
- AI/LLM integration for chat and recommendations
- Background job processing

## Development

```bash
poetry install
poetry run uvicorn app.main:app --reload
```

## Environment Variables

- `SUPABASE_URL`: Your Supabase project URL
- `SUPABASE_SERVICE_KEY`: Your Supabase service role key
- `SMARTPLEX_ENV`: Environment (development/production)
