from fastapi import FastAPI
from contextlib import asynccontextmanager
from .routes import router as api_router
from config import get_settings
from app.domain.utils.scalars_db_utils import SCALARS_DB_UTILS  # type: ignore
from db.clickhouse import check_connection, get_clickhouse_client
from db.redis import close_redis_client


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup logic can go here
    await check_connection()
    async for client in get_clickhouse_client():
        await client.command(SCALARS_DB_UTILS.build_create_mapping_table_statement())
    print("Connection to ClickHouse established")
    yield
    # Shutdown logic can go here
    await close_redis_client()


app = FastAPI(
    title=get_settings().PROJECT_NAME,
    lifespan=lifespan,
    openapi_url=f"{get_settings().API_PREFIX}/openapi.json",
)

app.include_router(api_router)


@app.get("/")
async def root():
    return {"message": "Welcome to the ML Metrics Service", "version": "1.0.0"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
