from sqlalchemy import create_engine, Column, String, DateTime, Integer, Text, ForeignKey
from sqlalchemy.orm import declarative_base, sessionmaker
import datetime

DATABASE_URL = "postgresql+psycopg://postgres:devpass@localhost:5432/postgres"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()


class Run(Base):
    __tablename__ = "runs"
    id = Column(Integer, primary_key=True)
    status = Column(String, default="running")
    started_at = Column(DateTime, default=datetime.datetime.utcnow)
    finished_at = Column(DateTime, nullable=True)


class StepRun(Base):
    __tablename__ = "step_runs"
    id = Column(Integer, primary_key=True)
    run_id = Column(Integer, ForeignKey("runs.id"))
    step_id = Column(String)
    status = Column(String)
    output = Column(Text, nullable=True)


def init_db():
    Base.metadata.create_all(engine)