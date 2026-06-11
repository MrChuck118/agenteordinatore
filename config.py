"""
config.py — Configurazione unificata per Agent Ordinatore.

Gestisce tutte le preferenze utente in un unico file config.json
salvato in %LOCALAPPDATA%/AgentOrdinatore/. Migra automaticamente
il vecchio settings.json dalla cartella del progetto.
"""

import json
import os
import sys
from pathlib import Path

from platformdirs import user_data_dir

# Percorso del vecchio settings.json (nella cartella del progetto)
_OLD_SETTINGS_FILE = Path(__file__).parent / "settings.json"

_DEFAULTS = {
    "ai_backend": "local",
    "selected_tier": "standard",
    "deepseek_model": "deepseek-v4-flash",
    "deepseek_api_key": "",
    "auto_detect": True,
    "gpu_offload": True,
    "allow_folder_rename": False,
    "theme": "dark",
}

AI_BACKEND_LOCAL = "local"
AI_BACKEND_DEEPSEEK = "deepseek"

DEEPSEEK_MODELS = {
    "deepseek-v4-flash": "DeepSeek V4 Flash (fallback Pro)",
    "deepseek-v4-pro": "DeepSeek V4 Pro",
}


def _get_config_dir() -> Path:
    """Ritorna la cartella dati dell'applicazione, creandola se necessario."""
    d = Path(user_data_dir("AgentOrdinatore", appauthor=False))
    d.mkdir(parents=True, exist_ok=True)
    return d


def _get_config_path() -> Path:
    return _get_config_dir() / "config.json"


def _migrate_old_settings():
    """Se esiste il vecchio settings.json, migra il contenuto e lo elimina."""
    if not _OLD_SETTINGS_FILE.exists():
        return {}

    migrated = {}
    try:
        data = json.loads(_OLD_SETTINGS_FILE.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            migrated = data
        _OLD_SETTINGS_FILE.unlink()
    except Exception:
        pass
    return migrated


def load_config() -> dict:
    """Carica la configurazione. Migra da settings.json se necessario."""
    config_path = _get_config_path()
    changed = False

    if config_path.exists():
        try:
            config = json.loads(config_path.read_text(encoding="utf-8"))
        except Exception:
            config = {}
            changed = True
    else:
        # Primo avvio: tenta migrazione dal vecchio settings.json
        config = _migrate_old_settings()
        changed = True

    # Riempi i campi mancanti con i default
    for key, default_val in _DEFAULTS.items():
        if key not in config:
            config[key] = default_val
            changed = True

    # Salva solo se qualcosa e' cambiato (migrazione o default aggiunti)
    if changed:
        save_config(config)
    return config


def save_config(config: dict):
    """Salva la configurazione su disco."""
    config_path = _get_config_path()
    config_path.write_text(
        json.dumps(config, indent=2, ensure_ascii=False), encoding="utf-8"
    )


def _project_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def get_env_file_candidates() -> list[Path]:
    """Percorsi .env supportati, in ordine di priorita'."""
    candidates = [
        Path.cwd() / ".env",
        _project_dir() / ".env",
        _get_config_dir() / ".env",
    ]
    unique: list[Path] = []
    seen: set[str] = set()
    for path in candidates:
        try:
            key = str(path.resolve())
        except OSError:
            key = str(path)
        if key not in seen:
            unique.append(path)
            seen.add(key)
    return unique


def _read_env_file_value(name: str) -> str:
    for env_path in get_env_file_candidates():
        if not env_path.exists():
            continue
        try:
            for raw_line in env_path.read_text(encoding="utf-8").splitlines():
                line = raw_line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, value = line.split("=", 1)
                if key.strip() != name:
                    continue
                value = value.strip().strip('"').strip("'")
                return value
        except OSError:
            continue
    return ""


def get_ai_backend() -> str:
    backend = load_config().get("ai_backend", AI_BACKEND_LOCAL)
    if backend not in {AI_BACKEND_LOCAL, AI_BACKEND_DEEPSEEK}:
        return AI_BACKEND_LOCAL
    return backend


def set_ai_backend(backend: str):
    if backend not in {AI_BACKEND_LOCAL, AI_BACKEND_DEEPSEEK}:
        backend = AI_BACKEND_LOCAL
    config = load_config()
    config["ai_backend"] = backend
    save_config(config)


def get_selected_tier() -> str:
    return load_config().get("selected_tier", "standard")


def set_selected_tier(tier: str):
    config = load_config()
    config["selected_tier"] = tier
    save_config(config)


def get_deepseek_model() -> str:
    configured = str(load_config().get("deepseek_model") or "").strip()
    if configured in DEEPSEEK_MODELS:
        return configured
    env_model = os.environ.get("DEEPSEEK_MODEL", "").strip() or _read_env_file_value("DEEPSEEK_MODEL")
    if env_model in DEEPSEEK_MODELS:
        return env_model
    return "deepseek-v4-flash"


def set_deepseek_model(model: str):
    if model not in DEEPSEEK_MODELS:
        model = "deepseek-v4-flash"
    config = load_config()
    config["deepseek_model"] = model
    save_config(config)


def get_saved_deepseek_api_key() -> str:
    return str(load_config().get("deepseek_api_key") or "").strip()


def set_deepseek_api_key(api_key: str):
    config = load_config()
    config["deepseek_api_key"] = str(api_key or "").strip()
    save_config(config)


def get_deepseek_api_key() -> str:
    saved = get_saved_deepseek_api_key()
    if saved:
        return saved
    env_value = os.environ.get("DEEPSEEK_API_KEY", "").strip()
    if env_value:
        return env_value
    return _read_env_file_value("DEEPSEEK_API_KEY")


def get_deepseek_api_key_source() -> str:
    if get_saved_deepseek_api_key():
        return "config"
    if os.environ.get("DEEPSEEK_API_KEY", "").strip():
        return "environment"
    if _read_env_file_value("DEEPSEEK_API_KEY"):
        return ".env"
    return ""


def is_deepseek_configured() -> bool:
    return bool(get_deepseek_api_key())


def get_theme() -> str:
    return load_config().get("theme", "dark")


def set_theme(theme: str):
    config = load_config()
    config["theme"] = theme
    save_config(config)


def is_folder_rename_allowed() -> bool:
    return bool(load_config().get("allow_folder_rename", False))


def set_folder_rename_allowed(enabled: bool):
    config = load_config()
    config["allow_folder_rename"] = bool(enabled)
    save_config(config)
