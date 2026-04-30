"""
model_manager.py — Gestione download e storage dei modelli GGUF.

Scarica i modelli Qwen3.5 da HuggingFace e li salva in
%LOCALAPPDATA%/AgentOrdinatore/models/.
"""

from pathlib import Path

from platformdirs import user_data_dir

from logger import get_app_logger

_log = get_app_logger()

MODELS = {
    "lite": {
        "name": "Qwen3.5-0.8B",
        "repo": "unsloth/Qwen3.5-0.8B-GGUF",
        "filename": "Qwen3.5-0.8B-Q4_K_M.gguf",
        "size_bytes": 533_000_000,
    },
    "standard": {
        "name": "Qwen3.5-2B",
        "repo": "unsloth/Qwen3.5-2B-GGUF",
        "filename": "Qwen3.5-2B-Q4_K_M.gguf",
        "size_bytes": 1_280_000_000,
    },
    "pro": {
        "name": "Qwen3.5-4B",
        "repo": "unsloth/Qwen3.5-4B-GGUF",
        "filename": "Qwen3.5-4B-Q4_K_M.gguf",
        "size_bytes": 2_740_000_000,
    },
    "ultra": {
        "name": "Qwen3.5-9B",
        "repo": "unsloth/Qwen3.5-9B-GGUF",
        "filename": "Qwen3.5-9B-Q4_K_M.gguf",
        "size_bytes": 5_680_000_000,
    },
}


def get_models_dir() -> Path:
    """Ritorna la cartella dei modelli, creandola se necessario."""
    d = Path(user_data_dir("AgentOrdinatore", appauthor=False)) / "models"
    d.mkdir(parents=True, exist_ok=True)
    return d


def get_model_path(tier: str) -> Path:
    """Ritorna il path completo del file GGUF per il tier indicato."""
    info = MODELS[tier]
    return get_models_dir() / info["filename"]


def is_model_downloaded(tier: str) -> bool:
    """Controlla se il modello del tier e' gia' scaricato."""
    return get_model_path(tier).exists()


def download_model(tier: str) -> Path:
    """
    Scarica il modello GGUF da HuggingFace.

    Args:
        tier: Il tier del modello da scaricare.

    Returns:
        Path del file scaricato.
    """
    from huggingface_hub import hf_hub_download

    info = MODELS[tier]
    models_dir = get_models_dir()

    _log.info("Download avviato: tier=%s repo=%s file=%s", tier, info["repo"], info["filename"])

    # huggingface_hub supporta un callback di progresso tramite tqdm,
    # ma per la GUI usiamo un approccio diverso: scarichiamo con
    # hf_hub_download e monitoriamo la dimensione del file.
    try:
        dest = hf_hub_download(
            repo_id=info["repo"],
            filename=info["filename"],
            local_dir=str(models_dir),
        )
    except Exception:
        _log.exception("Download fallito: tier=%s", tier)
        raise

    _log.info("Download completato: tier=%s path=%s", tier, dest)
    return Path(dest)


def delete_model(tier: str) -> bool:
    """Elimina il file GGUF di un tier. Ritorna True se eliminato."""
    path = get_model_path(tier)
    if path.exists():
        path.unlink()
        _log.info("Modello eliminato: tier=%s path=%s", tier, path)
        return True
    _log.debug("Eliminazione modello tier=%s richiesta ma file inesistente", tier)
    return False


def get_downloaded_models() -> list[str]:
    """Ritorna la lista dei tier con modello gia' scaricato."""
    return [tier for tier in MODELS if is_model_downloaded(tier)]
