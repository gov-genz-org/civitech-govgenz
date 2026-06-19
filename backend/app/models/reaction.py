from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, UniqueConstraint
from app.database import Base


class Reaction(Base):
    __tablename__ = "reactions"

    id           = Column(Integer, primary_key=True, index=True)
    user_id      = Column(Integer, nullable=False, index=True)
    content_type = Column(String(20), nullable=False, index=True)  # fact | alert | thread
    content_id   = Column(Integer, nullable=False, index=True)
    reaction     = Column(String(10), nullable=False)              # up | down
    created_at   = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint('user_id', 'content_type', 'content_id', name='uq_user_reaction'),
    )
