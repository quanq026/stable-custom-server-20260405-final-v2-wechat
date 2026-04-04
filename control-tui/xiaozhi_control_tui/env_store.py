from pathlib import Path
import uuid

from .constants import DEFAULT_MANAGED_ENV


def _decode_value(value: str) -> str:
    return value.replace("\\n", "\n")


def _encode_value(value: str) -> str:
    return value.replace("\r\n", "\n").replace("\n", "\\n")


def load_env(path: Path) -> dict[str, str]:
    if not path.exists():
        return dict(DEFAULT_MANAGED_ENV)

    values: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if key:
            values[key] = _decode_value(value)

    merged = dict(DEFAULT_MANAGED_ENV)
    merged.update(values)
    return merged


def _write_env(path: Path, values: dict[str, str]) -> dict[str, str]:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [f"{key}={_encode_value(values[key])}" for key in sorted(values)]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return values


def ensure_server_id(path: Path) -> str:
    merged = load_env(path)
    existing = merged.get("XIAOZHI_BRIDGE_SERVER_ID", "").strip()
    if existing:
        return existing

    server_id = uuid.uuid4().hex
    merged["XIAOZHI_BRIDGE_SERVER_ID"] = server_id
    _write_env(path, merged)
    return server_id


def save_env(path: Path, updates: dict[str, str | None]) -> dict[str, str]:
    merged = load_env(path)
    for key, value in updates.items():
        if value is None:
            merged.pop(key, None)
        else:
            merged[key] = str(value)

    if not merged.get("XIAOZHI_BRIDGE_SERVER_ID", "").strip():
        merged["XIAOZHI_BRIDGE_SERVER_ID"] = uuid.uuid4().hex
    return _write_env(path, merged)
