from __future__ import annotations

import json
from datetime import datetime, timedelta

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from src.models import Episode, PreferenceProfile, PreferenceUpdate


class Base(DeclarativeBase):
    pass


class EpisodeRow(Base):
    __tablename__ = "episodes"

    id = sa.Column(sa.String, primary_key=True)
    user_id = sa.Column(sa.String, nullable=False, index=True)
    event_type = sa.Column(sa.String, nullable=False)
    subject = sa.Column(sa.String, nullable=False)
    detail = sa.Column(sa.Text, nullable=False)
    sentiment = sa.Column(sa.Float, default=0.0)
    occurred_at = sa.Column(sa.DateTime, nullable=False)


class ProfileRow(Base):
    __tablename__ = "preference_profiles"

    user_id = sa.Column(sa.String, primary_key=True)
    communication_style = sa.Column(sa.String, default="concise")
    topics_of_interest = sa.Column(sa.Text, default="[]")   # JSON array
    topics_to_avoid = sa.Column(sa.Text, default="[]")      # JSON array
    known_context = sa.Column(sa.Text, default="{}")        # JSON object
    updated_at = sa.Column(sa.DateTime, nullable=False)


class PostgresService:
    def __init__(self, dsn: str) -> None:
        self._engine: AsyncEngine = create_async_engine(dsn, echo=False)
        self._session_factory = sessionmaker(
            self._engine, class_=AsyncSession, expire_on_commit=False
        )

    async def init_schema(self) -> None:
        async with self._engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    # ── Episodes ─────────────────────────────────────────────────────────────

    async def insert_episode(self, episode: Episode) -> None:
        async with self._session_factory() as session:
            row = EpisodeRow(
                id=episode.id,
                user_id=episode.user_id,
                event_type=episode.event_type,
                subject=episode.subject,
                detail=episode.detail,
                sentiment=episode.sentiment,
                occurred_at=episode.occurred_at,
            )
            session.add(row)
            await session.commit()

    async def get_recent_episodes(
        self,
        user_id: str,
        days: int = 30,
        subjects: list[str] | None = None,
        limit: int = 20,
    ) -> list[Episode]:
        cutoff = datetime.utcnow() - timedelta(days=days)
        async with self._session_factory() as session:
            stmt = (
                sa.select(EpisodeRow)
                .where(EpisodeRow.user_id == user_id)
                .where(EpisodeRow.occurred_at >= cutoff)
                .order_by(EpisodeRow.occurred_at.desc())
                .limit(limit)
            )
            if subjects:
                stmt = stmt.where(EpisodeRow.subject.in_(subjects))
            result = await session.execute(stmt)
            rows = result.scalars().all()
        return [
            Episode(
                id=r.id,
                user_id=r.user_id,
                event_type=r.event_type,
                subject=r.subject,
                detail=r.detail,
                sentiment=r.sentiment,
                occurred_at=r.occurred_at,
            )
            for r in rows
        ]

    async def get_old_episodes(self, user_id: str, days: int = 30) -> list[Episode]:
        cutoff = datetime.utcnow() - timedelta(days=days)
        async with self._session_factory() as session:
            result = await session.execute(
                sa.select(EpisodeRow)
                .where(EpisodeRow.user_id == user_id)
                .where(EpisodeRow.occurred_at < cutoff)
            )
            rows = result.scalars().all()
        return [
            Episode(
                id=r.id,
                user_id=r.user_id,
                event_type=r.event_type,
                subject=r.subject,
                detail=r.detail,
                sentiment=r.sentiment,
                occurred_at=r.occurred_at,
            )
            for r in rows
        ]

    async def delete_episodes(self, episode_ids: list[str]) -> None:
        async with self._session_factory() as session:
            await session.execute(
                sa.delete(EpisodeRow).where(EpisodeRow.id.in_(episode_ids))
            )
            await session.commit()

    # ── Preference profile ────────────────────────────────────────────────────

    async def load_profile(self, user_id: str) -> PreferenceProfile:
        async with self._session_factory() as session:
            result = await session.execute(
                sa.select(ProfileRow).where(ProfileRow.user_id == user_id)
            )
            row = result.scalar_one_or_none()
        if row is None:
            return PreferenceProfile(user_id=user_id)
        return PreferenceProfile(
            user_id=row.user_id,
            communication_style=row.communication_style,
            topics_of_interest=json.loads(row.topics_of_interest),
            topics_to_avoid=json.loads(row.topics_to_avoid),
            known_context=json.loads(row.known_context),
            updated_at=row.updated_at,
        )

    async def save_profile(self, profile: PreferenceProfile) -> None:
        async with self._session_factory() as session:
            existing = await session.get(ProfileRow, profile.user_id)
            now = datetime.utcnow()
            if existing is None:
                row = ProfileRow(
                    user_id=profile.user_id,
                    communication_style=profile.communication_style,
                    topics_of_interest=json.dumps(profile.topics_of_interest),
                    topics_to_avoid=json.dumps(profile.topics_to_avoid),
                    known_context=json.dumps(profile.known_context),
                    updated_at=now,
                )
                session.add(row)
            else:
                existing.communication_style = profile.communication_style
                existing.topics_of_interest = json.dumps(profile.topics_of_interest)
                existing.topics_to_avoid = json.dumps(profile.topics_to_avoid)
                existing.known_context = json.dumps(profile.known_context)
                existing.updated_at = now
            await session.commit()

    async def apply_preference_update(
        self, user_id: str, update: PreferenceUpdate
    ) -> PreferenceProfile:
        profile = await self.load_profile(user_id)
        if update.communication_style:
            profile.communication_style = update.communication_style
        if update.topics_of_interest:
            merged = list(set(profile.topics_of_interest + update.topics_of_interest))
            profile.topics_of_interest = merged
        if update.topics_to_avoid:
            merged = list(set(profile.topics_to_avoid + update.topics_to_avoid))
            profile.topics_to_avoid = merged
        if update.known_context:
            profile.known_context.update(update.known_context)
        await self.save_profile(profile)
        return profile
