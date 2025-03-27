from sqlalchemy import BigInteger, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base, CreatedUpdatedAt
from projects.models import Project
from users.models import Mentor, Participant


class Team(CreatedUpdatedAt, Base):
    __tablename__ = 'teams'

    id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        autoincrement=True
    )
    name: Mapped[str] = mapped_column(String(250), nullable=False)

    mentor_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey('mentors.id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )
    project_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey('projects.id', ondelete='CASCADE'),
        nullable=True,
        index=True,
        unique=True
    )

    # relationships
    team_members: Mapped[list['TeamMember']] = relationship(
        'TeamMember',
        back_populates='team',
        cascade='all, delete-orphan',
        passive_deletes=True
    )
    mentor: Mapped['Mentor'] = relationship(
        'Mentor',
        back_populates='teams',
        passive_deletes=True,
    )
    project: Mapped['Project'] = relationship(
        'Project',
        back_populates='team'
    )


class TeamMember(CreatedUpdatedAt, Base):
    __tablename__ = 'team_members'

    id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        autoincrement=True
    )
    team_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey('teams.id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )
    participant_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey('participants.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
        unique=True
    )
    role_name: Mapped[str] = mapped_column(String(250), nullable=False)

    # relationships
    team: Mapped['Team'] = relationship(
        'Team',
        back_populates='team_members'
    )
    participant: Mapped['Participant'] = relationship(
        'Participant',
        back_populates='team_members'
    )
