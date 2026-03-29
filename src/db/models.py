import json
from datetime import datetime, timezone

from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship

from src.db.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    workflows = relationship("Workflow", back_populates="user")


class Workflow(Base):
    __tablename__ = "workflows"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    workflow_json = Column(Text, nullable=False)
    n8n_id = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    user = relationship("User", back_populates="workflows")

    def set_workflow(self, data: dict):
        self.workflow_json = json.dumps(data)

    def get_workflow(self) -> dict:
        return json.loads(self.workflow_json)


class EventLog(Base):
    __tablename__ = "event_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    event_type = Column(String(50), nullable=False)
    app_name = Column(String(200), nullable=False)
    window_title = Column(String(500), nullable=True, default="")
    detail = Column(String(500), nullable=True, default="")

    user = relationship("User")


class WorkflowSuggestion(Base):
    __tablename__ = "workflow_suggestions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    description = Column(Text, nullable=False)
    summary = Column(String(300), nullable=True, default="")
    refined_prompt = Column(Text, nullable=True, default="")
    raw_events = Column(Text, nullable=False)
    status = Column(String(20), nullable=False, default="pending")

    user = relationship("User")
