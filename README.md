# Setup Database

`sudo -u postgres psql` - Opens default postgres user
`ALTER ROLE myuser SUPERUSER;` - Grant permission to create extension
`CREATE DATABASE experiment_tracker WITH OWNER = myuser;`
`export DATABASE_URL="postgresql://myuser:myuser@localhost:5432/experiment_tracker"` - Create db for specific user

# Run Backend
`cd python/backend`
`export DATABASE_URL="postgresql://myuser:myuser@localhost:5432/experiment_tracker"`
`uv run uvicorn api.main:app --reload --port 8000`

# Run Frontend
`cd apps/web`
`export NEXT_PUBLIC_BASE_URL=http://localhost:8000`
`pnpm run dev`