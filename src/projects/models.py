from datetime import datetime, UTC
from typing import TYPE_CHECKING, Optional

from sqlalchemy import String, BigInteger, Integer, SmallInteger, ForeignKey, TIMESTAMP
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base, CreatedUpdatedAt
from projects.constants import ProjectStatus

if TYPE_CHECKING:
    from teams.models import Team


class Project(CreatedUpdatedAt, Base):
    __tablename__ = 'projects'

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    name: Mapped[str] = mapped_column(String(50), nullable=False)
    description: Mapped[str] = mapped_column(String(500), nullable=False)
    document_path: Mapped[str] = mapped_column(String, nullable=True)
    score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # relationships
    team: Mapped['Team'] = relationship(
        'Team',
        back_populates='project',
        cascade='all, delete-orphan',
        passive_deletes=True
    )
    steps: Mapped[list['Step']] = relationship(
        'Step',
        back_populates='project',
        cascade='all, delete-orphan',
        passive_deletes=True
    )


class Step(Base):
    __tablename__ = 'steps'

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey('projects.id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )

    step_number: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    text: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    score: Mapped[int] = mapped_column(SmallInteger, default=0, nullable=False)
    timer_minutes: Mapped[int] = mapped_column(SmallInteger, default=30, nullable=False)
    status: Mapped[str] = mapped_column(String(200), default=ProjectStatus.NOT_STARTED, nullable=False)

    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        default=datetime.now(UTC),
        onupdate=datetime.now(UTC)
    )

    # relationships
    project: Mapped['Project'] = relationship('Project', back_populates='steps')
