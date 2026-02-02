from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import Integer, String, Float, text

class ProjectsTable:
    def create_table(self, project_id: str):
        table_name = safe_scalars_table_name(project_id)
        ddl = f"""
        CREATE TABLE IF NOT EXISTS {table_name} (
            timestamp   TIMESTAMP NOT NULL,
            experiment_id SYMBOL,
            scalar_name   SYMBOL,
            value         DOUBLE NOT NULL,
            step          INT,
            tags          STRING
        ) TIMESTAMP(timestamp) PARTITION BY DAY;
        """
        
    def safe_scalars_table_name(project_id: str) -> str:
    """
    Валидируем имя таблицы: только латиница, цифры, нижнее подчеркивание.
    Должно начинаться с буквы или нижнего подчеркивания.
    """
    name = f"scalars_{project_id}".lower()
    if not re.match(r"^[a-z_][a-z0-9_]{1,63}$", name):
        raise HTTPException(status_code=400, detail="Invalid project_id")
    return name