import json
from pathlib import Path
from typing import Any
import httpx
import yaml
from .config import get_settings

PROMPT_PATH = Path("prompts/system_prompts.yaml")


def load_prompts() -> dict[str, Any]:
    if not PROMPT_PATH.exists():
        return {"prompts": {}}
    return yaml.safe_load(PROMPT_PATH.read_text(encoding="utf-8")) or {"prompts": {}}


def save_prompt(prompt_id: str, system: str, user_template: str, provider: str = "configurable", model: str = "configurable") -> dict[str, Any]:
    data = load_prompts()
    data.setdefault("prompts", {})[prompt_id] = {
        "provider": provider,
        "model": model,
        "system": system,
        "user_template": user_template,
    }
    PROMPT_PATH.parent.mkdir(parents=True, exist_ok=True)
    PROMPT_PATH.write_text(yaml.safe_dump(data, sort_keys=True, allow_unicode=True), encoding="utf-8")
    return data["prompts"][prompt_id]


def render_template(template: str, variables: dict[str, Any]) -> str:
    rendered = template
    for key, value in variables.items():
        rendered = rendered.replace("{{" + key + "}}", json.dumps(value, ensure_ascii=False) if not isinstance(value, str) else value)
    return rendered


async def run_ai_prompt(prompt_id: str, variables: dict[str, Any], provider: str | None = None, model: str | None = None) -> dict[str, Any]:
    settings = get_settings()
    prompts = load_prompts().get("prompts", {})
    prompt = prompts.get(prompt_id)
    if not prompt:
        raise ValueError(f"Prompt no encontrado: {prompt_id}")

    selected_provider = provider or settings.ai_provider
    system = prompt.get("system", "")
    user = render_template(prompt.get("user_template", ""), variables)

    if selected_provider == "ollama":
        selected_model = model or settings.ollama_model
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(
                f"{settings.ollama_base_url.rstrip('/')}/api/chat",
                json={"model": selected_model, "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}], "stream": False},
            )
            response.raise_for_status()
            data = response.json()
            return {"provider": "ollama", "model": selected_model, "content": data.get("message", {}).get("content", ""), "raw": data}

    if selected_provider == "openai_compatible":
        if not settings.external_ai_base_url or not settings.external_ai_api_key:
            raise ValueError("EXTERNAL_AI_BASE_URL y EXTERNAL_AI_API_KEY son requeridos para openai_compatible")
        selected_model = model or settings.external_ai_model
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(
                f"{settings.external_ai_base_url.rstrip('/')}/v1/chat/completions",
                headers={"Authorization": f"Bearer {settings.external_ai_api_key}"},
                json={"model": selected_model, "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}]},
            )
            response.raise_for_status()
            data = response.json()
            return {"provider": "openai_compatible", "model": selected_model, "content": data["choices"][0]["message"]["content"], "raw": data}

    return {"provider": "mock", "model": model or "mock", "content": "Proveedor mock: configure Ollama o una API externa para respuestas reales.", "raw": {}}
