# Run QuestDB
`docker run -p 9000:9000 -p 9009:9009 -p 8812:8812 -p 9003:9003 questdb/questdb:9.3.2`
Server UI available at http://localhost:9000
Status available at http://localhost:9003

# Run Scalars Service
`uv run uvicorn api.main:app --reload --port 8001 --log-level debug`