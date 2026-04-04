import httpx


class LMStudioClient:
    def __init__(self, models_url: str, timeout: float = 5.0):
        self.models_url = models_url
        self.timeout = timeout

    def list_models(self) -> list[str]:
        response = httpx.get(self.models_url, timeout=self.timeout)
        response.raise_for_status()
        payload = response.json()
        items = payload.get("data", [])
        models = [
            item["id"]
            for item in items
            if isinstance(item, dict) and isinstance(item.get("id"), str) and item["id"]
        ]
        return sorted(models)

    def is_reachable(self) -> bool:
        try:
            self.list_models()
            return True
        except Exception:
            return False
