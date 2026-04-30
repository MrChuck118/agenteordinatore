"""
utils.py — Operazioni su disco per l'agente di organizzazione file.

Funzionalità:
  - Scansione di una cartella per elencare i file presenti.
  - Creazione sicura di sottocartelle di destinazione.
  - Spostamento file con gestione automatica dei conflitti (timestamp).
"""

from pathlib import Path
from datetime import datetime
import re
import shutil

from logger import get_app_logger, get_moves_logger

_log = get_app_logger()
_moves = get_moves_logger()

_WINDOWS_RESERVED_NAMES = {
    "CON", "PRN", "AUX", "NUL",
    *(f"COM{i}" for i in range(1, 10)),
    *(f"LPT{i}" for i in range(1, 10)),
}


def scan_folder(folder: Path) -> list[dict]:
    """
    Scansiona una cartella e restituisce la lista dei file con dimensione (non ricorsiva).

    Args:
        folder: Percorso della cartella da scansionare.

    Returns:
        Lista di dizionari {"path": Path, "size": int} per ogni file trovato.
        Le sottocartelle e i file nascosti (che iniziano con '.') vengono ignorati.
    """
    if not folder.is_dir():
        raise FileNotFoundError(f"La cartella '{folder}' non esiste.")

    return [
        {"path": item, "size": item.stat().st_size}
        for item in sorted(folder.iterdir())
        if item.is_file() and not item.name.startswith(".")
    ]


def format_size(size_bytes: int) -> str:
    """Formatta una dimensione in byte in formato leggibile (es: '1.2 MB')."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 ** 2:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 ** 3:
        return f"{size_bytes / 1024 ** 2:.1f} MB"
    else:
        return f"{size_bytes / 1024 ** 3:.1f} GB"


def sanitize_category(category: str, fallback: str = "Altro", max_depth: int = 2) -> str:
    """
    Converte una categoria proposta dall'AI in un path relativo sicuro.

    Mantiene al massimo max_depth livelli, rimuove traversal/assoluti e sostituisce
    caratteri non validi su Windows. Il valore restituito e' sempre relativo.
    """
    text = str(category or "").strip()
    if not text:
        return fallback

    # Blocca subito path assoluti Windows/UNC/POSIX e home expansion.
    if (
        re.match(r"^[A-Za-z]:[\\/]", text)
        or text.startswith(("/", "\\", "~"))
    ):
        _log.warning("Categoria AI assoluta/non sicura ignorata: %r", text)
        return fallback

    parts: list[str] = []
    for raw_part in text.replace("\\", "/").split("/"):
        part = raw_part.strip()
        if not part or part in {".", ".."}:
            continue

        part = re.sub(r'[<>:"|?*\x00-\x1f]', " ", part)
        part = re.sub(r"\s+", " ", part).strip(" .")
        if not part:
            continue

        reserved_base = part.split(".", 1)[0].upper()
        if reserved_base in _WINDOWS_RESERVED_NAMES:
            part = f"{part}_"

        parts.append(part[:80])
        if len(parts) >= max_depth:
            break

    if not parts:
        _log.warning("Categoria AI vuota/non sicura ignorata: %r", text)
        return fallback

    return "/".join(parts)


def ensure_folder(folder: Path) -> Path:
    """
    Crea una cartella (e tutte le cartelle intermedie) se non esiste già.

    Args:
        folder: Percorso della cartella da creare.

    Returns:
        Il Path della cartella (esistente o appena creata).
    """
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def _resolve_conflict(destination: Path) -> Path:
    """
    Se il file di destinazione esiste già, genera un nuovo nome
    aggiungendo un timestamp prima dell'estensione.

    Esempio: relazione.pdf → relazione_20260318_153042.pdf

    Args:
        destination: Percorso completo del file di destinazione.

    Returns:
        Un Path univoco (originale se libero, con timestamp se occupato).
    """
    if not destination.exists():
        return destination

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    stem = destination.stem        # nome senza estensione
    suffix = destination.suffix    # estensione (es. ".pdf")
    new_name = f"{stem}_{timestamp}{suffix}"

    return destination.parent / new_name


def move_file(source: Path, dest_folder: Path) -> Path:
    """
    Sposta un file nella cartella di destinazione.
    Se esiste già un file con lo stesso nome, aggiunge un timestamp.

    Args:
        source:      Percorso del file da spostare.
        dest_folder: Cartella di destinazione.

    Returns:
        Il Path finale del file spostato.
    """
    ensure_folder(dest_folder)

    destination = _resolve_conflict(dest_folder / source.name)
    try:
        shutil.move(str(source), str(destination))
    except Exception:
        _log.exception("MOVE failed: %s -> %s", source, destination)
        raise

    _moves.info("MOVE | %s -> %s", source, destination)
    return destination


def copy_file(source: Path, dest_folder: Path) -> Path:
    """
    Copia un file nella cartella di destinazione.
    Se esiste già un file con lo stesso nome, aggiunge un timestamp.

    Args:
        source:      Percorso del file da copiare.
        dest_folder: Cartella di destinazione.

    Returns:
        Il Path finale del file copiato.
    """
    ensure_folder(dest_folder)

    destination = _resolve_conflict(dest_folder / source.name)
    try:
        shutil.copy2(str(source), str(destination))
    except Exception:
        _log.exception("COPY failed: %s -> %s", source, destination)
        raise

    _moves.info("COPY | %s -> %s", source, destination)
    return destination
