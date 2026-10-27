from __future__ import annotations

from pydantic import BaseModel, field_validator


ALLOWED_SETTINGS = {
    "model_level",
    "temperature",
    "agent.profile_agent",
    "agent.resource_agent",
    "agent.path_agent",
    "agent.tutor_agent",
}


class UpdateSettingsRequest(BaseModel):
    settings: dict[str, str]

    @field_validator("settings")
    @classmethod
    def validate_settings(cls, values: dict[str, str]) -> dict[str, str]:
        if not values or set(values) - ALLOWED_SETTINGS:
            raise ValueError("包含不允许修改的系统设置")
        if "model_level" in values and values["model_level"] not in {
            "high",
            "medium",
            "low",
        }:
            raise ValueError("model_level 无效")
        if "temperature" in values:
            try:
                temperature = float(values["temperature"])
            except ValueError as exc:
                raise ValueError("temperature 必须是数字") from exc
            if not 0 <= temperature <= 2:
                raise ValueError("temperature 必须在 0 到 2 之间")
        for key, value in values.items():
            if key.startswith("agent.") and value not in {"true", "false"}:
                raise ValueError("Agent 开关必须是 true 或 false")
        return values
