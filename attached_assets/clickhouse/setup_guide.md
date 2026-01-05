# ClickHouse + FastAPI: Полная setup конфигурация

## Структура проекта

```
research-platform/
├── app/
│   ├── core/
│   │   ├── config.py           # Settings, ENV переменные
│   │   ├── dependencies.py     # Dependency injection
│   │   └── security.py         # Authentication, Authorization
│   │
│   ├── infrastructure/
│   │   └── clickhouse/
│   │       ├── __init__.py
│   │       └── client.py       # ClickHouseClient обёртка
│   │
│   ├── services/
│   │   ├── experiment_service.py
│   │   ├── metrics_service.py
│   │   └── evidence_service.py
│   │
│   ├── api/
│   │   └── v1/
│   │       ├── endpoints/
│   │       │   ├── metrics.py
│   │       │   └── hypotheses.py
│   │       └── __init__.py
│   │
│   ├── models/
│   │   ├── experiment.py
│   │   ├── project.py
│   │   ├── user.py
│   │   └── hypothesis.py
│   │
│   ├── schemas/
│   │   └── metrics.py
│   │
│   ├── tasks/
│   │   └── metrics_tasks.py    # Celery tasks
│   │
│   ├── cache/
│   │   └── metrics_cache.py
│   │
│   ├── database.py            # SQLAlchemy session
│   └── main.py               # FastAPI app
│
├── .env.example
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
└── init-clickhouse.sql
```

---

## 1. config.py

```python
# app/core/config.py

from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # App
    APP_NAME: str = "Research Experiment Platform"
    APP_VERSION: str = "0.1.0"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    LOG_LEVEL: str = "INFO"
    
    # Database - PostgreSQL
    DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/research_platform"
    
    # ClickHouse
    CLICKHOUSE_HOST: str = "localhost"
    CLICKHOUSE_PORT: int = 9000
    CLICKHOUSE_USER: str = "default"
    CLICKHOUSE_PASSWORD: str = ""
    CLICKHOUSE_DATABASE: str = "metrics"
    CLICKHOUSE_REPLICA: Optional[str] = None  # Для кластера
    CLICKHOUSE_POOL_SIZE: int = 10
    CLICKHOUSE_MAX_OVERFLOW: int = 20
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # Authentication
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # Celery
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/2"
    
    # Metrics
    METRICS_BATCH_SIZE: int = 100
    METRICS_FLUSH_INTERVAL: int = 5  # seconds
    
    # Evidence thresholds
    HYPOTHESIS_SUPPORT_THRESHOLD: float = 0.5
    HYPOTHESIS_REFUTE_THRESHOLD: float = -0.5
    
    class Config:
        env_file = ".env"

settings = Settings()
```

---

## 2. main.py

```python
# app/main.py

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging

from app.core.config import settings
from app.api.v1 import endpoints
from app.database import init_db

# Logging
logging.basicConfig(level=settings.LOG_LEVEL)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting up application...")
    init_db()
    yield
    # Shutdown
    logger.info("Shutting down application...")

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Change in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(endpoints.metrics.router)
app.include_router(endpoints.hypotheses.router)

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        workers=1 if settings.DEBUG else 4,
    )
```

---

## 3. requirements.txt

```
# Core
fastapi==0.104.1
uvicorn[standard]==0.24.0
pydantic[email]==2.4.2
pydantic-settings==2.0.3

# Database
sqlalchemy==2.0.23
psycopg2-binary==2.9.9
alembic==1.13.0

# ClickHouse
clickhouse-driver==0.4.6

# Auth
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4

# Async
celery==5.3.4
redis==5.0.1

# Utilities
python-multipart==0.0.6
httpx==0.25.2

# Monitoring & Logging
python-json-logger==2.0.7

# Development
pytest==7.4.3
pytest-asyncio==0.21.1
black==23.12.0
flake8==6.1.0
```

---

## 4. database.py

```python
# app/database.py

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.pool import QueuePool
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

# PostgreSQL engine
engine = create_engine(
    settings.DATABASE_URL,
    poolclass=QueuePool,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
    echo=settings.DEBUG,
)

SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
)

Base = declarative_base()

def get_db():
    """Dependency для получения DB session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    """Инициализировать таблицы"""
    logger.info("Creating database tables...")
    Base.metadata.create_all(bind=engine)

# Пример моделей
from sqlalchemy import Column, String, UUID, DateTime, Enum, Float, ForeignKey, JSON, Boolean
from datetime import datetime
import enum
import uuid

class Project(Base):
    __tablename__ = "projects"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    team_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(String(1024))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Experiment(Base):
    __tablename__ = "experiments"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False)
    name = Column(String(255), nullable=False)
    status = Column(String(50), default="running")  # planned, running, complete, failed
    parent_experiment_id = Column(UUID(as_uuid=True), nullable=True)
    root_experiment_id = Column(UUID(as_uuid=True), nullable=True)
    features_diff = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class ProjectMetric(Base):
    __tablename__ = "project_metrics"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False)
    name = Column(String(255), nullable=False)
    direction = Column(String(20), nullable=False)  # minimize, maximize
    aggregation = Column(String(20), default="last")
    created_at = Column(DateTime, default=datetime.utcnow)

class Hypothesis(Base):
    __tablename__ = "hypotheses"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(String(1024))
    status = Column(String(50), default="testing")  # proposed, testing, supported, refuted
    target_metrics = Column(JSON)  # List[str]
    baseline = Column(String(50), default="root")  # root, best, experiment_id
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
```

---

## 5. .env.example

```bash
# App
APP_NAME="Research Platform"
DEBUG=true
ENVIRONMENT=development
LOG_LEVEL=INFO

# PostgreSQL
DATABASE_URL=postgresql://postgres:postgres@postgres:5432/research_platform

# ClickHouse
CLICKHOUSE_HOST=clickhouse
CLICKHOUSE_PORT=9000
CLICKHOUSE_USER=default
CLICKHOUSE_PASSWORD=
CLICKHOUSE_DATABASE=metrics

# Redis
REDIS_URL=redis://redis:6379

# Auth
SECRET_KEY=your-super-secret-key-change-in-production
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Celery
CELERY_BROKER_URL=redis://redis:6379/1
CELERY_RESULT_BACKEND=redis://redis:6379/2

# Metrics Config
METRICS_BATCH_SIZE=100
METRICS_FLUSH_INTERVAL=5
HYPOTHESIS_SUPPORT_THRESHOLD=0.5
HYPOTHESIS_REFUTE_THRESHOLD=-0.5
```

---

## 6. docker-compose.yml (полный)

```yaml
version: '3.9'

services:
  # PostgreSQL
  postgres:
    image: postgres:16-alpine
    container_name: research_platform_postgres
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
      POSTGRES_DB: research_platform
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./init-postgres.sql:/docker-entrypoint-initdb.d/init.sql
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 10s
      timeout: 5s
      retries: 5
    networks:
      - research_network

  # ClickHouse
  clickhouse:
    image: clickhouse/clickhouse-server:latest
    container_name: research_platform_clickhouse
    environment:
      CLICKHOUSE_DB: metrics
      CLICKHOUSE_USER: default
      CLICKHOUSE_PASSWORD: ""
      CLICKHOUSE_DEFAULT_ACCESS_MANAGEMENT: 1
    ports:
      - "9000:9000"    # Native protocol
      - "8123:8123"    # HTTP
      - "9009:9009"    # Inter-server
    volumes:
      - clickhouse_data:/var/lib/clickhouse
      - ./init-clickhouse.sql:/docker-entrypoint-initdb.d/init.sql
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8123/ping"]
      interval: 10s
      timeout: 5s
      retries: 5
    networks:
      - research_network

  # Redis
  redis:
    image: redis:7-alpine
    container_name: research_platform_redis
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5
    networks:
      - research_network

  # FastAPI Backend
  api:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: research_platform_api
    ports:
      - "8000:8000"
    environment:
      DATABASE_URL: postgresql://postgres:postgres@postgres:5432/research_platform
      CLICKHOUSE_HOST: clickhouse
      CLICKHOUSE_PORT: 9000
      REDIS_URL: redis://redis:6379/0
      CELERY_BROKER_URL: redis://redis:6379/1
      CELERY_RESULT_BACKEND: redis://redis:6379/2
      LOG_LEVEL: DEBUG
    depends_on:
      postgres:
        condition: service_healthy
      clickhouse:
        condition: service_healthy
      redis:
        condition: service_healthy
    volumes:
      - ./app:/app/app
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
    networks:
      - research_network

  # Celery Worker
  celery:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: research_platform_celery
    environment:
      DATABASE_URL: postgresql://postgres:postgres@postgres:5432/research_platform
      CLICKHOUSE_HOST: clickhouse
      CLICKHOUSE_PORT: 9000
      CELERY_BROKER_URL: redis://redis:6379/1
      CELERY_RESULT_BACKEND: redis://redis:6379/2
    depends_on:
      - api
      - redis
    volumes:
      - ./app:/app/app
    command: celery -A app.celery_app worker -l info
    networks:
      - research_network

  # Celery Beat (Scheduler)
  celery-beat:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: research_platform_celery_beat
    environment:
      DATABASE_URL: postgresql://postgres:postgres@postgres:5432/research_platform
      CLICKHOUSE_HOST: clickhouse
      CLICKHOUSE_PORT: 9000
      CELERY_BROKER_URL: redis://redis:6379/1
      CELERY_RESULT_BACKEND: redis://redis:6379/2
    depends_on:
      - api
      - redis
    volumes:
      - ./app:/app/app
    command: celery -A app.celery_app beat -l info --scheduler django_celery_beat.schedulers:DatabaseScheduler
    networks:
      - research_network

  # pgAdmin (опционально, для управления БД)
  pgadmin:
    image: dpage/pgadmin4:latest
    container_name: research_platform_pgadmin
    environment:
      PGADMIN_DEFAULT_EMAIL: admin@example.com
      PGADMIN_DEFAULT_PASSWORD: admin
    ports:
      - "5050:80"
    depends_on:
      - postgres
    networks:
      - research_network

volumes:
  postgres_data:
  clickhouse_data:
  redis_data:

networks:
  research_network:
    driver: bridge
```

---

## 7. Dockerfile

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Default command
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

## 8. init-clickhouse.sql

```sql
CREATE DATABASE IF NOT EXISTS metrics;

USE metrics;

-- Основная таблица метрик
CREATE TABLE IF NOT EXISTS metrics (
    timestamp DateTime,
    team_id UUID,
    project_id UUID,
    experiment_id UUID,
    metric_name String,
    metric_value Float64,
    step UInt64,
    logged_at DateTime DEFAULT now(),
    host String DEFAULT ''
) ENGINE = ReplacingMergeTree(logged_at)
ORDER BY (team_id, project_id, experiment_id, metric_name, timestamp)
PARTITION BY toYYYYMM(timestamp)
SETTINGS index_granularity = 8192;

-- Таблица для агрегированных данных (по часам)
CREATE TABLE IF NOT EXISTS metrics_hourly (
    date DateTime,
    team_id UUID,
    project_id UUID,
    experiment_id UUID,
    metric_name String,
    min_value Float64,
    max_value Float64,
    avg_value Float64,
    last_value Float64,
    count UInt64
) ENGINE = ReplacingMergeTree()
ORDER BY (team_id, project_id, experiment_id, metric_name, date)
PARTITION BY toYYYYMM(date);

-- Evidence таблица
CREATE TABLE IF NOT EXISTS evidence_metrics (
    timestamp DateTime,
    team_id UUID,
    project_id UUID,
    hypothesis_id UUID,
    experiment_id UUID,
    metric_name String,
    baseline_value Float64,
    experiment_value Float64,
    delta Float64,
    direction Enum8('minimize' = 0, 'maximize' = 1),
    confidence_score Float32,
    logged_at DateTime DEFAULT now()
) ENGINE = ReplacingMergeTree(logged_at)
ORDER BY (team_id, project_id, hypothesis_id, experiment_id, metric_name, timestamp)
PARTITION BY toYYYYMM(timestamp);

-- Secondary indexes для быстрого поиска
ALTER TABLE metrics ADD INDEX idx_experiment (experiment_id) TYPE set(10) GRANULARITY 3;
ALTER TABLE metrics ADD INDEX idx_metric_name (metric_name) TYPE set(100) GRANULARITY 1;
ALTER TABLE metrics ADD INDEX idx_timestamp (timestamp) TYPE minmax GRANULARITY 3;
```

---

## 9. init-postgres.sql

```sql
-- Extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "hstore";

-- Additional setup if needed
```

---

## 10. Celery конфигурация

```python
# app/celery_app.py

from celery import Celery
from celery.schedules import crontab
from app.core.config import settings

celery_app = Celery(
    "research_platform",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # Hard limit 30 minutes
)

# Beat schedule (periodic tasks)
celery_app.conf.beat_schedule = {
    'aggregate-daily-metrics': {
        'task': 'app.tasks.metrics_tasks.aggregate_daily_metrics',
        'schedule': crontab(hour=0, minute=0),  # Полночь
    },
    'check-metrics-health': {
        'task': 'app.monitoring.alerts.run_metrics_health_checks',
        'schedule': 60,  # Каждую минуту
    },
}

# Auto-discover tasks from all registered apps
celery_app.autodiscover_tasks(['app'])
```

---

## 11. Запуск в production

### Используя systemd:

```ini
# /etc/systemd/system/research-platform.service

[Unit]
Description=Research Platform API
After=network.target postgresql.service clickhouse-server.service

[Service]
Type=notify
User=research
WorkingDirectory=/opt/research-platform
Environment="ENVIRONMENT=production"
Environment="LOG_LEVEL=INFO"
EnvironmentFile=/opt/research-platform/.env.production
ExecStart=/opt/research-platform/venv/bin/gunicorn \
    --workers 4 \
    --worker-class uvicorn.workers.UvicornWorker \
    --bind 0.0.0.0:8000 \
    app.main:app

Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### Используя nginx:

```nginx
upstream research_api {
    server localhost:8000;
    server localhost:8001;
    server localhost:8002;
    server localhost:8003;
}

server {
    listen 80;
    server_name api.research-platform.example.com;

    client_max_body_size 100M;

    location / {
        proxy_pass http://research_api;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # WebSocket support
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }

    # Health check endpoint
    location /health {
        proxy_pass http://research_api;
    }
}
```

---

## 12. Тестирование

```python
# tests/test_metrics.py

import pytest
from httpx import AsyncClient
from app.main import app
from app.core.dependencies import get_clickhouse_client
from app.infrastructure.clickhouse.client import ClickHouseClient

@pytest.fixture
async def client():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac

@pytest.mark.asyncio
async def test_log_metric(client):
    """Тест логирования одной метрики"""
    response = await client.post(
        "/api/v1/metrics/log/project-1/exp-1",
        json={
            "metric_name": "loss",
            "metric_value": 0.42,
            "step": 0,
        },
        headers={"Authorization": "Bearer test-token"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"

@pytest.mark.asyncio
async def test_get_metric_timeseries(client):
    """Тест получения временного ряда"""
    response = await client.get(
        "/api/v1/metrics/timeseries/project-1/exp-1/loss",
        headers={"Authorization": "Bearer test-token"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "points" in data
    assert isinstance(data["points"], list)
```

---

## Резюме: С чего начать

1. **Клонировать репозиторий** и скопировать файлы выше
2. **Создать `.env` файл** из `.env.example`
3. **Запустить docker-compose**:
   ```bash
   docker-compose up -d
   ```
4. **Проверить здоровье сервисов**:
   ```bash
   curl http://localhost:8000/health
   curl http://localhost:8123/ping  # ClickHouse
   ```
5. **Запустить миграции** (если нужны):
   ```bash
   docker-compose exec api alembic upgrade head
   ```
6. **Тестировать через Swagger UI**:
   ```
   http://localhost:8000/docs
   ```

**Готово к разработке и production deployment!** 🚀
