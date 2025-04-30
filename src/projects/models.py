from datetime import datetime, UTC
from typing import TYPE_CHECKING, Optional

from sqlalchemy import String, BigInteger, Integer, SmallInteger, Float, ForeignKey, TIMESTAMP, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base, CreatedUpdatedAt
from projects.constants import ProjectStatus

if TYPE_CHECKING:
    from teams.models import Team
    from users.models import User


class Project(CreatedUpdatedAt, Base):
    __tablename__ = 'projects'

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    name: Mapped[str] = mapped_column(String(50), nullable=False)
    description: Mapped[str] = mapped_column(String(500), nullable=False)
    document_path: Mapped[str] = mapped_column(String, nullable=True)
    score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # notification flag
    new_submission: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

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
    attempts: Mapped[list['StepAttempt']] = relationship('StepAttempt', back_populates='step')
    files: Mapped[list['StepFile']] = relationship('StepFile', back_populates='step')
    comments: Mapped[list['StepComment']] = relationship('StepComment', back_populates='step')


class StepAttempt(Base):
    __tablename__ = 'step_attempts'

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    step_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey('steps.id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )
    started_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), )
    end_time_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), )
    submitted_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=True,
    )

    # relationships
    step: Mapped['Step'] = relationship('Step', back_populates='attempts')


class StepFile(Base):
    __tablename__ = 'step_files'

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    step_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey('steps.id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )
    file_path: Mapped[str] = mapped_column(String, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    mimetype: Mapped[str] = mapped_column(String, nullable=False)
    size: Mapped[float] = mapped_column(Float, nullable=False)  # bytes

    # relationships
    step: Mapped['Step'] = relationship('Step', back_populates='files')


class StepComment(Base):
    __tablename__ = 'step_comments'

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    step_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey('steps.id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )
    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey('users.id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )
    text: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        default=datetime.now(UTC),
        onupdate=datetime.now(UTC)
    )

    # relationships
    step: Mapped['Step'] = relationship('Step', back_populates='comments')
    user: Mapped['User'] = relationship('User', back_populates='comments')
    files: Mapped[list['StepCommentFile']] = relationship('StepCommentFile', back_populates='comment')


class StepCommentFile(Base):
    __tablename__ = 'step_comments_files'

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    comment_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey('step_comments.id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )
    file_path: Mapped[str] = mapped_column(String, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    mimetype: Mapped[str] = mapped_column(String, nullable=False)
    size: Mapped[float] = mapped_column(Float, nullable=False)  # bytes

    # relationships
    comment: Mapped['StepComment'] = relationship('StepComment', back_populates='files')
