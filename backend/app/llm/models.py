from dataclasses import dataclass
from types import MappingProxyType
from typing import Mapping


@dataclass(frozen=True, slots=True)
class SparkModelConfig:
    name: str
    api_url: str
    domain: str


MODEL_REGISTRY: Mapping[str, SparkModelConfig] = MappingProxyType(
    {
        "lite": SparkModelConfig(
            name="lite",
            api_url="wss://spark-api.xf-yun.com/v1.1/chat",
            domain="general",
        ),
        "pro": SparkModelConfig(
            name="pro",
            api_url="wss://spark-api.xf-yun.com/v3.1/chat",
            domain="generalv3",
        ),
        "max": SparkModelConfig(
            name="max",
            api_url="wss://spark-api.xf-yun.com/v3.5/chat",
            domain="generalv3.5",
        ),
    }
)


def resolve_model(model: str) -> SparkModelConfig:
    try:
        return MODEL_REGISTRY[model]
    except KeyError as exc:
        supported = ", ".join(MODEL_REGISTRY)
        raise ValueError(
            f"Unknown Spark model {model!r}; supported models: {supported}"
        ) from exc

