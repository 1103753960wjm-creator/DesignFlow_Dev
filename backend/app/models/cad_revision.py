import uuid
from sqlalchemy import Column, DateTime, String, Text, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import UUID
from app.db.session import Base


class CadRevision(Base):
    __tablename__ = "cad_revisions"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True, index=True)
    job_id = Column(String, unique=True, nullable=False)
    input_filename = Column(String, nullable=True)
    input_ext = Column(String, nullable=True)
    output_dir = Column(String, nullable=True)
    model_obj_path = Column(String, nullable=True)
    views_json = Column(Text, nullable=True)
    status = Column(String, nullable=False, default="done")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
