# Setup Database

`sudo -u postgres psql` - Opens default postgres user
`ALTER ROLE myuser SUPERUSER;` - Grant permission to create extension
`export DATABASE_URL="postgresql://myuser:myuser@localhost:5432/experiment_tracker"` - Create db for specific user

# Run Backend 
`export DATABASE_URL="postgresql://myuser:myuser@localhost:5432/experiment_tracker"`
`uv run uvicorn backend.main:app --reload --port 8000`

# Run Frontend
`export NEXT_PUBLIC_BASE_URL=http://localhost:8000`
`pnpm dlx turbo dev`