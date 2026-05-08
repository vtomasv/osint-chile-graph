from contextlib import contextmanager
from datetime import datetime
from sqlalchemy import JSON, DateTime, Float, String, Text, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker
from .config import get_settings

settings = get_settings()
engine = create_engine(settings.database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass


class Investigation(Base):
    __tablename__ = "investigations"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    objective: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(32), default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Entity(Base):
    __tablename__ = "entities"
    id: Mapped[str] = mapped_column(String(96), primary_key=True)
    investigation_id: Mapped[str] = mapped_column(String(64), index=True)
    type: Mapped[str] = mapped_column(String(64), index=True)
    label: Mapped[str] = mapped_column(String(255), index=True)
    value: Mapped[str] = mapped_column(Text, default="")
    properties: Mapped[dict] = mapped_column(JSON, default=dict)
    confidence: Mapped[float] = mapped_column(Float, default=1.0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Relationship(Base):
    __tablename__ = "relationships"
    id: Mapped[str] = mapped_column(String(96), primary_key=True)
    investigation_id: Mapped[str] = mapped_column(String(64), index=True)
    source_id: Mapped[str] = mapped_column(String(96), index=True)
    target_id: Mapped[str] = mapped_column(String(96), index=True)
    type: Mapped[str] = mapped_column(String(64), index=True)
    properties: Mapped[dict] = mapped_column(JSON, default=dict)
    confidence: Mapped[float] = mapped_column(Float, default=0.7)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Evidence(Base):
    __tablename__ = "evidence"
    id: Mapped[str] = mapped_column(String(96), primary_key=True)
    investigation_id: Mapped[str] = mapped_column(String(64), index=True)
    source_name: Mapped[str] = mapped_column(String(255), default="local")
    source_url: Mapped[str] = mapped_column(Text, default="")
    extract: Mapped[str] = mapped_column(Text, default="")
    confidence: Mapped[float] = mapped_column(Float, default=0.7)
    properties: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class TransformRun(Base):
    __tablename__ = "transform_runs"
    id: Mapped[str] = mapped_column(String(96), primary_key=True)
    investigation_id: Mapped[str] = mapped_column(String(64), index=True)
    transform_id: Mapped[str] = mapped_column(String(128), index=True)
    input_type: Mapped[str] = mapped_column(String(64))
    input_value: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(32), default="completed")
    output: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class PromptConfig(Base):
    __tablename__ = "prompt_configs"
    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    system: Mapped[str] = mapped_column(Text)
    user_template: Mapped[str] = mapped_column(Text)
    provider: Mapped[str] = mapped_column(String(64), default="configurable")
    model: Mapped[str] = mapped_column(String(128), default="configurable")
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


def init_db() -> None:
    Base.metadata.create_all(bind=engine)


@contextmanager
def session_scope():
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
