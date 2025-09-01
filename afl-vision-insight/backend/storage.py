# backend/storage.py
from __future__ import annotations
import os, uuid
from datetime import datetime
from typing import Optional, List, Dict, Any

from sqlalchemy import create_engine, func, String, Integer, DateTime, JSON, select, UniqueConstraint
from sqlalchemy.orm import sessionmaker, DeclarativeBase, Mapped, mapped_column

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL not set")

engine = create_engine(DATABASE_URL, future=True, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)

IS_SQLITE = DATABASE_URL.startswith("sqlite")

if IS_SQLITE:
    UUID_TYPE = String(36)
    JSON_TYPE = JSON
    def UUID_DEFAULT() -> str:
        return str(uuid.uuid4())
else:
    from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB as PG_JSONB
    UUID_TYPE = PG_UUID(as_uuid=True)
    JSON_TYPE = PG_JSONB
    UUID_DEFAULT = uuid.uuid4

class Base(DeclarativeBase):
    pass

class Upload(Base):
    __tablename__ = "uploads"
    id: Mapped[str] = mapped_column(UUID_TYPE, primary_key=True, default=UUID_DEFAULT)
    path: Mapped[str] = mapped_column(String(512), nullable=False)
    media_type: Mapped[str] = mapped_column(String(32), nullable=False, default="video")
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

class Inference(Base):
    __tablename__ = "inferences"
    id: Mapped[str] = mapped_column(UUID_TYPE, primary_key=True, default=UUID_DEFAULT)
    upload_id: Mapped[str] = mapped_column(UUID_TYPE, nullable=False, index=True)
    task: Mapped[str] = mapped_column(String(16), nullable=False)  # "player" | "crowd"
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="ok")
    payload: Mapped[dict] = mapped_column(JSON_TYPE, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
class User(Base):
    __tablename__ = "users"
    __table_args__ = (UniqueConstraint("email", name="uq_users_email"),)
    id: Mapped[str] = mapped_column(UUID_TYPE, primary_key=True, default=UUID_DEFAULT)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

Base.metadata.create_all(bind=engine)

def create_user(email: str, hashed_password: str) -> dict:
    with _db() as db:
        user = User(email=email.lower().strip(), hashed_password=hashed_password)
        db.add(user); db.commit(); db.refresh(user)
        return {"id": str(user.id), "email": user.email, "created_at": user.created_at.isoformat()}

def get_user_by_email(email: str) -> Optional[User]:
    with _db() as db:
        stmt = select(User).where(User.email == email.lower().strip())
        row = db.execute(stmt).scalar_one_or_none()
        return row

def get_user_by_id(user_id: str) -> Optional[User]:
    with _db() as db:
        key = user_id if IS_SQLITE else uuid.UUID(user_id)
        stmt = select(User).where(User.id == key)
        row = db.execute(stmt).scalar_one_or_none()
        return row

def _db():
    return SessionLocal()

def save_upload(path: str, media_type: str, size_bytes: int) -> dict:
    with _db() as db:
        row = Upload(path=path, media_type=media_type, size_bytes=size_bytes)
        db.add(row); db.commit(); db.refresh(row)
        return {
            "id": str(row.id),
            "path": row.path,
            "media_type": row.media_type,
            "size_bytes": row.size_bytes,
            "created_at": row.created_at.isoformat()
        }

def get_upload(upload_id: str) -> Optional[dict]:
    from sqlalchemy.exc import NoResultFound
    with _db() as db:
        try:
            key = upload_id if IS_SQLITE else uuid.UUID(upload_id)
            row = db.query(Upload).filter(Upload.id == key).one()
            return {
                "id": str(row.id),
                "path": row.path,
                "media_type": row.media_type,
                "size_bytes": row.size_bytes,
                "created_at": row.created_at.isoformat()
            }
        except NoResultFound:
            return None

def save_inference(upload_id: str, task: str, status: str, payload: Dict[str, Any]) -> dict:
    with _db() as db:
        key = upload_id if IS_SQLITE else uuid.UUID(upload_id)
        row = Inference(upload_id=key, task=task, status=status, payload=payload or {})
        db.add(row); db.commit(); db.refresh(row)
        return {
            "id": str(row.id),
            "upload_id": str(row.upload_id),
            "task": row.task,
            "status": row.status,
            "payload": row.payload,
            "created_at": row.created_at.isoformat()
        }

def list_inferences(limit: int = 50) -> List[dict]:
    with _db() as db:
        rows = db.query(Inference).order_by(Inference.created_at.desc()).limit(limit).all()
        return [{
            "id": str(r.id),
            "upload_id": str(r.upload_id),
            "task": r.task,
            "status": r.status,
            "payload": r.payload,
            "created_at": r.created_at.isoformat()
        } for r in rows]

def inferences_summary() -> dict:
    with _db() as db:
        total  = db.query(func.count(Inference.id)).scalar() or 0
        player = db.query(func.count(Inference.id)).filter(Inference.task == "player").scalar() or 0
        crowd  = db.query(func.count(Inference.id)).filter(Inference.task == "crowd").scalar() or 0
        last   = db.query(Inference).order_by(Inference.created_at.desc()).first()
        last_payload = None
        if last:
            last_payload = {
                "id": str(last.id),
                "upload_id": str(last.upload_id),
                "task": last.task,
                "status": last.status,
                "payload": last.payload,
                "created_at": last.created_at.isoformat()
            }
        return {"total": total, "by_task": {"player": player, "crowd": crowd}, "last": last_payload}

def init_db() -> None:
    Base.metadata.create_all(bind=engine)
    with engine.connect() as conn:
        conn.exec_driver_sql("SELECT 1")
