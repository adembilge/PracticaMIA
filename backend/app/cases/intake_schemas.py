"""Strict, bounded product intake; categorization is NOT legal eligibility."""
from datetime import date
import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


REQUIRED_FIELDS = (
    "citizenship_class", "registration_context", "destination_municipality",
    "household_scope", "housing_basis",
)
SUPPORTED_FACTS = {
    "citizenship_class": "italian",
    "registration_context": "already_registered_in_italy",
    "destination_municipality": "milano",
    "household_scope": "individual_no_aggregation",
    "housing_basis": "registered_private_rental",
}


class IntakeFacts(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    citizenship_class: Literal["italian", "non_italian", "unknown"] | None = None
    registration_context: Literal["already_registered_in_italy", "arrival_from_abroad", "unknown"] | None = None
    destination_municipality: Literal["milano", "other", "unknown"] | None = None
    household_scope: Literal[
        "individual_no_aggregation", "joining_household", "multi_person", "unknown"
    ] | None = None
    housing_basis: Literal[
        "registered_private_rental", "owner", "guest", "other", "unknown"
    ] | None = None
    move_in_date: str | None = Field(default=None, max_length=10)

    @field_validator("move_in_date")
    @classmethod
    def validate_move_date(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
            raise ValueError("Expected YYYY-MM-DD")
        try:
            parsed = date.fromisoformat(value)
        except ValueError:
            raise ValueError("Invalid calendar date") from None
        if not 1900 <= parsed.year <= 2100:
            raise ValueError("Date outside intake limits")
        return value


class IntakeUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    facts: IntakeFacts
    confirm: bool = False


def describe_intake(facts: dict, confirmed: bool) -> dict:
    """Describe only product-level completeness; no administrative decision."""
    missing = [field for field in REQUIRED_FIELDS
               if facts.get(field) is None or facts[field] == "unknown"]
    unsupported = [
        field for field in REQUIRED_FIELDS
        if field not in missing and facts[field] != SUPPORTED_FACTS[field]
    ]
    return {
        "facts": facts,
        "fact_origin": "user_entered",
        "verification_state": "user_confirmed" if confirmed else "draft",
        "confirmed": confirmed,
        "missing_fields": missing,
        "outside_first_scenario": unsupported,
        "first_scenario_match": confirmed and not missing and not unsupported,
        "eligibility_evaluated": False,
        "document_requirements_evaluated": False,
        "official_submission": False,
    }
