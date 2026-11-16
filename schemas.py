import re
from datetime import date
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class StageInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    nom_etudiant: str = Field(min_length=1, examples=["Étudiant Démo"])
    entreprise: str = Field(min_length=1, examples=["Entreprise Exemple"])
    intitule: str = Field(min_length=1, examples=["Développement API REST"])
    date_debut: date = Field(examples=["2026-04-01"])
    date_fin: date = Field(examples=["2026-06-30"])

    @field_validator("date_debut", "date_fin", mode="before")
    @classmethod
    def validate_date_format(cls, value):
        # Les réponses SQLAlchemy fournissent déjà des objets date.
        if type(value) is date:
            return value
        if not isinstance(value, str) or not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value):
            raise ValueError("La date doit respecter le format YYYY-MM-DD.")
        return value

    @model_validator(mode="after")
    def validate_date_order(self) -> Self:
        if self.date_fin < self.date_debut:
            raise ValueError("La date de fin doit être supérieure ou égale à la date de début.")
        return self


class StageRead(StageInput):
    model_config = ConfigDict(from_attributes=True)

    id: int
