# ClickHouse Metrics для Research Platform: Практический Guide

## Расширенные сценарии использования

### 1. Интеграция с Evidence Model

Ваш PRD описывает **Evidence Model** — систему для оценки гипотез через метрики. Вот как это работает с ClickHouse:

```python
# app/services/evidence_service.py

from typing import List, Dict, Optional
from uuid import UUID
from datetime import datetime
from enum import Enum
from app.infrastructure.clickhouse.client import ClickHouseClient
from app.models import Hypothesis, ProjectMetric

class MetricDirection(str, Enum):
    MINIMIZE = "minimize"
    MAXIMIZE = "maximize"

class EvidenceService:
    """Сервис для вычисления Evidence Units и статусов гипотез"""
    
    def __init__(self, clickhouse: ClickHouseClient):
        self.ch = clickhouse
    
    def compute_evidence_unit(
        self,
        team_id: UUID,
        project_id: UUID,
        hypothesis_id: UUID,
        experiment_id: UUID,
        metric_name: str,
        baseline_value: float,
        direction: MetricDirection,
    ) -> Dict:
        """
        Вычислить Evidence Unit — вклад одного эксперимента в одну гипотезу
        
        Evidence Unit содержит:
        - baseline_value: значение в базовом эксперименте
        - experiment_value: значение в текущем эксперименте
        - delta: разница (signed)
        - normalized_delta: нормализованная разница
        - confidence_score: уверенность в метрике
        """
        
        # Получить последнее значение метрики в этом эксперименте
        experiment_metric = self.ch.get_experiment_metrics_summary(
            team_id=str(team_id),
            project_id=str(project_id),
            experiment_id=str(experiment_id),
        )
        
        if metric_name not in experiment_metric:
            return None  # Метрика не залогирована
        
        experiment_value = experiment_metric[metric_name]['last']
        
        # Вычислить delta в зависимости от направления
        if direction == MetricDirection.MAXIMIZE:
            delta = experiment_value - baseline_value
            normalized_delta = delta / max(abs(baseline_value), 1e-6)
        else:  # MINIMIZE
            delta = baseline_value - experiment_value
            normalized_delta = delta / max(abs(baseline_value), 1e-6)
        
        # Вычислить confidence score
        # (можно основать на стабильности метрики, количестве точек, и т.д.)
        metric_summary = experiment_metric[metric_name]
        variance = (metric_summary['max'] - metric_summary['min']) / max(
            abs(metric_summary['avg']), 1e-6
        )
        confidence_score = 1.0 / (1.0 + variance)  # Низкая дисперсия = высокая уверенность
        
        evidence_unit = {
            'hypothesis_id': str(hypothesis_id),
            'experiment_id': str(experiment_id),
            'metric_name': metric_name,
            'baseline_value': baseline_value,
            'experiment_value': experiment_value,
            'delta': delta,
            'normalized_delta': normalized_delta,
            'direction': direction.value,
            'confidence_score': confidence_score,
            'timestamp': datetime.utcnow(),
        }
        
        # Сохранить в ClickHouse для дальнейшего анализа
        self._store_evidence_unit(team_id, project_id, evidence_unit)
        
        return evidence_unit
    
    def _store_evidence_unit(
        self,
        team_id: UUID,
        project_id: UUID,
        evidence_unit: Dict,
    ):
        """Сохранить Evidence Unit в ClickHouse"""
        query = """
            INSERT INTO evidence_metrics (
                timestamp, team_id, project_id, hypothesis_id, experiment_id,
                metric_name, baseline_value, experiment_value, delta,
                direction, confidence_score, logged_at
            ) VALUES
        """
        
        direction_enum = 0 if evidence_unit['direction'] == 'minimize' else 1
        
        data = [(
            evidence_unit['timestamp'],
            team_id,
            project_id,
            UUID(evidence_unit['hypothesis_id']),
            UUID(evidence_unit['experiment_id']),
            evidence_unit['metric_name'],
            evidence_unit['baseline_value'],
            evidence_unit['experiment_value'],
            evidence_unit['delta'],
            direction_enum,
            evidence_unit['confidence_score'],
            datetime.utcnow(),
        )]
        
        self.ch.client.execute(query, data)
    
    def aggregate_hypothesis_evidence(
        self,
        team_id: UUID,
        project_id: UUID,
        hypothesis_id: UUID,
    ) -> Dict:
        """
        Агрегировать Evidence Units в Hypothesis-level Evidence
        
        E_hypothesis = Σ (confidence_i × normalized_delta_i)
        """
        
        query = """
            SELECT
                SUM(confidence_score * normalized_delta) as total_evidence,
                COUNT(*) as unit_count,
                SUM(confidence_score) as total_confidence
            FROM evidence_metrics
            WHERE team_id = %(team_id)s
              AND project_id = %(project_id)s
              AND hypothesis_id = %(hypothesis_id)s
        """
        
        result = self.ch.client.execute(
            query,
            params={
                'team_id': str(team_id),
                'project_id': str(project_id),
                'hypothesis_id': str(hypothesis_id),
            }
        )
        
        if not result or result[0][1] == 0:
            return {
                'total_evidence': 0.0,
                'unit_count': 0,
                'status': 'no_evidence',
            }
        
        total_evidence, unit_count, total_confidence = result[0]
        avg_confidence = total_confidence / unit_count if unit_count > 0 else 0
        
        # Определить статус на основе пороговых значений (configurable)
        SUPPORT_THRESHOLD = 0.5
        REFUTE_THRESHOLD = -0.5
        
        if total_evidence > SUPPORT_THRESHOLD:
            status = 'supported'
        elif total_evidence < REFUTE_THRESHOLD:
            status = 'refuted'
        else:
            status = 'testing'
        
        return {
            'total_evidence': total_evidence,
            'unit_count': unit_count,
            'avg_confidence': avg_confidence,
            'status': status,
        }
```

### 2. Celery Task для async обработки метрик

```python
# app/tasks/metrics_tasks.py

from celery import shared_task, group
from uuid import UUID
from typing import List
from app.infrastructure.clickhouse.client import ClickHouseClient
from app.models import Hypothesis, Experiment, ProjectMetric
from app.services.evidence_service import EvidenceService
from app.database import SessionLocal

@shared_task(bind=True, max_retries=3)
def process_metric_stream(
    self,
    team_id: str,
    project_id: str,
    experiment_id: str,
    metrics_batch: List[dict],
):
    """
    Celery task для async обработки потока метрик
    
    При получении батча метрик:
    1. Вставить в ClickHouse
    2. Обновить связанные Evidence Units
    3. Обновить статусы гипотез
    """
    
    ch = ClickHouseClient()
    db = SessionLocal()
    
    try:
        # Шаг 1: Вставить метрики в ClickHouse
        formatted_metrics = [
            {
                'timestamp': m['timestamp'],
                'team_id': team_id,
                'project_id': project_id,
                'experiment_id': experiment_id,
                'metric_name': m['metric_name'],
                'metric_value': m['metric_value'],
                'step': m['step'],
            }
            for m in metrics_batch
        ]
        
        ch.insert_metrics_batch(formatted_metrics)
        
        # Шаг 2: Найти все гипотезы, которые используют эту метрику
        experiment = db.query(Experiment).filter(
            Experiment.id == experiment_id
        ).first()
        
        if not experiment:
            return
        
        metric_names = set(m['metric_name'] for m in metrics_batch)
        
        hypotheses = db.query(Hypothesis).filter(
            Hypothesis.project_id == project_id,
            Hypothesis.target_metrics.overlap(list(metric_names))  # PostgreSQL array overlap
        ).all()
        
        # Шаг 3: Обновить Evidence Units для каждой гипотезы
        evidence_service = EvidenceService(ch)
        
        for hypothesis in hypotheses:
            for metric_name in metric_names:
                if metric_name in hypothesis.target_metrics:
                    # Найти baseline эксперимент
                    baseline_exp = get_baseline_experiment(
                        db, project_id, hypothesis.baseline
                    )
                    
                    if baseline_exp:
                        # Получить baseline значение
                        baseline_summary = ch.get_experiment_metrics_summary(
                            team_id=team_id,
                            project_id=project_id,
                            experiment_id=str(baseline_exp.id),
                        )
                        
                        if metric_name in baseline_summary:
                            baseline_value = baseline_summary[metric_name]['last']
                            
                            # Получить метрику в проекте для direction
                            project_metric = db.query(ProjectMetric).filter(
                                ProjectMetric.project_id == project_id,
                                ProjectMetric.name == metric_name,
                            ).first()
                            
                            if project_metric:
                                evidence_service.compute_evidence_unit(
                                    team_id=team_id,
                                    project_id=project_id,
                                    hypothesis_id=hypothesis.id,
                                    experiment_id=experiment_id,
                                    metric_name=metric_name,
                                    baseline_value=baseline_value,
                                    direction=project_metric.direction,
                                )
        
        # Шаг 4: Обновить статусы гипотез
        for hypothesis in hypotheses:
            evidence = evidence_service.aggregate_hypothesis_evidence(
                team_id=team_id,
                project_id=project_id,
                hypothesis_id=hypothesis.id,
            )
            
            hypothesis.status = evidence['status']
            db.commit()
    
    except Exception as exc:
        self.retry(exc=exc, countdown=60)
    
    finally:
        db.close()

@shared_task
def aggregate_daily_metrics(team_id: str, project_id: str, date: str):
    """
    Ежедневное агрегирование метрик в metrics_aggregated table
    (запускается как cron job в ночное время)
    """
    ch = ClickHouseClient()
    
    # Запрос для агрегирования данных за день
    query = f"""
        INSERT INTO metrics_aggregated
        SELECT
            toDate(timestamp) as date,
            team_id,
            project_id,
            experiment_id,
            metric_name,
            0 as step,  # Агрегированные данные не имеют шага
            min(metric_value) as min_value,
            max(metric_value) as max_value,
            avg(metric_value) as avg_value,
            argMax(metric_value, timestamp) as last_value,
            count() as count,
            now() as timestamp
        FROM metrics
        WHERE team_id = '{team_id}'
          AND project_id = '{project_id}'
          AND toDate(timestamp) = '{date}'
        GROUP BY team_id, project_id, experiment_id, metric_name, date
    """
    
    ch.client.execute(query)

def get_baseline_experiment(db, project_id: str, baseline: str):
    """Получить baseline эксперимент по конфигурации"""
    if baseline == 'root':
        # Найти root эксперимент проекта (первый в DAG)
        return db.query(Experiment).filter(
            Experiment.project_id == project_id,
            Experiment.parent_experiment_id.is_(None),
        ).first()
    elif baseline == 'best':
        # Найти эксперимент с лучшей метрикой (реализовать через Evidence)
        # Упрощено для примера
        return db.query(Experiment).filter(
            Experiment.project_id == project_id,
        ).order_by(Experiment.created_at.desc()).first()
    else:
        # baseline это experiment_id
        return db.query(Experiment).filter(
            Experiment.id == baseline,
        ).first()
```

### 3. Метрики для Hypothesis View в API

```python
# app/api/v1/endpoints/hypotheses.py

from fastapi import APIRouter, Depends, HTTPException
from uuid import UUID
from typing import List, Dict, Any
from app.core.dependencies import get_clickhouse_client, get_current_user
from app.core.security import AccessControl
from app.services.evidence_service import EvidenceService
from app.database import get_db

router = APIRouter(prefix="/api/v1/hypotheses", tags=["hypotheses"])

@router.get("/{project_id}/{hypothesis_id}/evidence")
async def get_hypothesis_evidence(
    project_id: UUID,
    hypothesis_id: UUID,
    clickhouse: ClickHouseClient = Depends(get_clickhouse_client),
    current_user = Depends(get_current_user),
    db = Depends(get_db),
):
    """
    Получить агрегированное Evidence для гипотезы
    Включает все Evidence Units и финальный статус
    """
    
    # Проверка доступа
    await AccessControl.verify_project_access(
        team_id=current_user.team_id,
        project_id=project_id,
        current_user=current_user,
        db=db,
    )
    
    evidence_service = EvidenceService(clickhouse)
    
    # Получить агрегированное evidence
    hypothesis_evidence = evidence_service.aggregate_hypothesis_evidence(
        team_id=current_user.team_id,
        project_id=project_id,
        hypothesis_id=hypothesis_id,
    )
    
    # Получить детальное Evidence Units
    query = """
        SELECT
            experiment_id,
            metric_name,
            baseline_value,
            experiment_value,
            delta,
            confidence_score,
            timestamp
        FROM evidence_metrics
        WHERE team_id = %(team_id)s
          AND project_id = %(project_id)s
          AND hypothesis_id = %(hypothesis_id)s
        ORDER BY timestamp DESC
    """
    
    result = clickhouse.client.execute(
        query,
        params={
            'team_id': str(current_user.team_id),
            'project_id': str(project_id),
            'hypothesis_id': str(hypothesis_id),
        }
    )
    
    evidence_units = [
        {
            'experiment_id': row[0],
            'metric_name': row[1],
            'baseline_value': row[2],
            'experiment_value': row[3],
            'delta': row[4],
            'confidence_score': row[5],
            'timestamp': row[6],
        }
        for row in result
    ]
    
    return {
        'project_id': str(project_id),
        'hypothesis_id': str(hypothesis_id),
        'status': hypothesis_evidence['status'],
        'total_evidence': hypothesis_evidence['total_evidence'],
        'unit_count': hypothesis_evidence['unit_count'],
        'avg_confidence': hypothesis_evidence['avg_confidence'],
        'evidence_units': evidence_units,
    }

@router.get("/{project_id}/metrics-comparison")
async def get_metrics_comparison(
    project_id: UUID,
    experiment_ids: List[UUID],
    metric_names: List[str] = None,
    clickhouse: ClickHouseClient = Depends(get_clickhouse_client),
    current_user = Depends(get_current_user),
    db = Depends(get_db),
):
    """
    Получить таблицу сравнения метрик между экспериментами
    Для Project Metrics Overview view
    
    Returns:
        {
            'experiments': ['exp-1', 'exp-2', 'exp-3'],
            'metrics': {
                'loss': [0.42, 0.38, 0.45],
                'accuracy': [0.95, 0.96, 0.94],
            },
            'improvements': {
                'exp-2': {'loss': -0.095, 'accuracy': 0.0105},
            }
        }
    """
    
    # Проверка доступа
    await AccessControl.verify_project_access(
        team_id=current_user.team_id,
        project_id=project_id,
        current_user=current_user,
        db=db,
    )
    
    # Получить сравнение
    comparison = clickhouse.compare_experiments(
        team_id=str(current_user.team_id),
        project_id=str(project_id),
        experiment_ids=[str(e) for e in experiment_ids],
        metric_names=metric_names,
    )
    
    # Вычислить improvements (baseline = первый эксперимент)
    baseline_exp = str(experiment_ids[0])
    improvements = {}
    
    for exp_id in comparison:
        if exp_id != baseline_exp:
            improvements[exp_id] = {}
            for metric_name in comparison[exp_id]:
                if metric_name in comparison[baseline_exp]:
                    baseline_val = comparison[baseline_exp][metric_name]['last']
                    current_val = comparison[exp_id][metric_name]['last']
                    improvements[exp_id][metric_name] = current_val - baseline_val
    
    return {
        'project_id': str(project_id),
        'baseline_experiment': baseline_exp,
        'experiments': [str(e) for e in experiment_ids],
        'comparison': comparison,
        'improvements': improvements,
    }
```

### 4. Real-time WebSocket для метрик (опционально)

```python
# app/api/v1/websockets/metrics_stream.py

from fastapi import APIRouter, WebSocket, Depends
from uuid import UUID
import json
import asyncio
from app.core.dependencies import get_current_user
from app.infrastructure.clickhouse.client import ClickHouseClient

router = APIRouter(prefix="/api/v1/ws")

@router.websocket("/metrics/{project_id}/{experiment_id}")
async def websocket_metrics_stream(
    websocket: WebSocket,
    project_id: UUID,
    experiment_id: UUID,
    current_user = Depends(get_current_user),
):
    """
    WebSocket для real-time метрик эксперимента
    Клиент подключается, и получает обновления каждую секунду
    """
    
    await websocket.accept()
    clickhouse = ClickHouseClient()
    
    try:
        while True:
            # Получить обновлённые метрики каждую секунду
            summary = clickhouse.get_experiment_metrics_summary(
                team_id=str(current_user.team_id),
                project_id=str(project_id),
                experiment_id=str(experiment_id),
            )
            
            # Отправить на клиент
            await websocket.send_json({
                'type': 'metrics_update',
                'timestamp': datetime.utcnow().isoformat(),
                'metrics': summary,
            })
            
            await asyncio.sleep(1)
    
    except Exception as e:
        await websocket.close(code=1000)
```

---

## Оптимизация queryий в production

### 1. Query Profiling

```python
# app/utils/clickhouse_profiler.py

import time
import logging
from functools import wraps
from app.infrastructure.clickhouse.client import ClickHouseClient

logger = logging.getLogger(__name__)

def profile_clickhouse_query(func):
    """Декоратор для профилирования ClickHouse запросов"""
    
    @wraps(func)
    def wrapper(*args, **kwargs):
        start = time.time()
        result = func(*args, **kwargs)
        elapsed = time.time() - start
        
        logger.info(
            f"ClickHouse query '{func.__name__}' took {elapsed:.2f}s"
        )
        
        if elapsed > 5.0:
            logger.warning(
                f"Slow query detected in {func.__name__}: {elapsed:.2f}s"
            )
        
        return result
    
    return wrapper

# Использование:
@profile_clickhouse_query
def get_metrics_for_report(team_id, project_id):
    # ... код ...
    pass
```

### 2. Кэширование часто используемых запросов

```python
# app/cache/metrics_cache.py

from typing import Optional, Dict, Any
from functools import lru_cache
import hashlib
from datetime import datetime, timedelta

class MetricsCache:
    """Простой TTL-кэш для метрик"""
    
    def __init__(self, ttl_seconds: int = 60):
        self.ttl = ttl_seconds
        self.cache = {}
        self.timestamps = {}
    
    def get_cache_key(self, **kwargs) -> str:
        """Генерировать уникальный ключ кэша"""
        key_str = '|'.join(f"{k}={v}" for k, v in sorted(kwargs.items()))
        return hashlib.md5(key_str.encode()).hexdigest()
    
    def get(self, key: str) -> Optional[Any]:
        """Получить значение из кэша"""
        if key in self.cache:
            if datetime.utcnow() - self.timestamps[key] < timedelta(seconds=self.ttl):
                return self.cache[key]
            else:
                del self.cache[key]
                del self.timestamps[key]
        return None
    
    def set(self, key: str, value: Any):
        """Установить значение в кэш"""
        self.cache[key] = value
        self.timestamps[key] = datetime.utcnow()
    
    def clear(self):
        """Очистить кэш"""
        self.cache.clear()
        self.timestamps.clear()

# Global cache instance
metrics_cache = MetricsCache(ttl_seconds=60)

# Использование с ClickHouse client:
class CachedClickHouseClient:
    
    def __init__(self, ch_client: ClickHouseClient):
        self.ch = ch_client
        self.cache = metrics_cache
    
    def get_experiment_metrics_summary(
        self,
        team_id: str,
        project_id: str,
        experiment_id: str,
    ) -> Dict[str, Dict[str, float]]:
        """Получить сводку с кэшированием"""
        
        cache_key = self.cache.get_cache_key(
            team_id=team_id,
            project_id=project_id,
            experiment_id=experiment_id,
        )
        
        cached = self.cache.get(cache_key)
        if cached:
            return cached
        
        result = self.ch.get_experiment_metrics_summary(
            team_id=team_id,
            project_id=project_id,
            experiment_id=experiment_id,
        )
        
        self.cache.set(cache_key, result)
        return result
```

---

## Мониторинг и алерты

### 1. Health check для ClickHouse

```python
# app/api/v1/health.py

from fastapi import APIRouter, Depends
from app.core.dependencies import get_clickhouse_client
import logging

router = APIRouter(prefix="/health", tags=["health"])

@router.get("/clickhouse")
async def check_clickhouse_health(
    clickhouse = Depends(get_clickhouse_client),
):
    """Проверить здоровье ClickHouse"""
    
    try:
        # Простой тест — получить текущее время из ClickHouse
        result = clickhouse.client.execute("SELECT now()")
        
        return {
            'status': 'healthy',
            'database': 'clickhouse',
            'timestamp': result[0][0],
        }
    
    except Exception as e:
        logging.error(f"ClickHouse health check failed: {e}")
        return {
            'status': 'unhealthy',
            'database': 'clickhouse',
            'error': str(e),
        }

@router.get("/metrics-ingestion")
async def check_metrics_ingestion(
    clickhouse = Depends(get_clickhouse_client),
):
    """Проверить, идёт ли приём метрик"""
    
    try:
        # Получить количество строк за последний час
        result = clickhouse.client.execute("""
            SELECT count() FROM metrics
            WHERE timestamp > now() - INTERVAL 1 HOUR
        """)
        
        count = result[0][0]
        
        status = 'healthy' if count > 0 else 'degraded'
        
        return {
            'status': status,
            'metrics_last_hour': count,
        }
    
    except Exception as e:
        return {
            'status': 'unhealthy',
            'error': str(e),
        }
```

### 2. Alerting

```python
# app/monitoring/alerts.py

import logging
from datetime import datetime, timedelta
from app.infrastructure.clickhouse.client import ClickHouseClient

logger = logging.getLogger(__name__)

class MetricsAlertManager:
    """Управление алертами для метрик"""
    
    def __init__(self, clickhouse: ClickHouseClient):
        self.ch = clickhouse
    
    def check_no_metrics_ingestion(self) -> bool:
        """Алерт: нет приёма метрик > 30 минут"""
        
        result = self.ch.client.execute("""
            SELECT count() FROM metrics
            WHERE timestamp > now() - INTERVAL 30 MINUTE
        """)
        
        count = result[0][0]
        
        if count == 0:
            logger.error("ALERT: No metrics ingestion for 30 minutes!")
            return True
        
        return False
    
    def check_disk_usage(self) -> bool:
        """Алерт: использование диска > 80%"""
        
        result = self.ch.client.execute("""
            SELECT
                (sum(bytes_on_disk) / sum(total_bytes)) * 100 as usage_percent
            FROM system.tables
            WHERE database = 'metrics'
        """)
        
        if result:
            usage = result[0][0]
            if usage > 80:
                logger.warning(f"ALERT: ClickHouse disk usage at {usage}%")
                return True
        
        return False

# Запустить как Celery beat task:
from celery.beat import schedule
from celery import app

@app.task
def run_metrics_health_checks():
    """Ежеминутная проверка здоровья метрик"""
    
    ch = ClickHouseClient()
    alert_manager = MetricsAlertManager(ch)
    
    alert_manager.check_no_metrics_ingestion()
    alert_manager.check_disk_usage()

# В celery config:
app.conf.beat_schedule = {
    'check-metrics-health': {
        'task': 'app.monitoring.alerts.run_metrics_health_checks',
        'schedule': schedule(run_every=60),  # Каждую минуту
    },
}
```

---

## FAQ и Troubleshooting

### Q1: Как избежать дублирования метрик?

**A:** Используйте ReplacingMergeTree с уникальным ключом:

```sql
-- Если один и тот же (experiment_id, metric_name, step) залогирован дважды
-- ClickHouse оставит только последнее значение (с последним logged_at)
CREATE TABLE metrics (
    timestamp DateTime,
    team_id UUID,
    project_id UUID,
    experiment_id UUID,
    metric_name String,
    metric_value Float64,
    step UInt64,
    logged_at DateTime,
    version UInt64  -- Версия для ReplacingMergeTree
) ENGINE = ReplacingMergeTree(logged_at)
ORDER BY (team_id, project_id, experiment_id, metric_name, step);
```

### Q2: Как запросить метрики, хранящиеся > 2 лет назад, если у нас TTL?

**A:** TTL (Time-To-Live) удаляет старые данные автоматически. Если нужно хранить долго:

```sql
ALTER TABLE metrics MODIFY TTL timestamp + INTERVAL 10 YEAR DELETE;
```

Или для архивирования на S3:

```sql
ALTER TABLE metrics MODIFY TTL timestamp + INTERVAL 2 YEAR TO DISK 's3_archive';
```

### Q3: Как оптимизировать запросы для больших датасетов?

**A:** Используйте PREWHERE (фильтрация до чтения столбцов):

```sql
-- ❌ Медленно (читает все столбцы, потом фильтрует)
SELECT metric_value FROM metrics
WHERE team_id = 'xxx' AND metric_name = 'loss';

-- ✅ Быстро (фильтрует в PREWHERE, потом читает нужные столбцы)
SELECT metric_value FROM metrics
PREWHERE team_id = 'xxx' AND metric_name = 'loss';
```

### Q4: Как скейлировать ClickHouse на миллиарды метрик?

**A:** Используйте распределённые таблицы (Distributed engine):

```sql
-- На каждом шарде (узле) создать локальную таблицу
CREATE TABLE metrics_local (
    -- как выше
) ENGINE = ReplacingMergeTree() ...;

-- На coordinator узле создать распределённую таблицу
CREATE TABLE metrics (
    -- как выше
) ENGINE = Distributed(
    'cluster_name',
    'metrics',          -- database
    'metrics_local',    -- local table name
    rand()              -- sharding key
);
```

---

## Заключение

**Ключевые компоненты для полной интеграции ClickHouse:**

1. ✅ **ClickHouseClient** — обёртка над драйвером
2. ✅ **EvidenceService** — вычисление гипотез через метрики
3. ✅ **Celery tasks** — async обработка потоков
4. ✅ **FastAPI endpoints** — REST API для метрик
5. ✅ **WebSocket** — real-time обновления (опционально)
6. ✅ **Кэширование** — оптимизация производительности
7. ✅ **Мониторинг** — health checks и алерты

Архитектура готова к **production** с поддержкой:
- Многопользовательской изоляции (team-based)
- Истории метрик и Evidence Units
- Real-time обновлений
- Масштабирования до миллиардов точек
- Гипотез и сравнения экспериментов
