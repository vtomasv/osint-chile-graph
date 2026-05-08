from typing import Any, Literal
from pydantic import BaseModel, Field


class SeedRequest(BaseModel):
    investigation_id: str | None = None
    input_type: Literal["rut", "email", "phone", "plate", "domain", "name", "company"]
    value: str = Field(min_length=1, max_length=500)


class InvestigationCreate(BaseModel):
    title: str = Field(min_length=2, max_length=255)
    objective: str = ""


class TransformRunRequest(BaseModel):
    investigation_id: str
    transform_id: str
    input_type: str
    value: str


class EntityOut(BaseModel):
    id: str
    type: str
    label: str
    value: str = ""
    properties: dict[str, Any] = {}
    confidence: float = 1.0


class EdgeOut(BaseModel):
    id: str
    source: str
    target: str
    type: str
    properties: dict[str, Any] = {}
    confidence: float = 0.7


class GraphOut(BaseModel):
    nodes: list[EntityOut]
    edges: list[EdgeOut]


class TransformOut(BaseModel):
    id: str
    name: str
    description: str
    input_types: list[str]
    output_types: list[str]
    execution_mode: Literal["automatic", "human_in_the_loop", "blocked"]
    risk_level: Literal["low", "medium", "high"]
    requires_human: bool
    source_policy: str


class AIRequest(BaseModel):
    prompt_id: str
    variables: dict[str, Any] = {}
    provider: str | None = None
    model: str | None = None



class PromptUpdate(BaseModel):
    prompt_id: str
    system: str = Field(min_length=1)
    user_template: str = Field(min_length=1)
    provider: str = "configurable"
    model: str = "configurable"
