from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import Integer, String, Float, text


class Base(DeclarativeBase):
    pass


class MetricBase(Base):
    __abstract__ = True

    id: Mapped[int] = mapped_column(primary_key=True)
    ts: Mapped[int]
    value: Mapped[float]


def metric_model(table_name: str):
    return type(
        f"Metric_{table_name}",
        (MetricBase,),
        {
            "__tablename__": table_name,
            "__table_args__": {"extend_existing": True},
        },
    )
