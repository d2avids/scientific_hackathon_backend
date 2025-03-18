from database import Base, CreatedUpdatedAt
from sqlalchemy import ForeignKey, String, BigInteger, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from teams.models import Team

# TODO: Дописать модель проекта
class Project(CreatedUpdatedAt, Base):
    __tablename__ = 'projects'

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(250), nullable=False)
    description: Mapped[str] = mapped_column(String(250), nullable=False)
    document_path: Mapped[str] = mapped_column(String, nullable=False)
    score: Mapped[int] = mapped_column(Integer, nullable=False)

    team: Mapped['Team'] = relationship(
        'Team',
        back_populates='project',
        cascade='all, delete-orphan',
        passive_deletes=True
    )
