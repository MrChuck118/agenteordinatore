"""
logger.py — Configurazione centralizzata del logging.

Espone due logger:
  - get_app_logger(): eventi generali (download, classificazioni, errori, etc.)
                     scrive su %LOCALAPPDATA%/AgentOrdinatore/logs/app.log
                     con rotazione automatica (max 5 file da 1 MB ciascuno).
  - get_moves_logger(): solo spostamenti/copie file, formato leggibile,
                        scrive su %LOCALAPPDATA%/AgentOrdinatore/logs/moves.log
                        senza rotazione (cronologia completa).

Uso tipico:
    from logger import get_app_logger, get_moves_logger
    log = get_app_logger()
    log.info("Download avviato per tier=%s", tier)
    moves = get_moves_logger()
    moves.info("MOVE | %s -> %s", source, dest)
"""

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from platformdirs import user_data_dir


_APP_LOGGER_NAME = "AgentOrdinatore"
_MOVES_LOGGER_NAME = "AgentOrdinatore.moves"

_app_logger: logging.Logger | None = None
_moves_logger: logging.Logger | None = None


def _get_logs_dir() -> Path:
    d = Path(user_data_dir("AgentOrdinatore", appauthor=False)) / "logs"
    d.mkdir(parents=True, exist_ok=True)
    return d


def get_logs_dir() -> Path:
    """Path della cartella log (per il bottone 'Apri cartella log' in GUI)."""
    return _get_logs_dir()


def get_app_logger() -> logging.Logger:
    """Logger principale per eventi generali. Idempotente."""
    global _app_logger
    if _app_logger is not None:
        return _app_logger

    logger = logging.getLogger(_APP_LOGGER_NAME)
    logger.setLevel(logging.INFO)
    logger.propagate = False

    if not logger.handlers:
        log_file = _get_logs_dir() / "app.log"
        handler = RotatingFileHandler(
            log_file,
            maxBytes=1_000_000,   # 1 MB
            backupCount=5,
            encoding="utf-8",
        )
        formatter = logging.Formatter(
            fmt="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    _app_logger = logger
    return logger


def get_moves_logger() -> logging.Logger:
    """Logger dedicato agli spostamenti/copie file. Idempotente."""
    global _moves_logger
    if _moves_logger is not None:
        return _moves_logger

    logger = logging.getLogger(_MOVES_LOGGER_NAME)
    logger.setLevel(logging.INFO)
    logger.propagate = False  # non propagare al root, evita duplicati

    if not logger.handlers:
        log_file = _get_logs_dir() / "moves.log"
        handler = logging.FileHandler(log_file, encoding="utf-8")
        # Formato semplice e grep-friendly
        formatter = logging.Formatter(
            fmt="%(asctime)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    _moves_logger = logger
    return logger


def set_debug_mode(enabled: bool):
    """Alza il livello di logging dell'app a DEBUG (solo app_logger)."""
    logger = get_app_logger()
    logger.setLevel(logging.DEBUG if enabled else logging.INFO)
