# ML Experiments Scalars Logging Service - FastAPI Integration
## Technical Specification

---

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Abstract Interface](#abstract-interface)
4. [QuestDB Implementation](#questdb-implementation)
5. [FastAPI Controller](#fastapi-controller)
6. [Data Models](#data-models)
7. [API Endpoints](#api-endpoints)
8. [Usage Examples](#usage-examples)

---

## Overview

### Purpose

Implement a production-ready scalars logging service for ML experiments that integrates with FastAPI. The service should:

- Log training scalars (loss, accuracy, custom scalars) during model training
- Support reservoir sampling for efficient visualization (last point always visible)
- Query scalars by experiment, scalar name, or project
- Export full scalars data for analysis
- Maintain high ingestion throughput (1M+ rows/sec)
- Support both batch and individual scalar logging

### Key Features

- **High Performance**: Sub-millisecond logging via ILP protocol
- **Flexible Querying**: Filter by project, experiment, scalar, time range
- **Reservoir Sampling**: Downsample large datasets while preserving trends
- **GDPR Compliant**: Easy deletion of experiments/old data
- **Abstraction Layer**: Easy to swap database implementation

### Technology Stack

- **Database**: QuestDB (per-project table design)
- **API Framework**: FastAPI
- **Data Format**: Pydantic models
- **Time Series**: TimestampNanos for precision

---

## Architecture

### High-Level Design

```
┌─────────────────────────────────────────┐
│        FastAPI Application              │
│  ┌───────────────────────────────────┐  │
│  │   ScalarsController               │  │
│  │   - POST /log                     │  │
│  │   - GET /query                    │  │
│  │   - GET /compare                  │  │
│  │   - GET /top                      │  │
│  │   - GET /export                   │  │
│  └───────────────────────────────────┘  │
└──────────────┬──────────────────────────┘
               │
               ↓
┌─────────────────────────────────────────┐
│   ScalarsService (Abstract)             │
│   - log_scalar()                        │
│   - log_scalars_batch()                 │
│   - query_scalars()                     │
│   - get_top_experiments()               │
│   - get_convergence()                   │
│   - export_project()                    │
│   - cleanup_old_data()                  │
└──────────────┬──────────────────────────┘
               │
      ┌────────┴────────┐
      ↓                 ↓
┌──────────────┐  ┌──────────────┐
│QuestDBScalars│  │MockScalars   │
│Service       │  │Service       │
│(Production)  │  │(Testing)     │
└──────────────┘  └──────────────┘
      │
      ↓
┌─────────────────────────────────────────┐
│        QuestDB Instance                 │
│  {project_id}_scalars table             │
│  - timestamp, experiment_id             │
│  - scalar_name, value, step             │
│  - tags, PARTITION BY DAY               │
└─────────────────────────────────────────┘
```

### Data Schema Changes

```sql
CREATE TABLE {project_id}_scalars (
    timestamp    TIMESTAMP NOT NULL,
    experiment_id SYMBOL NOT NULL,
    scalar_name   SYMBOL NOT NULL,
    value         DOUBLE NOT NULL,
    step          INT,                    -- Changed from epoch
    tags          STRING
) TIMESTAMP(timestamp) 
PARTITION BY DAY
```

**Changes from previous spec:**
- Removed `run_id` (experiments are unique per project)
- Renamed `epoch` → `step` (more general for any training paradigm)

---

## Abstract Interface

### ScalarsService (Abstract Base Class)

```python
from abc import ABC, abstractmethod
from typing import Dict, List, Optional
from datetime import datetime
import pandas as pd
from pydantic import BaseModel


class ScalarPoint(BaseModel):
    """Single scalar data point"""
    timestamp: datetime
    scalar_name: str
    value: float
    step: Optional[int] = None
    tags: Optional[Dict] = None


class ScalarsQuery(BaseModel):
    """Query parameters for scalars"""
    experiment_id: str
    scalar_name: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    max_points: Optional[int] = None  # For reservoir sampling


class ScalarsExportRequest(BaseModel):
    """Request parameters for scalars export"""
    experiment_ids: Optional[List[str]] = None
    scalar_names: Optional[List[str]] = None
    include_all_experiments: bool = False


class ComparisonQuery(BaseModel):
    """Query for comparing experiments"""
    experiment_ids: List[str]
    scalar_name: str
    max_points: Optional[int] = 500  # Default reservoir sampling limit


class ConvergenceStats(BaseModel):
    """Convergence analysis results"""
    initial_value: float
    final_value: float
    total_improvement: float
    rate_per_step: float
    is_monotonic: bool
    total_logs: int


class ExperimentStats(BaseModel):
    """Basic experiment statistics"""
    experiment_id: str
    total_logs: int
    scalar_count: int
    first_timestamp: datetime
    last_timestamp: datetime
    step_range: Dict[str, int]


class ScalarsService(ABC):
    """
    Abstract interface for scalars logging and querying.
    
    Implementations should:
    - Support high-throughput ingestion (1M+ rows/sec)
    - Implement reservoir sampling for visualization
    - Handle concurrent reads/writes
    - Support efficient time-range queries
    """
    
    @abstractmethod
    async def log_scalar(
        self,
        project_id: str,
        experiment_id: str,
        scalar_name: str,
        value: float,
        step: Optional[int] = None,
        tags: Optional[Dict] = None,
        timestamp: Optional[datetime] = None
    ) -> None:
        """
        Log a single scalar point.
        
        Args:
            project_id: Project identifier
            experiment_id: Experiment identifier
            scalar_name: Name of the scalar (loss, accuracy, etc.)
            value: Numerical scalar value
            step: Training step/iteration (optional)
            tags: Additional JSON tags (hyperparameters, config)
            timestamp: Logging timestamp (current time if not provided)
        """
        pass
    
    @abstractmethod
    async def log_scalars_batch(
        self,
        project_id: str,
        experiment_id: str,
        scalars: Dict[str, float],
        step: Optional[int] = None,
        tags: Optional[Dict] = None,
        timestamp: Optional[datetime] = None
    ) -> None:
        """
        Log multiple scalars at once (more efficient).
        
        Args:
            project_id: Project identifier
            experiment_id: Experiment identifier
            scalars: Dict of {scalar_name: value}
            step: Training step
            tags: Additional tags
            timestamp: Logging timestamp
        """
        pass
    
    @abstractmethod
    async def query_scalars(
        self,
        project_id: str,
        query: ScalarsQuery
    ) -> pd.DataFrame:
        """
        Query scalars with optional reservoir sampling.
        
        Returns DataFrame with columns:
        - timestamp
        - scalar_name
        - value
        - step
        - tags
        
        Args:
            project_id: Project identifier
            query: Query parameters including experiment_id, scalar_name, time range
        """
        pass
    
    @abstractmethod
    async def get_latest_scalars(
        self,
        project_id: str,
        experiment_ids: Optional[List[str]] = None
    ) -> pd.DataFrame:
        """
        Get the latest value for each scalar in each experiment.
        
        Useful for dashboards showing current status.
        
        Returns DataFrame with columns:
        - experiment_id
        - scalar_name
        - value
        - step
        - timestamp
        """
        pass
    
    @abstractmethod
    async def compare_experiments(
        self,
        project_id: str,
        query: ComparisonQuery
    ) -> pd.DataFrame:
        """
        Compare a single scalar across multiple experiments.
        
        Returns pivoted DataFrame:
        - index: timestamp
        - columns: experiment_id
        - values: scalar value
        
        Implements reservoir sampling to keep manageable data size.
        Last point always included to show latest values.
        """
        pass
    
    @abstractmethod
    async def get_top_experiments(
        self,
        project_id: str,
        scalar_name: str,
        top_k: int = 5,
        maximize: bool = True
    ) -> pd.DataFrame:
        """
        Get top-K experiments ranked by scalar.
        
        Returns DataFrame with:
        - experiment_id
        - max_value / min_value / avg_value
        - total_logs
        - last_updated
        
        Args:
            project_id: Project identifier
            scalar_name: Scalar to rank by
            top_k: Number of top experiments to return
            maximize: True if higher is better (accuracy), False if lower (loss)
        """
        pass
    
    @abstractmethod
    async def get_convergence_analysis(
        self,
        project_id: str,
        experiment_id: str,
        scalar_name: str
    ) -> ConvergenceStats:
        """
        Analyze scalar convergence (speed of improvement).
        
        Useful for detecting training issues or evaluating optimization.
        """
        pass
    
    @abstractmethod
    async def get_experiment_stats(
        self,
        project_id: str,
        experiment_id: str
    ) -> ExperimentStats:
        """Get basic statistics about an experiment."""
        pass
    
    @abstractmethod
    async def export_scalars(
        self,
        project_id: str,
        request: ScalarsExportRequest
    ) -> pd.DataFrame:
        """
        Export scalars data for analysis/sharing.
        
        Returns complete DataFrame with all requested scalars.
        Can handle large exports efficiently.
        """
        pass
    
    @abstractmethod
    async def delete_experiment(
        self,
        project_id: str,
        experiment_id: str
    ) -> None:
        """
        Delete all scalars for an experiment (GDPR compliance).
        """
        pass
    
    @abstractmethod
    async def cleanup_old_data(
        self,
        project_id: str,
        days_to_keep: int = 90
    ) -> int:
        """
        Delete scalars older than specified days.
        
        Returns: number of rows deleted
        """
        pass
    
    @abstractmethod
    async def initialize_project(
        self,
        project_id: str
    ) -> None:
        """
        Initialize storage for a new project.
        
        Called once per project before first logging.
        """
        pass


# Helper function for reservoir sampling
def reservoir_sample(
    data: List[float],
    timestamps: List[datetime],
    k: int
) -> tuple[List[float], List[datetime]]:
    """
    Reservoir Algorithm R for sampling with guaranteed last point.
    
    Ensures the last point is always included (important for visualization).
    
    Args:
        data: List of values to sample
        timestamps: Corresponding timestamps
        k: Target sample size
    
    Returns:
        Tuple of (sampled_values, sampled_timestamps)
    """
    import random
    
    if len(data) <= k:
        return data, timestamps
    
    # Always include first and last
    sampled_indices = {0, len(data) - 1}
    
    # Reservoir sample remaining points
    for i in range(1, len(data) - 1):
        if len(sampled_indices) < k:
            sampled_indices.add(i)
        else:
            j = random.randint(0, i)
            if j < k - 2:  # Reserve 2 slots for first/last
                sampled_indices.discard(min(sampled_indices))
                sampled_indices.add(i)
    
    sorted_indices = sorted(sampled_indices)
    sampled_values = [data[i] for i in sorted_indices]
    sampled_timestamps = [timestamps[i] for i in sorted_indices]
    
    return sampled_values, sampled_timestamps
```

---

## QuestDB Implementation

### QuestDBScalarsService

```python
import json
import psycopg2
import pandas as pd
from datetime import datetime
from typing import Dict, List, Optional
from questdb.ingress import Sender, TimestampNanos
import asyncio
from concurrent.futures import ThreadPoolExecutor


class QuestDBScalarsService(ScalarsService):
    """
    QuestDB implementation of ScalarsService.
    
    Features:
    - High-throughput ILP ingestion (1M+ rows/sec)
    - Efficient SQL queries for analytics
    - Automatic table creation per project
    - Reservoir sampling for visualization
    """
    
    def __init__(
        self,
        host: str = 'localhost',
        port_ilp: int = 9009,
        port_pg: int = 8812,
        user: str = 'admin',
        password: str = 'quest',
        batch_size: int = 100,
        executor: Optional[ThreadPoolExecutor] = None
    ):
        """
        Initialize QuestDB scalars service.
        
        Args:
            host: QuestDB host
            port_ilp: ILP (InfluxDB Line Protocol) port
            port_pg: PostgreSQL wire protocol port
            user: Database user
            password: Database password
            batch_size: Rows to accumulate before flush
            executor: ThreadPoolExecutor for async operations
        """
        self.host = host
        self.port_ilp = port_ilp
        self.port_pg = port_pg
        self.user = user
        self.password = password
        self.batch_size = batch_size
        self.executor = executor or ThreadPoolExecutor(max_workers=10)
        
        # Per-project senders for batching
        self._senders: Dict[str, Sender] = {}
        self._batch_counts: Dict[str, int] = {}
    
    def _get_table_name(self, project_id: str) -> str:
        """Get table name for project."""
        return f"{project_id}_scalars"
    
    def _get_sender(self, project_id: str) -> Sender:
        """Get or create ILP sender for project."""
        if project_id not in self._senders:
            self._senders[project_id] = Sender('tcp', self.host, self.port_ilp)
            self._batch_counts[project_id] = 0
        return self._senders[project_id]
    
    def _get_connection(self) -> psycopg2.extensions.connection:
        """Create PostgreSQL connection."""
        return psycopg2.connect(
            host=self.host,
            port=self.port_pg,
            user=self.user,
            password=self.password,
            database='qdb'
        )
    
    async def initialize_project(self, project_id: str) -> None:
        """Create table for project if not exists."""
        table_name = self._get_table_name(project_id)
        
        def _create_table():
            conn = self._get_connection()
            try:
                with conn.cursor() as cur:
                    cur.execute(f"""
                        CREATE TABLE IF NOT EXISTS {table_name} (
                            timestamp TIMESTAMP NOT NULL,
                            experiment_id SYMBOL NOT NULL,
                            scalar_name SYMBOL NOT NULL,
                            value DOUBLE NOT NULL,
                            step INT,
                            tags STRING
                        ) TIMESTAMP(timestamp) 
                        PARTITION BY DAY
                    """)
                conn.commit()
            finally:
                conn.close()
        
        await asyncio.get_event_loop().run_in_executor(
            self.executor, _create_table
        )
    
    async def log_scalar(
        self,
        project_id: str,
        experiment_id: str,
        scalar_name: str,
        value: float,
        step: Optional[int] = None,
        tags: Optional[Dict] = None,
        timestamp: Optional[datetime] = None
    ) -> None:
        """Log single scalar via ILP."""
        if timestamp is None:
            timestamp = TimestampNanos.now()
        
        tags_str = json.dumps(tags) if tags else '{}'
        
        sender = self._get_sender(project_id)
        sender.row(
            self._get_table_name(project_id),
            symbols={
                'experiment_id': experiment_id,
                'scalar_name': scalar_name
            },
            columns={
                'value': value,
                'step': step or 0,
                'tags': tags_str
            },
            at=timestamp
        )
        
        self._batch_counts[project_id] += 1
        if self._batch_counts[project_id] >= self.batch_size:
            await self.flush(project_id)
    
    async def log_scalars_batch(
        self,
        project_id: str,
        experiment_id: str,
        scalars: Dict[str, float],
        step: Optional[int] = None,
        tags: Optional[Dict] = None,
        timestamp: Optional[datetime] = None
    ) -> None:
        """Log multiple scalars efficiently."""
        for scalar_name, value in scalars.items():
            await self.log_scalar(
                project_id=project_id,
                experiment_id=experiment_id,
                scalar_name=scalar_name,
                value=value,
                step=step,
                tags=tags,
                timestamp=timestamp
            )
    
    async def flush(self, project_id: str) -> None:
        """Flush batched scalars to database."""
        if project_id in self._senders and self._batch_counts[project_id] > 0:
            sender = self._senders[project_id]
            
            def _flush():
                sender.flush()
            
            await asyncio.get_event_loop().run_in_executor(
                self.executor, _flush
            )
            self._batch_counts[project_id] = 0
    
    async def query_scalars(
        self,
        project_id: str,
        query: ScalarsQuery
    ) -> pd.DataFrame:
        """Query scalars with optional reservoir sampling."""
        table_name = self._get_table_name(project_id)
        
        sql = f"""
            SELECT 
                timestamp,
                scalar_name,
                value,
                step,
                tags
            FROM {table_name}
            WHERE experiment_id = %s
        """
        params = [query.experiment_id]
        
        if query.scalar_name:
            sql += " AND scalar_name = %s"
            params.append(query.scalar_name)
        
        if query.start_time:
            sql += " AND timestamp >= %s"
            params.append(query.start_time)
        
        if query.end_time:
            sql += " AND timestamp <= %s"
            params.append(query.end_time)
        
        sql += " ORDER BY timestamp"
        
        def _query():
            conn = self._get_connection()
            try:
                df = pd.read_sql(sql, conn, params=params)
                
                # Apply reservoir sampling if requested
                if query.max_points and len(df) > query.max_points:
                    df = self._apply_reservoir_sampling(
                        df, query.max_points
                    )
                
                return df
            finally:
                conn.close()
        
        return await asyncio.get_event_loop().run_in_executor(
            self.executor, _query
        )
    
    async def get_latest_scalars(
        self,
        project_id: str,
        experiment_ids: Optional[List[str]] = None
    ) -> pd.DataFrame:
        """Get latest scalar values per experiment."""
        table_name = self._get_table_name(project_id)
        
        sql = f"""
            SELECT 
                experiment_id,
                scalar_name,
                value,
                step,
                timestamp
            FROM (
                SELECT 
                    experiment_id,
                    scalar_name,
                    value,
                    step,
                    timestamp,
                    ROW_NUMBER() OVER (
                        PARTITION BY experiment_id, scalar_name 
                        ORDER BY timestamp DESC
                    ) as rn
                FROM {table_name}
        """
        params = []
        
        if experiment_ids:
            placeholders = ','.join(['%s'] * len(experiment_ids))
            sql += f" WHERE experiment_id IN ({placeholders})"
            params.extend(experiment_ids)
        
        sql += """
            )
            WHERE rn = 1
            ORDER BY experiment_id, scalar_name
        """
        
        def _query():
            conn = self._get_connection()
            try:
                return pd.read_sql(sql, conn, params=params)
            finally:
                conn.close()
        
        return await asyncio.get_event_loop().run_in_executor(
            self.executor, _query
        )
    
    async def compare_experiments(
        self,
        project_id: str,
        query: ComparisonQuery
    ) -> pd.DataFrame:
        """Compare experiments with reservoir sampling."""
        table_name = self._get_table_name(project_id)
        
        sql = f"""
            SELECT 
                timestamp,
                experiment_id,
                value
            FROM {table_name}
            WHERE scalar_name = %s
              AND experiment_id IN ({','.join(['%s'] * len(query.experiment_ids))})
            ORDER BY experiment_id, timestamp
        """
        
        params = [query.scalar_name] + query.experiment_ids
        
        def _query():
            conn = self._get_connection()
            try:
                df = pd.read_sql(sql, conn, params=params)
                
                # Apply reservoir sampling per experiment
                if query.max_points:
                    sampled_dfs = []
                    for exp_id in query.experiment_ids:
                        exp_df = df[df['experiment_id'] == exp_id].copy()
                        if len(exp_df) > query.max_points:
                            exp_df = self._apply_reservoir_sampling(
                                exp_df, query.max_points
                            )
                        sampled_dfs.append(exp_df)
                    df = pd.concat(sampled_dfs, ignore_index=True)
                
                # Pivot for comparison
                return df.pivot(
                    index='timestamp',
                    columns='experiment_id',
                    values='value'
                )
            finally:
                conn.close()
        
        return await asyncio.get_event_loop().run_in_executor(
            self.executor, _query
        )
    
    async def get_top_experiments(
        self,
        project_id: str,
        scalar_name: str,
        top_k: int = 5,
        maximize: bool = True
    ) -> pd.DataFrame:
        """Get top-K experiments ranked by scalar."""
        table_name = self._get_table_name(project_id)
        
        order_by = "DESC" if maximize else "ASC"
        
        sql = f"""
            SELECT 
                experiment_id,
                MAX(value) as max_value,
                MIN(value) as min_value,
                AVG(value) as avg_value,
                COUNT(*) as total_logs,
                MAX(timestamp) as last_updated
            FROM {table_name}
            WHERE scalar_name = %s
            GROUP BY experiment_id
            ORDER BY max_value {order_by}
            LIMIT %s
        """
        
        params = [scalar_name, top_k]
        
        def _query():
            conn = self._get_connection()
            try:
                return pd.read_sql(sql, conn, params=params)
            finally:
                conn.close()
        
        return await asyncio.get_event_loop().run_in_executor(
            self.executor, _query
        )
    
    async def get_convergence_analysis(
        self,
        project_id: str,
        experiment_id: str,
        scalar_name: str
    ) -> ConvergenceStats:
        """Analyze scalar convergence."""
        df = await self.query_scalars(
            project_id,
            ScalarsQuery(
                experiment_id=experiment_id,
                scalar_name=scalar_name
            )
        )
        
        if len(df) < 2:
            return ConvergenceStats(
                initial_value=0,
                final_value=0,
                total_improvement=0,
                rate_per_step=0,
                is_monotonic=False,
                total_logs=0
            )
        
        df = df.sort_values('timestamp')
        values = df['value'].values
        
        improvement = values[-1] - values[0]
        steps = len(df)
        rate_per_step = improvement / steps if steps > 0 else 0
        
        is_monotonic = (
            all(values[i] <= values[i+1] for i in range(len(values)-1)) or
            all(values[i] >= values[i+1] for i in range(len(values)-1))
        )
        
        return ConvergenceStats(
            initial_value=float(values[0]),
            final_value=float(values[-1]),
            total_improvement=float(improvement),
            rate_per_step=float(rate_per_step),
            is_monotonic=is_monotonic,
            total_logs=len(values)
        )
    
    async def get_experiment_stats(
        self,
        project_id: str,
        experiment_id: str
    ) -> ExperimentStats:
        """Get experiment statistics."""
        table_name = self._get_table_name(project_id)
        
        sql = f"""
            SELECT 
                COUNT(*) as total_logs,
                COUNT(DISTINCT scalar_name) as scalar_count,
                MIN(timestamp) as first_timestamp,
                MAX(timestamp) as last_timestamp,
                MIN(step) as min_step,
                MAX(step) as max_step
            FROM {table_name}
            WHERE experiment_id = %s
        """
        
        def _query():
            conn = self._get_connection()
            try:
                result = pd.read_sql(sql, conn, params=[experiment_id])
                row = result.iloc[0]
                
                return ExperimentStats(
                    experiment_id=experiment_id,
                    total_logs=int(row['total_logs']),
                    scalar_count=int(row['scalar_count']),
                    first_timestamp=row['first_timestamp'],
                    last_timestamp=row['last_timestamp'],
                    step_range={
                        'min': int(row['min_step']) if row['min_step'] else 0,
                        'max': int(row['max_step']) if row['max_step'] else 0
                    }
                )
            finally:
                conn.close()
        
        return await asyncio.get_event_loop().run_in_executor(
            self.executor, _query
        )
    
    async def export_scalars(
        self,
        project_id: str,
        request: ScalarsExportRequest
    ) -> pd.DataFrame:
        """Export scalars data."""
        table_name = self._get_table_name(project_id)
        
        sql = f"SELECT * FROM {table_name}"
        conditions = []
        params = []
        
        if not request.include_all_experiments and request.experiment_ids:
            placeholders = ','.join(['%s'] * len(request.experiment_ids))
            conditions.append(f"experiment_id IN ({placeholders})")
            params.extend(request.experiment_ids)
        
        if request.scalar_names:
            placeholders = ','.join(['%s'] * len(request.scalar_names))
            conditions.append(f"scalar_name IN ({placeholders})")
            params.extend(request.scalar_names)
        
        if conditions:
            sql += " WHERE " + " AND ".join(conditions)
        
        sql += " ORDER BY timestamp"
        
        def _query():
            conn = self._get_connection()
            try:
                return pd.read_sql(sql, conn, params=params)
            finally:
                conn.close()
        
        return await asyncio.get_event_loop().run_in_executor(
            self.executor, _query
        )
    
    async def delete_experiment(
        self,
        project_id: str,
        experiment_id: str
    ) -> None:
        """Delete experiment (GDPR)."""
        table_name = self._get_table_name(project_id)
        
        def _delete():
            conn = self._get_connection()
            try:
                with conn.cursor() as cur:
                    cur.execute(
                        f"DELETE FROM {table_name} WHERE experiment_id = %s",
                        [experiment_id]
                    )
                conn.commit()
            finally:
                conn.close()
        
        await asyncio.get_event_loop().run_in_executor(
            self.executor, _delete
        )
    
    async def cleanup_old_data(
        self,
        project_id: str,
        days_to_keep: int = 90
    ) -> int:
        """Delete old scalars."""
        table_name = self._get_table_name(project_id)
        
        def _cleanup():
            conn = self._get_connection()
            try:
                with conn.cursor() as cur:
                    cur.execute(
                        f"""
                        DELETE FROM {table_name}
                        WHERE timestamp < NOW() - INTERVAL '{days_to_keep}' DAY
                        """
                    )
                    rows_deleted = cur.rowcount
                conn.commit()
                return rows_deleted
            finally:
                conn.close()
        
        return await asyncio.get_event_loop().run_in_executor(
            self.executor, _cleanup
        )
    
    def _apply_reservoir_sampling(
        self,
        df: pd.DataFrame,
        max_points: int
    ) -> pd.DataFrame:
        """Apply reservoir sampling with last point guarantee."""
        if len(df) <= max_points:
            return df
        
        df = df.reset_index(drop=True)
        values = df['value'].values.tolist()
        timestamps = df['timestamp'].values.tolist()
        
        sampled_values, sampled_timestamps = reservoir_sample(
            values, timestamps, max_points
        )
        
        # Create new dataframe with sampled points
        sampled_indices = [
            df[df['timestamp'] == ts].index[0]
            for ts in sampled_timestamps
        ]
        
        return df.loc[sorted(sampled_indices)].reset_index(drop=True)
    
    async def close(self):
        """Clean up resources."""
        for sender in self._senders.values():
            sender.__exit__(None, None, None)
        self._senders.clear()
```

---

## FastAPI Controller

### ScalarsController

```python
from fastapi import APIRouter, HTTPException, Query, BackgroundTasks
from typing import List, Optional
from datetime import datetime
import io
import csv

router = APIRouter(prefix="/api/v1/scalars", tags=["scalars"])


class ScalarsController:
    """
    FastAPI controller for scalars operations.
    
    Handles HTTP requests for logging and querying scalars.
    """
    
    def __init__(self, service: ScalarsService):
        """
        Initialize controller with scalars service.
        
        Args:
            service: ScalarsService implementation (abstract interface)
        """
        self.service = service
        self._setup_routes()
    
    def _setup_routes(self):
        """Register all route handlers."""
        
        @router.post("/log/{project_id}/{experiment_id}")
        async def log_scalar_endpoint(
            project_id: str,
            experiment_id: str,
            scalar_name: str = Query(..., description="Name of scalar"),
            value: float = Query(..., description="Scalar value"),
            step: Optional[int] = Query(None, description="Training step"),
            tags: Optional[str] = Query(None, description="JSON tags")
        ):
            """Log a single scalar point."""
            try:
                tags_dict = json.loads(tags) if tags else None
                await self.service.log_scalar(
                    project_id=project_id,
                    experiment_id=experiment_id,
                    scalar_name=scalar_name,
                    value=value,
                    step=step,
                    tags=tags_dict
                )
                return {"status": "logged"}
            except Exception as e:
                raise HTTPException(status_code=400, detail=str(e))
        
        @router.post("/log-batch/{project_id}/{experiment_id}")
        async def log_scalars_batch_endpoint(
            project_id: str,
            experiment_id: str,
            scalars_dict: Dict[str, float],
            step: Optional[int] = Query(None),
            tags: Optional[str] = Query(None)
        ):
            """Log multiple scalars at once."""
            try:
                tags_dict = json.loads(tags) if tags else None
                await self.service.log_scalars_batch(
                    project_id=project_id,
                    experiment_id=experiment_id,
                    scalars=scalars_dict,
                    step=step,
                    tags=tags_dict
                )
                return {"status": "batch_logged", "count": len(scalars_dict)}
            except Exception as e:
                raise HTTPException(status_code=400, detail=str(e))
        
        @router.get("/query/{project_id}")
        async def query_scalars_endpoint(
            project_id: str,
            experiment_id: str = Query(...),
            scalar_name: Optional[str] = Query(None),
            max_points: Optional[int] = Query(500, description="For reservoir sampling"),
            start_time: Optional[datetime] = Query(None),
            end_time: Optional[datetime] = Query(None)
        ):
            """Query scalars with optional sampling."""
            try:
                query = ScalarsQuery(
                    experiment_id=experiment_id,
                    scalar_name=scalar_name,
                    max_points=max_points,
                    start_time=start_time,
                    end_time=end_time
                )
                df = await self.service.query_scalars(project_id, query)
                
                return {
                    "count": len(df),
                    "scalars": df.to_dict(orient='records')
                }
            except Exception as e:
                raise HTTPException(status_code=400, detail=str(e))
        
        @router.get("/latest/{project_id}")
        async def get_latest_endpoint(
            project_id: str,
            experiment_ids: Optional[List[str]] = Query(None)
        ):
            """Get latest scalar values."""
            try:
                df = await self.service.get_latest_scalars(
                    project_id, experiment_ids
                )
                return df.to_dict(orient='records')
            except Exception as e:
                raise HTTPException(status_code=400, detail=str(e))
        
        @router.post("/compare/{project_id}")
        async def compare_experiments_endpoint(
            project_id: str,
            query: ComparisonQuery
        ):
            """Compare experiments on a scalar."""
            try:
                df = await self.service.compare_experiments(project_id, query)
                
                return {
                    "scalar_name": query.scalar_name,
                    "experiments": df.columns.tolist(),
                    "data": df.to_dict(orient='index')
                }
            except Exception as e:
                raise HTTPException(status_code=400, detail=str(e))
        
        @router.get("/top/{project_id}")
        async def get_top_experiments_endpoint(
            project_id: str,
            scalar_name: str = Query(...),
            top_k: int = Query(5),
            maximize: bool = Query(True)
        ):
            """Get top-K experiments."""
            try:
                df = await self.service.get_top_experiments(
                    project_id, scalar_name, top_k, maximize
                )
                return df.to_dict(orient='records')
            except Exception as e:
                raise HTTPException(status_code=400, detail=str(e))
        
        @router.get("/convergence/{project_id}/{experiment_id}")
        async def get_convergence_endpoint(
            project_id: str,
            experiment_id: str,
            scalar_name: str = Query(...)
        ):
            """Get convergence analysis."""
            try:
                stats = await self.service.get_convergence_analysis(
                    project_id, experiment_id, scalar_name
                )
                return stats.dict()
            except Exception as e:
                raise HTTPException(status_code=400, detail=str(e))
        
        @router.get("/stats/{project_id}/{experiment_id}")
        async def get_stats_endpoint(
            project_id: str,
            experiment_id: str
        ):
            """Get experiment statistics."""
            try:
                stats = await self.service.get_experiment_stats(
                    project_id, experiment_id
                )
                return stats.dict()
            except Exception as e:
                raise HTTPException(status_code=400, detail=str(e))
        
        @router.post("/export/{project_id}")
        async def export_scalars_endpoint(
            project_id: str,
            request: ScalarsExportRequest,
            background_tasks: BackgroundTasks
        ):
            """Export scalars as CSV."""
            try:
                df = await self.service.export_scalars(project_id, request)
                
                # Create CSV in memory
                output = io.StringIO()
                df.to_csv(output, index=False)
                
                return {
                    "rows": len(df),
                    "csv_content": output.getvalue()
                }
            except Exception as e:
                raise HTTPException(status_code=400, detail=str(e))
        
        @router.delete("/experiment/{project_id}/{experiment_id}")
        async def delete_experiment_endpoint(
            project_id: str,
            experiment_id: str
        ):
            """Delete experiment (GDPR)."""
            try:
                await self.service.delete_experiment(project_id, experiment_id)
                return {"status": "deleted"}
            except Exception as e:
                raise HTTPException(status_code=400, detail=str(e))
        
        @router.post("/cleanup/{project_id}")
        async def cleanup_endpoint(
            project_id: str,
            days_to_keep: int = Query(90)
        ):
            """Clean up old scalars."""
            try:
                rows = await self.service.cleanup_old_data(
                    project_id, days_to_keep
                )
                return {"rows_deleted": rows}
            except Exception as e:
                raise HTTPException(status_code=400, detail=str(e))
        
        @router.post("/init/{project_id}")
        async def init_project_endpoint(project_id: str):
            """Initialize project."""
            try:
                await self.service.initialize_project(project_id)
                return {"status": "initialized"}
            except Exception as e:
                raise HTTPException(status_code=400, detail=str(e))
    
    def get_router(self) -> APIRouter:
        """Get FastAPI router with all endpoints."""
        return router
```

---

## Data Models

### Request/Response Models (Pydantic)

Already defined in Abstract Interface section:
- `ScalarPoint`
- `ScalarsQuery`
- `ScalarsExportRequest`
- `ComparisonQuery`
- `ConvergenceStats`
- `ExperimentStats`

---

## API Endpoints

### Summary Table

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/log/{project_id}/{experiment_id}` | POST | Log single scalar |
| `/log-batch/{project_id}/{experiment_id}` | POST | Log multiple scalars |
| `/query/{project_id}` | GET | Query scalars with sampling |
| `/latest/{project_id}` | GET | Get latest scalar values |
| `/compare/{project_id}` | POST | Compare experiments |
| `/top/{project_id}` | GET | Get top experiments |
| `/convergence/{project_id}/{experiment_id}` | GET | Analyze convergence |
| `/stats/{project_id}/{experiment_id}` | GET | Get experiment stats |
| `/export/{project_id}` | POST | Export scalars as CSV |
| `/experiment/{project_id}/{experiment_id}` | DELETE | Delete experiment |
| `/cleanup/{project_id}` | POST | Delete old scalars |
| `/init/{project_id}` | POST | Initialize project |

---

## Usage Examples

### 1. FastAPI Application Setup

```python
from fastapi import FastAPI
from contextlib import asynccontextmanager

# Create service
scalars_service = QuestDBScalarsService(
    host='localhost',
    port_ilp=9009,
    port_pg=8812
)

# Create controller
scalars_controller = ScalarsController(scalars_service)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    yield
    # Shutdown
    await scalars_service.close()

app = FastAPI(lifespan=lifespan)
app.include_router(scalars_controller.get_router())
```

### 2. Logging During Training

```python
# Client code during model training
import httpx

async with httpx.AsyncClient() as client:
    for epoch in range(num_epochs):
        for batch in train_loader:
            step = epoch * len(train_loader) + batch_idx
            
            loss = train_step(batch)
            
            # Log single scalar
            await client.get(
                "http://localhost:8000/api/v1/scalars/log/detection_v1/exp-001",
                params={
                    "scalar_name": "loss",
                    "value": loss,
                    "step": step
                }
            )
        
        # Log multiple scalars at epoch end
        val_scalars = evaluate(val_loader)
        
        await client.post(
            "http://localhost:8000/api/v1/scalars/log-batch/detection_v1/exp-001",
            params={
                "scalars_dict": val_scalars,
                "step": step,
                "tags": json.dumps({"lr": 0.001, "batch_size": 32})
            }
        )
```

### 3. Querying and Comparing

```python
async with httpx.AsyncClient() as client:
    # Get latest scalars
    response = await client.get(
        "http://localhost:8000/api/v1/scalars/latest/detection_v1",
        params={"experiment_ids": ["exp-001", "exp-002"]}
    )
    latest = response.json()
    
    # Compare experiments
    response = await client.post(
        "http://localhost:8000/api/v1/scalars/compare/detection_v1",
        json={
            "experiment_ids": ["exp-001", "exp-002", "exp-003"],
            "scalar_name": "accuracy",
            "max_points": 500  # Reservoir sampling
        }
    )
    comparison = response.json()
    
    # Get convergence analysis
    response = await client.get(
        "http://localhost:8000/api/v1/scalars/convergence/detection_v1/exp-001",
        params={"scalar_name": "loss"}
    )
    convergence = response.json()
```

---

## Implementation Checklist

- [ ] Create abstract `ScalarsService` base class
- [ ] Implement `QuestDBScalarsService`
- [ ] Create Pydantic data models
- [ ] Implement `ScalarsController` with all endpoints
- [ ] Add error handling and validation
- [ ] Implement async/await patterns
- [ ] Add request/response logging
- [ ] Create unit tests for abstract interface
- [ ] Create integration tests with QuestDB
- [ ] Write API documentation
- [ ] Benchmark ingestion throughput
- [ ] Add monitoring/scalars collection
- [ ] Document deployment procedure

---

## Notes

1. **Abstraction Benefits**:
   - Easy to swap implementations (QuestDB → PostgreSQL)
   - Simple to test with mock service
   - Clear interface contracts

2. **Reservoir Sampling**:
   - Ensures last point is always visible (important for trends)
   - Reduces data transfer for large datasets
   - Applied per experiment in comparisons

3. **Performance**:
   - ILP batching for 1M+ rows/sec
   - Async/await for non-blocking I/O
   - ThreadPoolExecutor for SQL queries
   - Per-project senders to batch efficiently

4. **Schema Change**:
   - `epoch` → `step` (more general)
   - Removed `run_id` (not needed per-experiment design)

