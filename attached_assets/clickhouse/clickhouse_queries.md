# ClickHouse Queries для Research Platform

## Часть 1: Диаграммы взаимодействия

### Data Flow при логировании метрик

```
SDK (Python) на тренировке
        ↓
[metric_name="loss", value=0.42, step=10]
        ↓
HTTP POST /api/v1/metrics/batch (батч из 100 метрик)
        ↓
FastAPI Endpoint (проверка прав через team_id)
        ↓
ClickHouseClient.insert_metrics_batch()
        ↓
INSERT INTO metrics (ClickHouse)
        ↓
Celery Task: process_metric_stream()
  ├─ Получить все гипотезы, использующие метрику
  ├─ Вычислить Evidence Units
  ├─ INSERT INTO evidence_metrics
  └─ UPDATE hypothesis.status в PostgreSQL
```

### Evidence Model Flow

```
Hypothesis: "AdamW с lr=1e-4 быстрее сходится"
    ↓
target_metrics: ["loss", "accuracy"]
baseline: "exp-0-baseline"
    ↓
[Exp-1: loss=0.42, acc=0.95]
[Exp-2: loss=0.38, acc=0.96]
[Exp-3: loss=0.45, acc=0.93]
    ↓
Evidence Unit для каждого exp:
    Exp-1: delta_loss = -0.08, delta_acc = +0.05, confidence=0.8
    Exp-2: delta_loss = -0.04, delta_acc = +0.06, confidence=0.85
    Exp-3: delta_loss = +0.03, delta_acc = -0.02, confidence=0.7
    ↓
Hypothesis Evidence = SUM(confidence * normalized_delta)
    = 0.8*(-0.08) + 0.85*(-0.04) + 0.7*(0.03) + ...
    = -0.064 - 0.034 + 0.021 = -0.077
    ↓
Status = "Testing" (между -0.5 и 0.5)
```

---

## Часть 2: SQL Queries для анализа

### 1. Получить метрики эксперимента

```sql
-- Последние 100 значений метрики "loss" для exp-123
SELECT
    timestamp,
    step,
    metric_value as loss
FROM metrics
WHERE team_id = '550e8400-e29b-41d4-a716-446655440001'
  AND project_id = '550e8400-e29b-41d4-a716-446655440002'
  AND experiment_id = '550e8400-e29b-41d4-a716-446655440123'
  AND metric_name = 'loss'
ORDER BY timestamp ASC
LIMIT 100;
```

### 2. Сравнение трёх экспериментов

```sql
-- Финальные значения метрик для 3 экспериментов
SELECT
    experiment_id,
    metric_name,
    argMax(metric_value, timestamp) as final_value
FROM metrics
WHERE team_id = '550e8400-e29b-41d4-a716-446655440001'
  AND project_id = '550e8400-e29b-41d4-a716-446655440002'
  AND experiment_id IN (
      '550e8400-e29b-41d4-a716-446655440111',
      '550e8400-e29b-41d4-a716-446655440112',
      '550e8400-e29b-41d4-a716-446655440113'
  )
GROUP BY experiment_id, metric_name
ORDER BY experiment_id, metric_name;
```

**Result (pivot для удобства):**
```
┌──────────────────┬───────────────┬────────────┐
│ experiment_id    │ metric_name   │ final_value│
├──────────────────┼───────────────┼────────────┤
│ exp-111          │ loss          │ 0.42       │
│ exp-111          │ accuracy      │ 0.95       │
│ exp-112          │ loss          │ 0.38       │
│ exp-112          │ accuracy      │ 0.96       │
│ exp-113          │ loss          │ 0.45       │
│ exp-113          │ accuracy      │ 0.93       │
└──────────────────┴───────────────┴────────────┘
```

### 3. Тренды: улучшение/ухудшение

```sql
-- Как менялись метрики от эксперимента к эксперименту
-- (DAG порядок: exp-0 → exp-1 → exp-2 → exp-3)
WITH metric_timeline AS (
    SELECT
        experiment_id,
        metric_name,
        argMax(metric_value, timestamp) as final_value,
        COUNT(*) as point_count
    FROM metrics
    WHERE team_id = '550e8400-e29b-41d4-a716-446655440001'
      AND project_id = '550e8400-e29b-41d4-a716-446655440002'
    GROUP BY experiment_id, metric_name
)
SELECT
    metric_name,
    experiment_id,
    final_value,
    LAG(final_value) OVER (
        PARTITION BY metric_name 
        ORDER BY experiment_id
    ) as prev_value,
    final_value - LAG(final_value) OVER (
        PARTITION BY metric_name 
        ORDER BY experiment_id
    ) as delta
FROM metric_timeline
ORDER BY metric_name, experiment_id;
```

### 4. Найти лучший эксперимент по метрике

```sql
-- Найти experiment с минимальной потерей (MINIMIZE)
SELECT
    experiment_id,
    metric_name,
    MIN(metric_value) as min_loss,
    argMinIf(timestamp, metric_value, timestamp > now() - INTERVAL 24 HOUR) as time_achieved
FROM metrics
WHERE team_id = '550e8400-e29b-41d4-a716-446655440001'
  AND project_id = '550e8400-e29b-41d4-a716-446655440002'
  AND metric_name = 'loss'
GROUP BY experiment_id, metric_name
ORDER BY min_loss ASC
LIMIT 1;
```

### 5. Evidence для гипотезы

```sql
-- Все Evidence Units для гипотезы h-123
SELECT
    experiment_id,
    metric_name,
    baseline_value,
    experiment_value,
    delta,
    IF(direction = 0, 'minimize', 'maximize') as direction,
    confidence_score,
    timestamp
FROM evidence_metrics
WHERE team_id = '550e8400-e29b-41d4-a716-446655440001'
  AND project_id = '550e8400-e29b-41d4-a716-446655440002'
  AND hypothesis_id = '550e8400-e29b-41d4-a716-446655440321'
ORDER BY timestamp DESC;
```

**Result:**
```
┌──────────────┬─────────────┬────────┬─────────────┬────────┬──────┬───────────┬──────────┐
│ experiment   │ metric      │baseline│experiment   │ delta  │ dir  │confidence│timestamp │
├──────────────┼─────────────┼────────┼─────────────┼────────┼──────┼───────────┼──────────┤
│ exp-1        │ loss        │ 0.50   │ 0.42        │-0.08   │min   │ 0.80     │ 2024-... │
│ exp-1        │ accuracy    │ 0.90   │ 0.95        │+0.05   │max   │ 0.85     │ 2024-... │
│ exp-2        │ loss        │ 0.50   │ 0.38        │-0.12   │min   │ 0.75     │ 2024-... │
│ exp-2        │ accuracy    │ 0.90   │ 0.96        │+0.06   │max   │ 0.82     │ 2024-... │
└──────────────┴─────────────┴────────┴─────────────┴────────┴──────┴───────────┴──────────┘
```

### 6. Статистика гипотезы

```sql
-- Агрегированное Evidence для гипотезы
SELECT
    hypothesis_id,
    COUNT(*) as unit_count,
    SUM(confidence_score * delta) as total_evidence,
    AVG(confidence_score) as avg_confidence,
    MIN(experiment_value) as best_value,
    MAX(experiment_value) as worst_value
FROM evidence_metrics
WHERE team_id = '550e8400-e29b-41d4-a716-446655440001'
  AND project_id = '550e8400-e29b-41d4-a716-446655440002'
  AND hypothesis_id = '550e8400-e29b-41d4-a716-446655440321'
GROUP BY hypothesis_id;
```

### 7. Самые нестабильные метрики

```sql
-- Метрики с высокой дисперсией (требуют внимания)
SELECT
    experiment_id,
    metric_name,
    COUNT(*) as points,
    AVG(metric_value) as avg_value,
    MIN(metric_value) as min_value,
    MAX(metric_value) as max_value,
    MAX(metric_value) - MIN(metric_value) as range,
    stddevPopStable(metric_value) as stddev
FROM metrics
WHERE team_id = '550e8400-e29b-41d4-a716-446655440001'
  AND project_id = '550e8400-e29b-41d4-a716-446655440002'
  AND timestamp > now() - INTERVAL 7 DAY
GROUP BY experiment_id, metric_name
HAVING stddev > 0.1
ORDER BY stddev DESC;
```

### 8. Скорость сходимости метрики

```sql
-- На каком шаге метрика достигла целевого значения
WITH metric_steps AS (
    SELECT
        experiment_id,
        step,
        metric_value,
        LAG(metric_value) OVER (
            PARTITION BY experiment_id 
            ORDER BY step
        ) as prev_value
    FROM metrics
    WHERE team_id = '550e8400-e29b-41d4-a716-446655440001'
      AND project_id = '550e8400-e29b-41d4-a716-446655440002'
      AND metric_name = 'loss'
)
SELECT
    experiment_id,
    MIN(step) as converged_at_step,
    COUNT(*) as total_steps
FROM metric_steps
WHERE metric_value < 0.4  -- Target value
GROUP BY experiment_id;
```

### 9. Сравнение распределений метрик между группами экспериментов

```sql
-- Разделить эксперименты на группы (batch size: большой vs маленький)
-- и сравнить метрики
SELECT
    CASE 
        WHEN experiment_id LIKE 'exp-batch-large-%' THEN 'Large Batch'
        WHEN experiment_id LIKE 'exp-batch-small-%' THEN 'Small Batch'
        ELSE 'Other'
    END as group_name,
    metric_name,
    COUNT(*) as samples,
    AVG(metric_value) as mean,
    quantile(0.5)(metric_value) as median,
    quantile(0.25)(metric_value) as q25,
    quantile(0.75)(metric_value) as q75,
    stddevPopStable(metric_value) as stddev
FROM metrics
WHERE team_id = '550e8400-e29b-41d4-a716-446655440001'
  AND project_id = '550e8400-e29b-41d4-a716-446655440002'
GROUP BY group_name, metric_name
ORDER BY group_name, metric_name;
```

### 10. Метрики, которые не скачут (стабильные)

```sql
-- Найти метрики с коэффициентом вариации < 0.1 (стабильные)
WITH metric_stats AS (
    SELECT
        experiment_id,
        metric_name,
        AVG(metric_value) as mean_value,
        stddevPopStable(metric_value) as std_value,
        stddevPopStable(metric_value) / AVG(metric_value) as cv
    FROM metrics
    WHERE team_id = '550e8400-e29b-41d4-a716-446655440001'
      AND project_id = '550e8400-e29b-41d4-a716-446655440002'
      AND timestamp > now() - INTERVAL 1 DAY
    GROUP BY experiment_id, metric_name
)
SELECT *
FROM metric_stats
WHERE cv < 0.1
ORDER BY experiment_id, metric_name;
```

---

## Часть 3: Python примеры для анализа

### Используя httpx для API calls

```python
# examples/analysis_client.py

import httpx
import pandas as pd
from typing import List, Dict
from uuid import UUID

class ResearchAnalysisClient:
    def __init__(self, base_url: str, token: str):
        self.base_url = base_url
        self.token = token
        self.headers = {"Authorization": f"Bearer {token}"}
    
    async def get_experiment_comparison(
        self,
        project_id: UUID,
        experiment_ids: List[UUID],
    ) -> pd.DataFrame:
        """Получить сравнение экспериментов в виде DataFrame"""
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/api/v1/metrics/compare",
                params={
                    "project_id": project_id,
                    "experiment_ids": [str(e) for e in experiment_ids],
                },
                headers=self.headers,
            )
            response.raise_for_status()
        
        data = response.json()
        
        # Преобразовать в DataFrame для удобного анализа
        rows = []
        for exp_id, metrics in data['experiments'].items():
            for metric_name, values in metrics.items():
                rows.append({
                    'experiment': exp_id,
                    'metric': metric_name,
                    'last': values['last'],
                })
        
        df = pd.DataFrame(rows)
        df_pivot = df.pivot(index='metric', columns='experiment', values='last')
        
        return df_pivot
    
    async def analyze_hypothesis(
        self,
        project_id: UUID,
        hypothesis_id: UUID,
    ) -> Dict:
        """Получить детальный анализ гипотезы"""
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/api/v1/hypotheses/{project_id}/{hypothesis_id}/evidence",
                headers=self.headers,
            )
            response.raise_for_status()
        
        data = response.json()
        
        # Вычислить статистику
        evidence_units = data['evidence_units']
        df = pd.DataFrame(evidence_units)
        
        return {
            'status': data['status'],
            'total_evidence': data['total_evidence'],
            'unit_count': len(evidence_units),
            'avg_confidence': df['confidence_score'].mean(),
            'evidence_by_metric': df.groupby('metric_name')['delta'].mean().to_dict(),
        }

# Использование:
async def main():
    client = ResearchAnalysisClient(
        base_url="http://localhost:8000",
        token="your-token",
    )
    
    # Сравнить эксперименты
    df = await client.get_experiment_comparison(
        project_id=UUID("550e8400-e29b-41d4-a716-446655440002"),
        experiment_ids=[
            UUID("550e8400-e29b-41d4-a716-446655440111"),
            UUID("550e8400-e29b-41d4-a716-446655440112"),
            UUID("550e8400-e29b-41d4-a716-446655440113"),
        ],
    )
    
    print("Comparison Results:")
    print(df)
    print("\nImprovement over baseline (exp-111):")
    baseline = df['550e8400-e29b-41d4-a716-446655440111']
    for col in df.columns[1:]:
        improvement = (df[col] - baseline) / baseline * 100
        print(f"\n{col}:")
        print(improvement)
    
    # Анализ гипотезы
    hyp_analysis = await client.analyze_hypothesis(
        project_id=UUID("550e8400-e29b-41d4-a716-446655440002"),
        hypothesis_id=UUID("550e8400-e29b-41d4-a716-446655440321"),
    )
    
    print(f"\nHypothesis Status: {hyp_analysis['status']}")
    print(f"Total Evidence: {hyp_analysis['total_evidence']:.3f}")
    print(f"Units: {hyp_analysis['unit_count']}")
    print(f"Avg Confidence: {hyp_analysis['avg_confidence']:.2f}")

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
```

### Plotly визуализация

```python
# examples/visualize_metrics.py

import plotly.graph_objects as go
import plotly.express as px
from app.core.dependencies import get_clickhouse_client
from uuid import UUID

def plot_metric_timeseries(
    team_id: str,
    project_id: str,
    experiment_id: str,
    metric_name: str,
):
    """Визуализировать временной ряд метрики"""
    
    ch = get_clickhouse_client()
    
    points = ch.get_metric_timeseries(
        team_id=team_id,
        project_id=project_id,
        experiment_id=experiment_id,
        metric_name=metric_name,
    )
    
    df = pd.DataFrame([
        {
            'timestamp': p['timestamp'],
            'step': p['step'],
            'value': p['value'],
        }
        for p in points
    ])
    
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=df['step'],
        y=df['value'],
        mode='lines+markers',
        name=metric_name,
        line=dict(width=2),
    ))
    
    fig.update_layout(
        title=f"{metric_name} для {experiment_id}",
        xaxis_title="Step",
        yaxis_title="Value",
        hovermode='x unified',
        template='plotly_white',
    )
    
    return fig

def plot_experiment_comparison(
    team_id: str,
    project_id: str,
    experiment_ids: List[str],
    metric_names: List[str],
):
    """Сравнить метрики между экспериментами (bar chart)"""
    
    ch = get_clickhouse_client()
    
    comparison = ch.compare_experiments(
        team_id=team_id,
        project_id=project_id,
        experiment_ids=experiment_ids,
        metric_names=metric_names,
    )
    
    # Преобразовать для plotly
    data = []
    for exp_id in experiment_ids:
        for metric_name in metric_names:
            if metric_name in comparison[exp_id]:
                value = comparison[exp_id][metric_name]['last']
                data.append({
                    'experiment': exp_id[:8],  # truncate for display
                    'metric': metric_name,
                    'value': value,
                })
    
    df = pd.DataFrame(data)
    
    fig = px.bar(
        df,
        x='metric',
        y='value',
        color='experiment',
        barmode='group',
        title="Metric Comparison",
        template='plotly_white',
    )
    
    return fig

# Использование:
fig1 = plot_metric_timeseries(
    team_id="team-123",
    project_id="proj-456",
    experiment_id="exp-789",
    metric_name="loss",
)
fig1.show()

fig2 = plot_experiment_comparison(
    team_id="team-123",
    project_id="proj-456",
    experiment_ids=["exp-111", "exp-222", "exp-333"],
    metric_names=["loss", "accuracy"],
)
fig2.show()
```

---

## Часть 4: Оптимизационные hints

### Query Planning

Перед выполнением сложного запроса используйте `EXPLAIN`:

```sql
EXPLAIN
SELECT
    experiment_id,
    metric_name,
    COUNT(*) as points
FROM metrics
WHERE team_id = '...'
  AND project_id = '...'
  AND metric_name = 'loss'
GROUP BY experiment_id, metric_name;
```

ClickHouse покажет план выполнения и оценку.

### Использовать FINAL для ReplacingMergeTree

```sql
-- Если нужны актуальные данные (после OPTIMIZE)
SELECT *
FROM metrics
FINAL
WHERE team_id = '...'
ORDER BY timestamp DESC
LIMIT 10;
```

### Batch размеры

- Оптимальный batch = 10-100K строк за раз
- Слишком маленькие (~10) → overhead
- Слишком большие (>1M) → OOM на сервере

---

## Резюме: готовые SQL шаблоны

- ✅ Получить временной ряд метрики
- ✅ Сравнить эксперименты
- ✅ Вычислить Evidence Units
- ✅ Анализировать гипотезы
- ✅ Найти лучший эксперимент
- ✅ Вычислить стабильность метрик

Всё готово для полноценной платформы! 🎉
