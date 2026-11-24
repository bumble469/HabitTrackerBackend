from datetime import date
from typing import Optional
from pydantic import AliasChoices, BaseModel, ConfigDict, Field, field_validator

class RiskHabit(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str
    name: str = ""
    created_on: date = Field(validation_alias=AliasChoices("created_on", "createdAt"))

    @field_validator("created_on", mode="before")
    @classmethod
    def trim_created_on(cls, v):
        """Accept '2026-11-20T10:00:00.000Z' as well as '2026-11-20'."""
        if isinstance(v, str) and len(v) > 10:
            return v[:10]
        return v


class RiskRequest(BaseModel):
    today: Optional[date] = None
    habits: list[RiskHabit]
    completions: dict[str, list[date]] = {}


class RiskItem(BaseModel):
    habit_id: str
    risk: Optional[float]
    level: str
    reasons: list[str]
