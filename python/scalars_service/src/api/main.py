from fastapi import FastAPI
from contextlib import asynccontextmanager
from .routes import router as api_router
from config import get_settings
from db.questdb import check_connection


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup logic can go here
    await check_connection()
    print("Connection to QuestDB established")
    yield
    # Shutdown logic can go here


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
