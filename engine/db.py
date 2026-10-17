from sqlalchemy import create_engine, Column, String, DateTime, Integer, Text, ForeignKey
from sqlalchemy.orm import declarative_base, sessionmaker
import datetime
import os
from sqlalchemy import BigInteger, Boolean
from dotenv import load_dotenv
load_dotenv()

_url = os.environ.get("DATABASE_URL")
if not _url:
    raise RuntimeError("DATABASE_URL is not set")

# Neon gives "postgresql://...", but SQLAlchemy needs the driver named
# explicitly to use psycopg 3.
if _url.startswith("postgresql://"):
    _url = _url.replace("postgresql://", "postgresql+psycopg://", 1)

DATABASE_URL = _url

engine = create_engine(DATABASE_URL, pool_pre_ping=True, pool_recycle=300)
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

class SeenJob(Base):
    __tablename__ = "seen_jobs"
    id = Column(Integer, primary_key=True)
    job_id = Column(BigInteger, unique=True)

class Job(Base):
    __tablename__ = "jobs"
    id = Column(Integer, primary_key=True)
    job_id = Column(BigInteger, unique=True)
    title = Column(String)
    company = Column(String)
    url = Column(String)
    location = Column(String)
    status = Column(String, default="new")   # new / applied / ignored
    first_seen = Column(DateTime, default=datetime.datetime.utcnow)
    last_seen = Column(DateTime)
    is_open = Column(Boolean, default=True)    


def init_db():
    Base.metadata.create_all(engine)