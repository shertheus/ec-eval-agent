"""Validated contracts shared by HTTP, command line, and experiment workers."""
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)


class DatasetRequest(StrictModel):
    kind: Literal["sem", "var", "import"] = "sem"
    name: str = Field(default="demo", max_length=100)
    nodes: int = Field(default=5, ge=2, le=200)
    samples: int = Field(default=200, ge=30, le=100000)
    edges: int = Field(default=5, ge=0, le=10000)
    seed: int = Field(default=1, ge=0, le=2**31-1)
    mechanism: Literal["linear", "mlp", "tanh"] = "linear"
    noise_scale: float = Field(default=1., gt=0, le=100)
    path: str | None = None
    input_kind: Literal["iid", "timeseries"] = "timeseries"
    node_ids: list[str] | None = None
    sample_interval: float | None = Field(default=None, gt=0)
    source: str = Field(default="user supplied", max_length=1000)

    @model_validator(mode="after")
    def check_edges(self):
        if self.kind != "import" and self.edges > self.nodes*(self.nodes-1)//2:
            raise ValueError("edges exceeds this generator's graph capacity")
        if self.kind == "import" and not self.path:
            raise ValueError("import requires path inside BRAIN_EVAL_INPUT")
        if self.kind == "sem" and self.mechanism == "tanh":
            raise ValueError("SEM generator supports linear or mlp")
        if self.kind == "var" and self.mechanism == "mlp":
            raise ValueError("dynamic generator supports linear or tanh; it is not an MLP")
        return self


class Method(StrictModel):
    name: Literal["notears", "golem", "dag_gnn", "granger", "neural_gc"]
    params: dict[str, int | float | str | bool] = Field(default_factory=dict)
    device: Literal["cpu", "cuda"] = "cpu"


class Protocol(StrictModel):
    schema_version: Literal["1"] = "1"
    title: str = Field(default="Connectivity evaluation", min_length=1, max_length=200)
    dataset_ids: list[str] = Field(min_length=1, max_length=20)
    methods: list[Method] = Field(min_length=1, max_length=8)
    seeds: list[int] = Field(default_factory=lambda: [1], min_length=1, max_length=20)
    timeout_seconds: int = Field(default=300, ge=5, le=86400)
    exclude_self: Literal[True] = True
    evaluation_level: Literal["region"] = "region"

    @model_validator(mode="after")
    def unique(self):
        for values in (self.dataset_ids, self.seeds, [m.name for m in self.methods]):
            if len(values) != len(set(values)):
                raise ValueError("dataset IDs, seeds and method names must be unique")
        if any(s < 0 or s >= 2**31 for s in self.seeds):
            raise ValueError("seeds must be in [0, 2**31)")
        if len(self.dataset_ids)*len(self.methods)*len(self.seeds) > 200:
            raise ValueError("maximum 200 runs per experiment")
        return self


class Submission(StrictModel):
    protocol: Protocol
    idempotency_key: str = Field(min_length=1, max_length=128)


class Action(StrictModel):
    action: Literal["cancel", "retry"]


class Comparison(StrictModel):
    experiment_ids: list[str] = Field(min_length=2, max_length=20)
    strict_dataset_match: bool = True
