"""
config.py — Configurazione unificata per Agent Ordinatore.

Gestisce tutte le preferenze utente in un unico file config.json
salvato in %LOCALAPPDATA%/AgentOrdinatore/. Migra automaticamente
il vecchio settings.json dalla cartella del progetto.
"""

import json
from pathlib import Path

from platformdirs import user_data_dir

# Percorso del vecchio settings.json (nella cartella del progetto)
_OLD_SETTINGS_FILE = Path(__file__).parent / "settings.json"

_DEFAULTS = {
    "selected_tier": "standard",
    "auto_detect": True,
    "gpu_offload": True,
    "theme": "dark",
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


def get_selected_tier() -> str:
    return load_config().get("selected_tier", "standard")


def set_selected_tier(tier: str):
    config = load_config()
    config["selected_tier"] = tier
    save_config(config)


def get_theme() -> str:
    return load_config().get("theme", "dark")


def set_theme(theme: str):
    config = load_config()
    config["theme"] = theme
    save_config(config)
