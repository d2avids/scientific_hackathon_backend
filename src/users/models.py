from typing import Optional, TYPE_CHECKING

from sqlalchemy import Boolean, String, SmallInteger, BigInteger, ForeignKey, Date, Float
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base, CreatedUpdatedAt

if TYPE_CHECKING:
    from teams.models import Team, TeamMember
    from projects.models import StepComment


class User(CreatedUpdatedAt, Base):
    __tablename__ = 'users'

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(50), nullable=False, unique=True, index=True)
    password: Mapped[str] = mapped_column(String, nullable=False)

    # required business-logic related fields
    is_mentor: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    first_name: Mapped[str] = mapped_column(String(50), nullable=False)
    birth_date: Mapped[Date] = mapped_column(Date, nullable=False)
    last_name: Mapped[str] = mapped_column(String(50), nullable=False)
    patronymic: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    phone_number: Mapped[str] = mapped_column(String(11), nullable=False)
    edu_organization: Mapped[str] = mapped_column(String(100), nullable=False)
    verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # non-required business-logic related fields
    about: Mapped[Optional[str]] = mapped_column(String(2500), nullable=True)
    photo_path: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    personal_data: Mapped[bool] = mapped_column(Boolean, default=True)
    regulations_agreement: Mapped[bool] = mapped_column(Boolean, default=True)

    # relationships
    participant: Mapped['Participant'] = relationship(
        back_populates='user',
        cascade='all, delete-orphan',
        passive_deletes=True
    )
    mentor: Mapped['Mentor'] = relationship(
        back_populates='user',
        cascade='all, delete-orphan',
        passive_deletes=True
    )
    documents: Mapped[list['UserDocument']] = relationship(
        'UserDocument',
        back_populates='user',
        cascade='all, delete-orphan',
        passive_deletes=True
    )
    comments: Mapped[list['StepComment']] = relationship(
        'StepComment',
        back_populates='user',
        cascade='all, delete-orphan',
        passive_deletes=True
    )


class Region(Base):
    __tablename__ = 'regions'

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(250), nullable=False)
    code: Mapped[Optional[int]] = mapped_column(SmallInteger, nullable=True)

    # relationships
    participants: Mapped[list['Participant']] = relationship(back_populates='region')


class Participant(CreatedUpdatedAt, Base):
    __tablename__ = 'participants'

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey('users.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
        unique=True
    )
    region_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey('regions.id', ondelete='RESTRICT'),
        nullable=False
    )

    # required fields
    school_grade: Mapped[str] = mapped_column(String(15), nullable=False)
    city: Mapped[str] = mapped_column(String(250), nullable=False)

    # non-required fields
    interests: Mapped[Optional[str]] = mapped_column(String(250), nullable=True)
    olympics: Mapped[Optional[str]] = mapped_column(String(250), nullable=True)
    achievements: Mapped[Optional[str]] = mapped_column(String(250), nullable=True)

    # relationships
    user: Mapped['User'] = relationship(back_populates='participant', single_parent=True)
    region: Mapped['Region'] = relationship(back_populates='participants', cascade='all, delete')
    team_members: Mapped['TeamMember'] = relationship(
        back_populates='participant',
        cascade='all, delete-orphan',
        uselist=False
    )


class Mentor(CreatedUpdatedAt, Base):
    __tablename__ = 'mentors'

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey('users.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
        unique=True
    )

    # required fields
    specialization: Mapped[str] = mapped_column(String(250), nullable=False)
    job_title: Mapped[str] = mapped_column(String(150), nullable=False)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # non-required fields
    research_topics: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    articles: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    scientific_interests: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # relationships
    teams: Mapped[list['Team']] = relationship(
        'Team',
        back_populates='mentor',
        passive_deletes=True,
        lazy='selectin'
    )
    taught_subjects: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # relationships
    user: Mapped['User'] = relationship(back_populates='mentor', single_parent=True)
    teams: Mapped[list['Team']] = relationship('Team', back_populates='mentor', cascade='none')


class UserDocument(CreatedUpdatedAt, Base):
    __tablename__ = 'user_documents'

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey('users.id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    path: Mapped[str] = mapped_column(String, nullable=False)
    mimetype: Mapped[str] = mapped_column(String, nullable=False)
    size: Mapped[float] = mapped_column(Float, nullable=False)  # bytes

    user: Mapped['User'] = relationship('User', back_populates='documents')
