from pydantic import BaseModel, ConfigDict, Field


class PredictionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    sqft: float = Field(ge=300, le=8000)
    bedrooms: int = Field(ge=0, le=10)
    bathrooms: float = Field(ge=0.5, le=8, multiple_of=0.5)
    age_years: int = Field(ge=0, le=150)
    location_score: float = Field(ge=0, le=10)


class PredictionResponse(BaseModel):
    prediction: float
    model_version: str


class HealthResponse(BaseModel):
    status: str
    api_version: str
    model_version: str
