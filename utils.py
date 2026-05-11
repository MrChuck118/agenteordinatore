"""
utils.py — Operazioni su disco per l'agente di organizzazione file.

Funzionalità:
  - Scansione di una cartella per elencare i file presenti.
  - Creazione sicura di sottocartelle di destinazione.
  - Spostamento file con gestione automatica dei conflitti (timestamp).
  - Rinomina sicura di cartelle con logging e gestione conflitti.
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

_GENERIC_FOLDER_NAMES = {
    "backup",
    "cartella",
    "desktop",
    "misc",
    "new folder",
    "nuova cartella",
    "roba",
    "temp",
    "temporary",
    "tmp",
    "varie",
    "various",
}

_PROJECT_MARKERS = {
    ".git",
    ".hg",
    ".svn",
    "Cargo.toml",
    "composer.json",
    "go.mod",
    "node_modules",
    "package-lock.json",
    "package.json",
    "poetry.lock",
    "pyproject.toml",
    "requirements.txt",
    "src",
    "yarn.lock",
}

_PROJECT_EXTENSION_MARKERS = {
    ".csproj",
    ".sln",
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


def sanitize_folder_name(name: str, fallback: str = "Cartella") -> str:
    """Rende sicuro un nome cartella singolo, senza sottopercorsi."""
    return sanitize_category(name, fallback=fallback, max_depth=1)


def is_generic_folder_name(name: str) -> bool:
    """Ritorna True se il nome sembra generico o poco informativo."""
    text = re.sub(r"\s+", " ", str(name or "").strip().lower())
    if not text:
        return True
    if text in _GENERIC_FOLDER_NAMES:
        return True

    base = re.sub(r"[\s._-]*\(?\d+\)?$", "", text).strip()
    if base in _GENERIC_FOLDER_NAMES:
        return True

    compact = re.sub(r"[^a-z0-9]+", "", text)
    if not compact or compact.isdigit():
        return True
    return len(compact) <= 2


def detect_project_markers(folder: Path) -> list[str]:
    """Trova marker che fanno pensare a un progetto intenzionale."""
    markers: list[str] = []
    for marker in sorted(_PROJECT_MARKERS):
        if (folder / marker).exists():
            markers.append(marker)
    for item in sorted(folder.iterdir()):
        ext = item.suffix.lower()
        if item.is_file() and ext in _PROJECT_EXTENSION_MARKERS and ext not in markers:
            markers.append(ext)
    return markers


def find_nested_folder_pair(folders: list[Path]) -> tuple[Path, Path] | None:
    """
    Ritorna una coppia (parent, child) se due cartelle selezionate sono annidate.

    Serve a bloccare swap/multiswap rischiosi tra una cartella e una sua
    sottocartella, caso in cui i file potrebbero essere campionati/spostati in
    modo confuso.
    """
    resolved: list[tuple[Path, Path]] = []
    for folder in folders:
        try:
            resolved_path = folder.resolve()
        except OSError:
            resolved_path = folder.absolute()
        resolved.append((folder, resolved_path))

    for idx, (left_original, left_resolved) in enumerate(resolved):
        for right_original, right_resolved in resolved[idx + 1:]:
            if left_resolved == right_resolved:
                continue
            if right_resolved.is_relative_to(left_resolved):
                return left_original, right_original
            if left_resolved.is_relative_to(right_resolved):
                return right_original, left_original
    return None


def build_folder_profile(folder: Path, sample_limit: int = 30) -> dict:
    """
    Costruisce un profilo leggero di una cartella per il suggerimento nome.

    Il profilo usa solo metadati locali: nome file, estensioni, dimensioni e
    marker di progetto. Non legge il contenuto dei file.
    """
    files = scan_folder(folder)
    extension_counts: dict[str, int] = {}
    sample_files: list[str] = []
    total_size = 0

    for entry in files:
        path = entry["path"]
        total_size += entry["size"]
        ext = path.suffix.lower() or "[senza estensione]"
        extension_counts[ext] = extension_counts.get(ext, 0) + 1
        if len(sample_files) < sample_limit:
            sample_files.append(path.name)

    top_extensions = sorted(
        extension_counts.items(),
        key=lambda item: (-item[1], item[0]),
    )[:10]

    markers = detect_project_markers(folder)
    return {
        "path": str(folder),
        "current_name": folder.name,
        "file_count": len(files),
        "total_size": total_size,
        "total_size_str": format_size(total_size),
        "sample_files": sample_files,
        "extensions": dict(top_extensions),
        "weak_name": is_generic_folder_name(folder.name),
        "project_markers": markers,
        "protected": bool(markers),
    }


def build_folder_profile_from_names(
    folder: Path,
    file_names: list[str],
    sample_limit: int = 30,
) -> dict:
    """
    Costruisce un profilo cartella partendo da una lista di nomi file prevista.

    Serve per valutare un eventuale nuovo nome dopo uno swap, prima che tutte le
    operazioni siano gia' state applicate sul disco.
    """
    clean_names = [
        str(name)
        for name in file_names
        if str(name).strip() and not Path(str(name)).name.startswith(".")
    ]
    extension_counts: dict[str, int] = {}
    sample_files: list[str] = []

    for name in clean_names:
        path = Path(name)
        ext = path.suffix.lower() or "[senza estensione]"
        extension_counts[ext] = extension_counts.get(ext, 0) + 1
        if len(sample_files) < sample_limit:
            sample_files.append(path.name)

    top_extensions = sorted(
        extension_counts.items(),
        key=lambda item: (-item[1], item[0]),
    )[:10]

    markers = detect_project_markers(folder)
    return {
        "path": str(folder),
        "current_name": folder.name,
        "file_count": len(clean_names),
        "total_size": 0,
        "total_size_str": "n/d",
        "sample_files": sample_files,
        "extensions": dict(top_extensions),
        "weak_name": is_generic_folder_name(folder.name),
        "project_markers": markers,
        "protected": bool(markers),
        "projected": True,
    }


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


def _resolve_folder_conflict(destination: Path) -> Path:
    """Ritorna una destinazione cartella libera senza sovrascrivere."""
    if not destination.exists():
        return destination

    base = destination.name
    parent = destination.parent
    for idx in range(2, 1000):
        candidate = parent / f"{base}_{idx}"
        if not candidate.exists():
            return candidate

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    return parent / f"{base}_{timestamp}"


def rename_folder_safe(source: Path, new_name: str) -> Path:
    """
    Rinomina una cartella in modo sicuro nella stessa cartella padre.

    Il nome viene sanitizzato, i conflitti vengono risolti con suffisso e
    l'azione reale viene registrata in moves.log come RENAME_FOLDER.
    """
    if not source.is_dir():
        raise FileNotFoundError(f"La cartella '{source}' non esiste.")

    safe_name = sanitize_folder_name(new_name, fallback=source.name)
    if safe_name.lower() == source.name.lower():
        return source

    destination = _resolve_folder_conflict(source.parent / safe_name)
    try:
        source.rename(destination)
    except Exception:
        _log.exception("RENAME_FOLDER failed: %s -> %s", source, destination)
        raise

    _moves.info("RENAME_FOLDER | %s -> %s", source, destination)
    return destination


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
