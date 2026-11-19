from pydantic import BaseModel, Field, field_validator


class RecipeRequest(BaseModel):
    ingredients: list[str] = Field(min_length=1, max_length=30)

    @field_validator("ingredients")
    @classmethod
    def clean_ingredients(cls, values: list[str]) -> list[str]:
        cleaned = list(dict.fromkeys(
            " ".join(value.strip().lower().split())
            for value in values
            if value and value.strip()
        ))
        if not cleaned:
            raise ValueError("Please provide at least one non-empty ingredient.")
        if any(len(value) > 60 for value in cleaned):
            raise ValueError("Each ingredient must be 60 characters or fewer.")
        return cleaned


class AssistantRequest(BaseModel):
    message: str = Field(min_length=2, max_length=500)

    @field_validator("message")
    @classmethod
    def clean_message(cls, value: str) -> str:
        cleaned = " ".join(value.strip().split())
        if not cleaned:
            raise ValueError("Please enter a dish or a cooking question.")
        return cleaned
