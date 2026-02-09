# Object Storage Service

FastAPI service providing content-addressable storage (CAS) backed by MinIO and Postgres.

## Local Development
# Setup Database

`sudo -u postgres psql` - Opens default postgres user
`ALTER ROLE myuser SUPERUSER;` - Grant permission to create extension
`CREATE DATABASE object_storage WITH OWNER = myuser;`
`export DATABASE_URL="postgresql://myuser:myuser@localhost:5432/object_storage"` - Create db for specific user

### TL;DR
```
cd python/object_storage
cp env.example .env
docker rm -f minio
docker run -p 9000:9000 -p 9001:9001 --name minio -v <path_to_data>:/data -e "MINIO_ROOT_USER=admin" -e "MINIO_ROOT_PASSWORD=password" minio/minio server /data --console-address ":9001" 
uv run uvicorn object_storage.main:app --reload --port 8002 --log-level debug
```

### Run the service
```
uv run uvicorn object_storage.main:app --reload --port 8002 --log-level debug
```

