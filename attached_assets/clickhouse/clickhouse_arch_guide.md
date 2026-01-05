# Полное руководство: ClickHouse для метрик ML/DL платформы

## Содержание
1. [Архитектурный обзор](#архитектурный-обзор)
2. [Модель данных и схемы](#модель-данных-и-схемы)
3. [Интеграция с FastAPI](#интеграция-с-fastapi)
4. [Многопользовательская изоляция данных](#многопользовательская-изоляция-данных)
5. [Оптимизация и производительность](#оптимизация-и-производительность)
6. [Примеры кода](#примеры-кода)
7. [Развёртывание](#развёртывание)

---

## Архитектурный обзор

### Зачем ClickHouse?

**ClickHouse** идеален для хранения временных рядов метрик потому что:
- ✅ **Columnar storage** — оптимизирован для аналитики (SELECT по отдельным столбцам)
- ✅ **Высокая пропускная способность** — миллионы метрик в секунду
- ✅ **Сжатие** — значительная экономия дискового пространства
- ✅ **Быстрые агрегирующие запросы** — GROUP BY, SUM, AVG за миллисекунды
- ✅ **ReplacingMergeTree** — легко перезаписывать значения метрик
- ✅ **Встроенная репликация и шардирование**

### Двухуровневая архитектура

```
┌─────────────────────────────────────────┐
│  FastAPI Backend                        │
│  ├─ User/Team Management (FastAPI Users)│
│  ├─ Experiment Metadata (PostgreSQL)    │
│  └─ Project Config (PostgreSQL)         │
└────────────┬────────────────────────────┘
             │
        ┌────┴────────────────────┐
        │                         │
            ↓                                    ↓
┌──────────────────┐    ┌────────────────────┐
│  PostgreSQL      │    │  ClickHouse        │
│  ─────────────   │    │  ──────────────    │
│  Projects        │    │  Metric streams    │
│  Experiments     │    │  Time series data  │
│  Features        │    │  Evidence data     │
│  Hypotheses      │    │  Aggregations      │
│  Users/Teams     │    │                    │
└──────────────────┘    └────────────────────┘
```

**PostgreSQL** — для иерархических данных (DAG, Feature diffs, References)
**ClickHouse** — для OLAP временных рядов (миллиарды metric points)

---

## Модель данных и схемы

### 1. PostgreSQL: Сущности, связанные с метриками

```sql
-- Таблица для конфигурации метрик в проекте
CREATE TABLE project_metrics (
    id UUID PRIMARY KEY,
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    direction VARCHAR(10) CHECK (direction IN ('minimize', 'maximize')),
    aggregation VARCHAR(20) CHECK (aggregation IN ('last', 'best', 'average')),
    source_type VARCHAR(50) CHECK (source_type IN ('scalar', 'derived')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(project_id, name)
);

-- Таблица для отслеживания логирования метрик экспериментом
-- (используется для synchronization между FastAPI и ClickHouse)
CREATE TABLE metric_write_logs (
    id UUID PRIMARY KEY,
    experiment_id UUID NOT NULL REFERENCES experiments(id) ON DELETE CASCADE,
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    metric_name VARCHAR(255) NOT NULL,
    last_logged_at TIMESTAMP,
    total_points INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(experiment_id, metric_name)
);

-- Таблица для отслеживания записей в ClickHouse
CREATE TABLE clickhouse_sync_state (
    id UUID PRIMARY KEY,
    experiment_id UUID NOT NULL REFERENCES experiments(id) ON DELETE CASCADE,
    last_synced_at TIMESTAMP,
    pending_rows INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(experiment_id)
);
```

### 2. ClickHouse: Таблицы для метрик

#### Основная таблица метрик

```sql
-- PRIMARY KEY оптимизирует queries по (team_id, project_id, experiment_id, metric_name, timestamp)
CREATE TABLE metrics (
    timestamp DateTime,
    team_id UUID,
    project_id UUID,
    experiment_id UUID,
    metric_name String,
    metric_value Float64,
    step UInt64,
    logged_at DateTime,
    host String DEFAULT ''
) ENGINE = ReplacingMergeTree()
ORDER BY (team_id, project_id, experiment_id, metric_name, timestamp)
PARTITION BY toYYYYMM(timestamp)
TTL timestamp + INTERVAL 2 YEAR DELETE;
```

**Почему ReplacingMergeTree:**
- Если один и тот же `(experiment_id, metric_name, step)` залогирован дважды, храним только новое значение
- Версионирование: `(team_id, project_id, experiment_id, metric_name, step, logged_at)`

#### Таблица агрегированных данных (для быстрых запросов)

```sql
CREATE TABLE metrics_aggregated (
    date Date,
    team_id UUID,
    project_id UUID,
    experiment_id UUID,
    metric_name String,
    step UInt64,
    min_value Float64,
    max_value Float64,
    avg_value Float64,
    last_value Float64,
    count UInt64,
    timestamp DateTime DEFAULT now()
) ENGINE = ReplacingMergeTree()
ORDER BY (team_id, project_id, experiment_id, metric_name, date, step)
PARTITION BY toYYYYMM(date);
```

#### Таблица для evidence (связь метрик с гипотезами)

```sql
CREATE TABLE evidence_metrics (
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
    logged_at DateTime
) ENGINE = ReplacingMergeTree()
ORDER BY (team_id, project_id, hypothesis_id, experiment_id, metric_name, timestamp)
PARTITION BY toYYYYMM(timestamp);
```

---

## Интеграция с FastAPI

### 1. Клиент для работы с ClickHouse

```python
# app/infrastructure/clickhouse/client.py

from typing import Optional, List, Dict, Any
from datetime import datetime
from clickhouse_driver import Client as CHClient
import logging

logger = logging.getLogger(__name__)

class ClickHouseClient:
    """Обёртка над драйвером ClickHouse для метрик"""
    
    def __init__(
        self,
        host: str = "localhost",
        port: int = 9000,
        user: str = "default",
        password: str = "",
        database: str = "metrics",
    ):
        self.client = CHClient(
            host,
            port=port,
            user=user,
            password=password,
            database=database,
        )
        self.database = database
    
    def insert_metric(
        self,
        team_id: str,
        project_id: str,
        experiment_id: str,
        metric_name: str,
        metric_value: float,
        step: int,
        timestamp: Optional[datetime] = None,
        host: str = "",
    ) -> None:
        """Вставить одну метрику"""
        if timestamp is None:
            timestamp = datetime.utcnow()
        
        query = """
            INSERT INTO metrics (
                timestamp, team_id, project_id, experiment_id,
                metric_name, metric_value, step, logged_at, host
            ) VALUES
        """
        
        data = [
            (
                timestamp,
                team_id,
                project_id,
                experiment_id,
                metric_name,
                metric_value,
                step,
                datetime.utcnow(),
                host,
            )
        ]
        
        self.client.execute(query, data)
        logger.debug(
            f"Inserted metric: {metric_name}={metric_value} "
            f"for exp={experiment_id}, step={step}"
        )
    
    def insert_metrics_batch(
        self,
        metrics: List[Dict[str, Any]],
    ) -> None:
        """Вставить батч метрик (эффективнее для большого количества)
        
        Ожидает список словарей:
        {
            'timestamp': datetime,
            'team_id': str,
            'project_id': str,
            'experiment_id': str,
            'metric_name': str,
            'metric_value': float,
            'step': int,
            'host': str (optional)
        }
        """
        if not metrics:
            return
        
        query = """
            INSERT INTO metrics (
                timestamp, team_id, project_id, experiment_id,
                metric_name, metric_value, step, logged_at, host
            ) VALUES
        """
        
        data = [
            (
                m.get('timestamp', datetime.utcnow()),
                m['team_id'],
                m['project_id'],
                m['experiment_id'],
                m['metric_name'],
                m['metric_value'],
                m['step'],
                datetime.utcnow(),
                m.get('host', ''),
            )
            for m in metrics
        ]
        
        self.client.execute(query, data)
        logger.info(f"Inserted batch of {len(metrics)} metrics")
    
    def get_metric_timeseries(
        self,
        team_id: str,
        project_id: str,
        experiment_id: str,
        metric_name: str,
        limit: int = 10000,
    ) -> List[Dict[str, Any]]:
        """Получить временной ряд метрики"""
        query = """
            SELECT
                timestamp,
                step,
                metric_value
            FROM metrics
            WHERE team_id = %(team_id)s
              AND project_id = %(project_id)s
              AND experiment_id = %(experiment_id)s
              AND metric_name = %(metric_name)s
            ORDER BY timestamp ASC
            LIMIT %(limit)s
        """
        
        result = self.client.execute(
            query,
            params={
                'team_id': team_id,
                'project_id': project_id,
                'experiment_id': experiment_id,
                'metric_name': metric_name,
                'limit': limit,
            }
        )
        
        return [
            {
                'timestamp': row[0],
                'step': row[1],
                'value': row[2],
            }
            for row in result
        ]
    
    def get_experiment_metrics_summary(
        self,
        team_id: str,
        project_id: str,
        experiment_id: str,
    ) -> Dict[str, Dict[str, float]]:
        """Получить сводку по всем метрикам эксперимента
        
        Returns:
            {
                'loss': {'last': 0.42, 'min': 0.35, 'max': 0.95, 'avg': 0.50},
                'accuracy': {...},
            }
        """
        query = """
            SELECT
                metric_name,
                min(metric_value) as min_value,
                max(metric_value) as max_value,
                avg(metric_value) as avg_value,
                argMax(metric_value, timestamp) as last_value
            FROM metrics
            WHERE team_id = %(team_id)s
              AND project_id = %(project_id)s
              AND experiment_id = %(experiment_id)s
            GROUP BY metric_name
        """
        
        result = self.client.execute(
            query,
            params={
                'team_id': team_id,
                'project_id': project_id,
                'experiment_id': experiment_id,
            }
        )
        
        summary = {}
        for row in result:
            metric_name, min_val, max_val, avg_val, last_val = row
            summary[metric_name] = {
                'last': last_val,
                'min': min_val,
                'max': max_val,
                'avg': avg_val,
            }
        
        return summary
    
    def compare_experiments(
        self,
        team_id: str,
        project_id: str,
        experiment_ids: List[str],
        metric_names: Optional[List[str]] = None,
    ) -> Dict[str, Dict[str, Dict[str, float]]]:
        """Сравнить метрики между экспериментами
        
        Returns:
            {
                'exp_1': {
                    'loss': {'last': 0.42, ...},
                    'accuracy': {...},
                },
                'exp_2': {...},
            }
        """
        experiments_str = ','.join([f"'{e}'" for e in experiment_ids])
        
        query = f"""
            SELECT
                experiment_id,
                metric_name,
                argMax(metric_value, timestamp) as last_value
            FROM metrics
            WHERE team_id = %(team_id)s
              AND project_id = %(project_id)s
              AND experiment_id IN ({experiments_str})
              {f"AND metric_name IN ({','.join([f\"'{m}'\" for m in metric_names])})" if metric_names else ""}
            GROUP BY experiment_id, metric_name
        """
        
        result = self.client.execute(
            query,
            params={
                'team_id': team_id,
                'project_id': project_id,
            }
        )
        
        comparison = {exp_id: {} for exp_id in experiment_ids}
        for row in result:
            exp_id, metric_name, value = row
            if metric_name not in comparison[exp_id]:
                comparison[exp_id][metric_name] = {}
            comparison[exp_id][metric_name]['last'] = value
        
        return comparison
    
    def delete_experiment_metrics(
        self,
        team_id: str,
        project_id: str,
        experiment_id: str,
    ) -> None:
        """Удалить все метрики эксперимента (Alt: использовать TTL)"""
        query = """
            ALTER TABLE metrics DELETE
            WHERE team_id = %(team_id)s
              AND project_id = %(project_id)s
              AND experiment_id = %(experiment_id)s
        """
        
        self.client.execute(
            query,
            params={
                'team_id': team_id,
                'project_id': project_id,
                'experiment_id': experiment_id,
            }
        )
        logger.info(f"Deleted metrics for experiment {experiment_id}")
```

### 2. Dependency Injection в FastAPI

```python
# app/core/dependencies.py

from fastapi import Depends
from app.infrastructure.clickhouse.client import ClickHouseClient
from app.config import settings

_clickhouse_client: Optional[ClickHouseClient] = None

def get_clickhouse_client() -> ClickHouseClient:
    """Dependency для получения ClickHouse клиента"""
    global _clickhouse_client
    if _clickhouse_client is None:
        _clickhouse_client = ClickHouseClient(
            host=settings.CLICKHOUSE_HOST,
            port=settings.CLICKHOUSE_PORT,
            user=settings.CLICKHOUSE_USER,
            password=settings.CLICKHOUSE_PASSWORD,
            database=settings.CLICKHOUSE_DATABASE,
        )
    return _clickhouse_client
```

### 3. Pydantic модели для API

```python
# app/schemas/metrics.py

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from uuid import UUID

class MetricPoint(BaseModel):
    """Одна точка метрики"""
    timestamp: datetime
    step: int
    value: float

class MetricTimeSeriesResponse(BaseModel):
    """Ответ для временного ряда метрики"""
    experiment_id: UUID
    metric_name: str
    points: List[MetricPoint]
    count: int

    class Config:
        json_schema_extra = {
            "example": {
                "experiment_id": "550e8400-e29b-41d4-a716-446655440000",
                "metric_name": "loss",
                "count": 100,
                "points": [
                    {"timestamp": "2024-01-01T10:00:00", "step": 0, "value": 0.95},
                    {"timestamp": "2024-01-01T10:01:00", "step": 1, "value": 0.87},
                ]
            }
        }

class MetricLogRequest(BaseModel):
    """Запрос на логирование метрики"""
    metric_name: str
    metric_value: float
    step: int
    timestamp: Optional[datetime] = None
    host: Optional[str] = None

class MetricBatchLogRequest(BaseModel):
    """Батч-логирование метрик"""
    metrics: List[MetricLogRequest]

class ExperimentMetricsSummary(BaseModel):
    """Сводка метрик эксперимента"""
    experiment_id: UUID
    metrics: Dict[str, Dict[str, float]]  # {metric_name: {last, min, max, avg}}

class ComparisonResult(BaseModel):
    """Результат сравнения экспериментов"""
    project_id: UUID
    experiments: Dict[str, Dict[str, Dict[str, float]]]
```

### 4. API endpoints в FastAPI

```python
# app/api/v1/endpoints/metrics.py

from fastapi import APIRouter, Depends, HTTPException, Query
from uuid import UUID
from typing import List, Optional
from datetime import datetime

from app.core.dependencies import get_clickhouse_client, get_current_user
from app.infrastructure.clickhouse.client import ClickHouseClient
from app.schemas.metrics import (
    MetricLogRequest,
    MetricBatchLogRequest,
    MetricTimeSeriesResponse,
    ExperimentMetricsSummary,
    ComparisonResult,
)
from app.services.experiment_service import ExperimentService

router = APIRouter(prefix="/api/v1/metrics", tags=["metrics"])

@router.post("/log/{project_id}/{experiment_id}")
async def log_metric(
    project_id: UUID,
    experiment_id: UUID,
    metric_data: MetricLogRequest,
    clickhouse: ClickHouseClient = Depends(get_clickhouse_client),
    current_user = Depends(get_current_user),
):
    """Залогировать одну метрику
    
    - **project_id**: ID проекта
    - **experiment_id**: ID эксперимента
    - **metric_data**: Данные метрики
    """
    # Проверка прав доступа (упрощено)
    # В реальности нужна проверка через ExperimentService и ProjectService
    
    try:
        clickhouse.insert_metric(
            team_id=str(current_user.team_id),
            project_id=str(project_id),
            experiment_id=str(experiment_id),
            metric_name=metric_data.metric_name,
            metric_value=metric_data.metric_value,
            step=metric_data.step,
            timestamp=metric_data.timestamp or datetime.utcnow(),
            host=metric_data.host or "",
        )
        return {
            "status": "success",
            "message": f"Metric {metric_data.metric_name} logged successfully"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/batch/{project_id}/{experiment_id}")
async def log_metrics_batch(
    project_id: UUID,
    experiment_id: UUID,
    batch_data: MetricBatchLogRequest,
    clickhouse: ClickHouseClient = Depends(get_clickhouse_client),
    current_user = Depends(get_current_user),
):
    """Залогировать батч метрик (более эффективно)"""
    try:
        metrics = [
            {
                'timestamp': m.timestamp or datetime.utcnow(),
                'team_id': str(current_user.team_id),
                'project_id': str(project_id),
                'experiment_id': str(experiment_id),
                'metric_name': m.metric_name,
                'metric_value': m.metric_value,
                'step': m.step,
                'host': m.host or '',
            }
            for m in batch_data.metrics
        ]
        
        clickhouse.insert_metrics_batch(metrics)
        return {
            "status": "success",
            "count": len(metrics),
            "message": f"Logged {len(metrics)} metrics successfully"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get(
    "/timeseries/{project_id}/{experiment_id}/{metric_name}",
    response_model=MetricTimeSeriesResponse
)
async def get_metric_timeseries(
    project_id: UUID,
    experiment_id: UUID,
    metric_name: str,
    limit: int = Query(10000, le=100000),
    clickhouse: ClickHouseClient = Depends(get_clickhouse_client),
    current_user = Depends(get_current_user),
):
    """Получить временной ряд метрики"""
    try:
        points = clickhouse.get_metric_timeseries(
            team_id=str(current_user.team_id),
            project_id=str(project_id),
            experiment_id=str(experiment_id),
            metric_name=metric_name,
            limit=limit,
        )
        
        return MetricTimeSeriesResponse(
            experiment_id=experiment_id,
            metric_name=metric_name,
            points=[
                {
                    'timestamp': p['timestamp'],
                    'step': p['step'],
                    'value': p['value'],
                }
                for p in points
            ],
            count=len(points),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get(
    "/summary/{project_id}/{experiment_id}",
    response_model=ExperimentMetricsSummary
)
async def get_experiment_metrics_summary(
    project_id: UUID,
    experiment_id: UUID,
    clickhouse: ClickHouseClient = Depends(get_clickhouse_client),
    current_user = Depends(get_current_user),
):
    """Получить сводку по метрикам эксперимента"""
    try:
        summary = clickhouse.get_experiment_metrics_summary(
            team_id=str(current_user.team_id),
            project_id=str(project_id),
            experiment_id=str(experiment_id),
        )
        
        return ExperimentMetricsSummary(
            experiment_id=experiment_id,
            metrics=summary,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post(
    "/compare",
    response_model=ComparisonResult
)
async def compare_experiments(
    project_id: UUID,
    experiment_ids: List[UUID] = Query(...),
    metric_names: Optional[List[str]] = Query(None),
    clickhouse: ClickHouseClient = Depends(get_clickhouse_client),
    current_user = Depends(get_current_user),
):
    """Сравнить метрики между экспериментами"""
    try:
        comparison = clickhouse.compare_experiments(
            team_id=str(current_user.team_id),
            project_id=str(project_id),
            experiment_ids=[str(e) for e in experiment_ids],
            metric_names=metric_names,
        )
        
        return ComparisonResult(
            project_id=project_id,
            experiments=comparison,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

---

## Многопользовательская изоляция данных

### 1. Стратегия изоляции

**Принцип: Team-based partitioning**

```
┌───────────────────────────────────────┐
│ ClickHouse Cluster                    │
├───────────────────────────────────────┤
│ Metrics Table (Sharded by team_id)    │
│                                       │
│  Partition 1 (Team A)                 │
│  ├─ Project 1                         │
│  │  ├─ Experiment 1: 1M points        │
│  │  └─ Experiment 2: 500K points      │
│  └─ Project 2                         │
│                                       │
│  Partition 2 (Team B)                 │
│  ├─ Project 1                         │
│  │  └─ Experiment 1: 2M points        │
│  └─ Project 3                         │
│                                       │
│  ... и т.д.                           │
└───────────────────────────────────────┘
```

**Ключевые моменты:**

1. **team_id в PRIMARY KEY первым** — ClickHouse оптимизирует доступ
2. **Row-level security на уровне FastAPI** — проверяем права перед запросом к ClickHouse
3. **Нет SELECT без team_id** — всегда фильтруем по team_id в WHERE

### 2. Middleware для проверки доступа

```python
# app/core/security.py

from typing import Optional
from uuid import UUID
from fastapi import HTTPException, Depends

class AccessControl:
    """Контроль доступа к данным на основе team_id"""
    
    @staticmethod
    async def verify_project_access(
        team_id: UUID,
        project_id: UUID,
        current_user,
        db,  # SQLAlchemy session
    ) -> bool:
        """Проверить, имеет ли пользователь доступ к проекту"""
        from app.models import Project
        
        project = db.query(Project).filter(
            Project.id == project_id,
            Project.team_id == team_id,
        ).first()
        
        if not project:
            raise HTTPException(
                status_code=403,
                detail="Access denied to this project"
            )
        
        # Дополнительная проверка роли (Admin, Researcher, Viewer)
        return True
    
    @staticmethod
    async def verify_experiment_access(
        team_id: UUID,
        project_id: UUID,
        experiment_id: UUID,
        current_user,
        db,
    ) -> bool:
        """Проверить доступ к эксперименту"""
        from app.models import Experiment, Project
        
        # Сначала проверяем project
        await AccessControl.verify_project_access(
            team_id, project_id, current_user, db
        )
        
        # Потом проверяем experiment
        experiment = db.query(Experiment).filter(
            Experiment.id == experiment_id,
            Experiment.project_id == project_id,
        ).first()
        
        if not experiment:
            raise HTTPException(
                status_code=404,
                detail="Experiment not found"
            )
        
        return True
```

### 3. Безопасный endpoint

```python
# app/api/v1/endpoints/secure_metrics.py

from fastapi import APIRouter, Depends, HTTPException
from uuid import UUID
from app.core.dependencies import get_clickhouse_client, get_current_user
from app.core.security import AccessControl
from app.database import get_db

router = APIRouter(prefix="/api/v1/metrics", tags=["metrics"])

@router.get("/secure/timeseries/{project_id}/{experiment_id}/{metric_name}")
async def get_metric_timeseries_secure(
    project_id: UUID,
    experiment_id: UUID,
    metric_name: str,
    clickhouse: ClickHouseClient = Depends(get_clickhouse_client),
    current_user = Depends(get_current_user),
    db = Depends(get_db),
):
    """Безопасно получить временной ряд (с проверкой доступа)"""
    
    # Проверка доступа
    await AccessControl.verify_experiment_access(
        team_id=current_user.team_id,
        project_id=project_id,
        experiment_id=experiment_id,
        current_user=current_user,
        db=db,
    )
    
    # Только после проверки доступа выполняем запрос к ClickHouse
    points = clickhouse.get_metric_timeseries(
        team_id=str(current_user.team_id),  # Используем team_id из сессии
        project_id=str(project_id),
        experiment_id=str(experiment_id),
        metric_name=metric_name,
    )
    
    return {
        "experiment_id": experiment_id,
        "metric_name": metric_name,
        "points": points,
    }
```

---

## Оптимизация и производительность

### 1. Batch insertion для SDK

```python
# app/sdk/experiment.py

from typing import List, Dict, Any
from datetime import datetime
import time

class BatchMetricBuffer:
    """Буферизация метрик перед отправкой"""
    
    def __init__(self, max_size: int = 100, flush_interval: float = 5.0):
        self.max_size = max_size
        self.flush_interval = flush_interval
        self.buffer: List[Dict[str, Any]] = []
        self.last_flush = time.time()
    
    def add(
        self,
        metric_name: str,
        metric_value: float,
        step: int,
        timestamp: Optional[datetime] = None,
    ):
        """Добавить метрику в буфер"""
        self.buffer.append({
            'metric_name': metric_name,
            'metric_value': metric_value,
            'step': step,
            'timestamp': timestamp or datetime.utcnow(),
        })
        
        # Автоматическая отправка если буфер полон или истёк интервал
        if len(self.buffer) >= self.max_size:
            self.flush()
        elif time.time() - self.last_flush >= self.flush_interval:
            self.flush()
    
    def flush(self):
        """Отправить накопленные метрики на сервер"""
        if not self.buffer:
            return
        
        # Отправка через API
        response = self.client.post(
            f"/api/v1/metrics/batch/{self.project_id}/{self.experiment_id}",
            json={"metrics": self.buffer},
        )
        
        if response.status_code == 200:
            self.buffer.clear()
            self.last_flush = time.time()
        else:
            raise Exception(f"Failed to flush metrics: {response.text}")
```

### 2. Индексы в ClickHouse

```sql
-- Secondary indexes для быстрого поиска
ALTER TABLE metrics
ADD INDEX idx_experiment (experiment_id) TYPE set(10) GRANULARITY 3;

ALTER TABLE metrics
ADD INDEX idx_metric_name (metric_name) TYPE set(100) GRANULARITY 1;

ALTER TABLE metrics
ADD INDEX idx_timestamp (timestamp) TYPE minmax GRANULARITY 3;
```

### 3. Materialized View для агрегирования

```sql
-- Автоматическое агрегирование по часам
CREATE MATERIALIZED VIEW metrics_hourly_mv
TO metrics_hourly AS
SELECT
    toStartOfHour(timestamp) AS hour,
    team_id,
    project_id,
    experiment_id,
    metric_name,
    min(metric_value) as min_value,
    max(metric_value) as max_value,
    avg(metric_value) as avg_value,
    argMax(metric_value, timestamp) as last_value,
    count() as count
FROM metrics
GROUP BY team_id, project_id, experiment_id, metric_name, hour;

CREATE TABLE metrics_hourly (
    hour DateTime,
    team_id UUID,
    project_id UUID,
    experiment_id UUID,
    metric_name String,
    min_value Float64,
    max_value Float64,
    avg_value Float64,
    last_value Float64,
    count UInt64
) ENGINE = SummingMergeTree()
ORDER BY (team_id, project_id, experiment_id, metric_name, hour);
```

---

## Примеры кода

### 1. Полный пример SDK для логирования метрик

```python
# examples/experiment_tracking.py

from research_sdk import Experiment
from typing import Optional
import time

# Инициализация эксперимента
exp = Experiment(
    project="vision_transformer",
    name="vit_base_imagenet",
    team_id="team-123",
    api_url="http://localhost:8000",
    api_key="your-api-key",
)

# Логирование конфигурации
exp.log_features({
    'model': {
        'architecture': 'ViT-Base',
        'patch_size': 16,
        'hidden_dim': 768,
    },
    'training': {
        'optimizer': 'AdamW',
        'learning_rate': 1e-4,
        'batch_size': 256,
        'epochs': 100,
    }
})

# Логирование кода
exp.log_code_snapshot("git_diff")

# Тренировка модели с логированием метрик
for epoch in range(100):
    for batch_idx, (images, labels) in enumerate(train_loader):
        # ... обучение ...
        
        loss = 0.42  # пример
        accuracy = 0.95
        
        step = epoch * len(train_loader) + batch_idx
        
        # Логирование одной метрики
        exp.log_metric("loss", loss, step=step)
        
        # Или через буфер (более эффективно)
        exp.buffer_metric("accuracy", accuracy, step=step)
        
        # Периодический flushh буфера
        if batch_idx % 100 == 0:
            exp.flush_metrics()
    
    print(f"Epoch {epoch} completed")

# Логирование артефактов
exp.log_artifacts(path="./checkpoints", pattern="*.pt")

# Завершение эксперимента
exp.finish(status="complete")

print("Experiment tracking completed!")
```

### 2. Анализ метрик через Python (Pandas)

```python
# examples/metric_analysis.py

import requests
import pandas as pd
from datetime import datetime

# Получить данные для нескольких экспериментов
api_url = "http://localhost:8000"
project_id = "550e8400-e29b-41d4-a716-446655440000"
experiment_ids = [
    "exp-001",
    "exp-002",
    "exp-003",
]

# Получить сравнение
response = requests.post(
    f"{api_url}/api/v1/metrics/compare",
    params={
        "project_id": project_id,
        "experiment_ids": experiment_ids,
    },
    headers={"Authorization": "Bearer your-token"},
)

comparison = response.json()

# Преобразовать в DataFrame
data = []
for exp_id, metrics in comparison['experiments'].items():
    for metric_name, values in metrics.items():
        data.append({
            'experiment': exp_id,
            'metric': metric_name,
            'last_value': values['last'],
        })

df = pd.DataFrame(data)
df_pivot = df.pivot(index='metric', columns='experiment', values='last_value')

print(df_pivot)
print("\nImprovement over baseline:")
baseline = df_pivot[experiment_ids[0]]
for exp in experiment_ids[1:]:
    improvement = (df_pivot[exp] - baseline) / baseline * 100
    print(f"\n{exp}:")
    print(improvement)
```

### 3. Интеграция с Hypothesis для automated testing

```python
# examples/hypothesis_evidence.py

from research_sdk import Experiment, HypothesisEvaluator

# Определить гипотезу
hypothesis_manager = HypothesisEvaluator(
    project="vision_transformer",
    hypothesis_id="h-lr-comparison",
    baseline_experiment="vit_base_lr_1e5",
    target_metrics=["loss", "accuracy"],
)

# Запустить несколько экспериментов с разными LR
lrs = [1e-5, 1e-4, 1e-3]

for lr in lrs:
    exp_name = f"vit_base_lr_{lr}".replace(".", "_")
    
    exp = Experiment(
        project="vision_transformer",
        name=exp_name,
    )
    
    exp.log_features({
        'learning_rate': lr,
    })
    
    # ... обучение ...
    
    for epoch in range(100):
        loss = train_epoch(model, data, lr)
        exp.log_metric("loss", loss, step=epoch)
    
    exp.finish(status="complete")

# Оценить гипотезу
hypothesis_manager.evaluate()
result = hypothesis_manager.get_result()

print(f"Hypothesis Status: {result['status']}")  # Supported/Refuted/Testing
print(f"Evidence Score: {result['evidence_score']}")
print(f"Confidence: {result['confidence']}")
```

---

## Развёртывание

### 1. Docker Compose для локальной разработки

```yaml
# docker-compose.yml

version: '3.8'

services:
  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
      POSTGRES_DB: research_platform
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data

  clickhouse:
    image: clickhouse/clickhouse-server:latest
    environment:
      CLICKHOUSE_DB: metrics
      CLICKHOUSE_USER: default
      CLICKHOUSE_PASSWORD: ""
    ports:
      - "9000:9000"      # Native port
      - "8123:8123"      # HTTP port
    volumes:
      - clickhouse_data:/var/lib/clickhouse
      - ./init-clickhouse.sql:/docker-entrypoint-initdb.d/init.sql

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data

  fastapi:
    build: .
    ports:
      - "8000:8000"
    environment:
      DATABASE_URL: postgresql://postgres:postgres@postgres:5432/research_platform
      CLICKHOUSE_HOST: clickhouse
      CLICKHOUSE_PORT: 9000
      REDIS_URL: redis://redis:6379
    depends_on:
      - postgres
      - clickhouse
      - redis
    volumes:
      - ./app:/app/app
    command: uvicorn app.main:app --host 0.0.0.0 --reload

volumes:
  postgres_data:
  clickhouse_data:
  redis_data:
```

### 2. Инициализационный скрипт ClickHouse

```sql
-- init-clickhouse.sql

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
    logged_at DateTime,
    host String DEFAULT ''
) ENGINE = ReplacingMergeTree()
ORDER BY (team_id, project_id, experiment_id, metric_name, timestamp)
PARTITION BY toYYYYMM(timestamp)
TTL timestamp + INTERVAL 2 YEAR DELETE;

-- Таблица для агрегированных данных
CREATE TABLE IF NOT EXISTS metrics_aggregated (
    date Date,
    team_id UUID,
    project_id UUID,
    experiment_id UUID,
    metric_name String,
    step UInt64,
    min_value Float64,
    max_value Float64,
    avg_value Float64,
    last_value Float64,
    count UInt64,
    timestamp DateTime DEFAULT now()
) ENGINE = ReplacingMergeTree()
ORDER BY (team_id, project_id, experiment_id, metric_name, date, step)
PARTITION BY toYYYYMM(date);

-- Таблица для evidence
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
    logged_at DateTime
) ENGINE = ReplacingMergeTree()
ORDER BY (team_id, project_id, hypothesis_id, experiment_id, metric_name, timestamp)
PARTITION BY toYYYYMM(timestamp);
```

### 3. Production конфигурация

```ini
# .env.production

# PostgreSQL
DATABASE_URL=postgresql://user:password@db.example.com:5432/research_platform

# ClickHouse
CLICKHOUSE_HOST=clickhouse.example.com
CLICKHOUSE_PORT=9000
CLICKHOUSE_USER=metrics_user
CLICKHOUSE_PASSWORD=secure_password
CLICKHOUSE_DATABASE=metrics

# Redis
REDIS_URL=redis://redis.example.com:6379/0

# FastAPI
LOG_LEVEL=INFO
WORKERS=4
ENVIRONMENT=production
```

---

## Миграция данных (PostgreSQL → ClickHouse)

```python
# app/scripts/migrate_metrics_to_clickhouse.py

import logging
from datetime import datetime
from typing import List
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.infrastructure.clickhouse.client import ClickHouseClient
from app.models import Experiment, Project
from app.config import settings

logger = logging.getLogger(__name__)

def migrate_metrics(batch_size: int = 10000):
    """Миграция метрик из какого-либо источника в ClickHouse"""
    
    # Инициализировать клиенты
    pg_engine = create_engine(settings.DATABASE_URL)
    Session = sessionmaker(bind=pg_engine)
    ch_client = ClickHouseClient(
        host=settings.CLICKHOUSE_HOST,
        port=settings.CLICKHOUSE_PORT,
        user=settings.CLICKHOUSE_USER,
        password=settings.CLICKHOUSE_PASSWORD,
    )
    
    session = Session()
    
    try:
        # Получить все проекты и эксперименты
        experiments = session.query(Experiment).all()
        
        total_metrics = 0
        
        for experiment in experiments:
            logger.info(f"Processing experiment {experiment.id}")
            
            # Получить метрики из источника (например, JSON-файла)
            metrics = _load_metrics_for_experiment(experiment.id)
            
            if not metrics:
                continue
            
            # Подготовить данные для ClickHouse
            ch_metrics = []
            for metric in metrics:
                ch_metrics.append({
                    'timestamp': metric['timestamp'],
                    'team_id': str(experiment.project.team_id),
                    'project_id': str(experiment.project_id),
                    'experiment_id': str(experiment.id),
                    'metric_name': metric['name'],
                    'metric_value': metric['value'],
                    'step': metric['step'],
                })
            
            # Загрузить в батчах
            for i in range(0, len(ch_metrics), batch_size):
                batch = ch_metrics[i:i+batch_size]
                ch_client.insert_metrics_batch(batch)
                total_metrics += len(batch)
                logger.info(f"Inserted {total_metrics} metrics so far")
        
        logger.info(f"Migration completed! Total metrics: {total_metrics}")
    
    finally:
        session.close()

def _load_metrics_for_experiment(experiment_id: str) -> List[dict]:
    """Загрузить метрики из источника"""
    # Реализовать в зависимости от источника
    # (JSON-файлы, старая БД, и т.д.)
    pass

if __name__ == "__main__":
    migrate_metrics()
```

---

## Заключение

**Ключевые выводы:**

1. ✅ **ClickHouse идеален для временных рядов метрик** — columnar storage, fast aggregations
2. ✅ **PostgreSQL для metadata и иерархии** — гипотезы, эксперименты, особенности
3. ✅ **Team-based partitioning** — безопасная изоляция данных
4. ✅ **Batch insertion** — для оптимальной производительности
5. ✅ **Materialized Views** — для автоматической агрегации
6. ✅ **SDK с буфферизацией** — минимизирует нагрузку на сеть

**Архитектура готова к масштабированию до миллиардов метрик!**
