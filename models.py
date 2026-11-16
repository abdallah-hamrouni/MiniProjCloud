from datetime import date

from sqlalchemy import Date, String
from sqlalchemy.orm import Mapped, mapped_column

from database import Base


class Stage(Base):
    __tablename__ = "stages"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    nom_etudiant: Mapped[str] = mapped_column(String, nullable=False)
    entreprise: Mapped[str] = mapped_column(String, nullable=False)
    intitule: Mapped[str] = mapped_column(String, nullable=False)
    date_debut: Mapped[date] = mapped_column(Date, nullable=False)
    date_fin: Mapped[date] = mapped_column(Date, nullable=False)
