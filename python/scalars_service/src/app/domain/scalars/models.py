from sqlalchemy.orm import declarative_base
from sqlalchemy import Column, Integer, String, TIMESTAMP

Base = declarative_base()


class BaseLog(Base):
    __abstract__ = True

    timestamp = Column(TIMESTAMP, primary_key=True)
    experiment_id = Column(String)
    scalar_name = Column(String)
    value = Column(Integer)
    step = Column(Integer)
    tags = Column(String)


def scalars_model(table_name):
    return type(table_name, (BaseLog,), {"__tablename__": table_name})
