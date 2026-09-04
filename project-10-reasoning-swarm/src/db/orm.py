import uuid
from datetime import datetime
from sqlalchemy import String, Integer, Float, Text, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from src.db.database import Base


class DebateRecord(Base):
    __tablename__ = "debates"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    question: Mapped[str] = mapped_column(Text)
    domain: Mapped[str] = mapped_column(String(100))
    max_rounds: Mapped[int] = mapped_column(Integer, default=3)
    consensus_reached: Mapped[bool] = mapped_column(Boolean, default=False)
    final_answer: Mapped[str | None] = mapped_column(Text, nullable=True)
    final_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    rounds: Mapped[list["RoundRecord"]] = relationship(
        "RoundRecord", back_populates="debate", cascade="all, delete-orphan"
    )


class RoundRecord(Base):
    __tablename__ = "rounds"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    debate_id: Mapped[str] = mapped_column(String, ForeignKey("debates.id"))
    round_number: Mapped[int] = mapped_column(Integer)
    summary: Mapped[str] = mapped_column(Text, default="")
    agreement_score: Mapped[float] = mapped_column(Float, default=0.0)

    debate: Mapped["DebateRecord"] = relationship("DebateRecord", back_populates="rounds")
    turns: Mapped[list["AgentTurnRecord"]] = relationship(
        "AgentTurnRecord", back_populates="round", cascade="all, delete-orphan"
    )


class AgentTurnRecord(Base):
    __tablename__ = "agent_turns"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    round_id: Mapped[int] = mapped_column(Integer, ForeignKey("rounds.id"))
    agent: Mapped[str] = mapped_column(String(50))
    content: Mapped[str] = mapped_column(Text)
    confidence: Mapped[float] = mapped_column(Float)
    key_claims: Mapped[str] = mapped_column(Text, default="")
    citations: Mapped[str] = mapped_column(Text, default="")

    round: Mapped["RoundRecord"] = relationship("RoundRecord", back_populates="turns")
