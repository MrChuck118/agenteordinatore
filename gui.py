"""
gui.py — Interfaccia grafica desktop per Agent Ordinatore.

Uso:
    python gui.py

Richiede PySide6: pip install PySide6
"""

import sys

# Quando lanciato con pythonw.exe (no console), sys.stdout/stderr sono None.
# huggingface_hub e tqdm scrivono progress su stderr → crash con
# 'NoneType' object has no attribute 'write'. Reindiriziamo a un file di log
# cosi' nulla va perso (warning librerie, tqdm, ecc.).
if sys.stdout is None or sys.stderr is None:
    from logger import get_logs_dir
    _libs_log = open(get_logs_dir() / "libs.log", "a", encoding="utf-8", buffering=1)
    if sys.stdout is None:
        sys.stdout = _libs_log
    if sys.stderr is None:
        sys.stderr = _libs_log

import json
from pathlib import Path
from datetime import datetime

from platformdirs import user_data_dir

from logger import get_app_logger, get_logs_dir
log = get_app_logger()

from PySide6.QtWidgets import (  # type: ignore
    QApplication, QMainWindow, QTabWidget, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QFileDialog, QTableWidget, QTableWidgetItem,
    QProgressBar, QRadioButton, QButtonGroup, QHeaderView, QAbstractItemView,
    QMessageBox, QTreeWidget, QTreeWidgetItem, QSizePolicy, QLineEdit,
    QCheckBox, QGroupBox,
)
from PySide6.QtCore import Qt, Signal, QThread, QTimer, QUrl  # type: ignore
from PySide6.QtGui import QBrush, QColor, QDragEnterEvent, QDropEvent, QFont, QIcon, QDesktopServices  # type: ignore

from utils import (
    scan_folder, move_file, copy_file, format_size, sanitize_category,
    build_folder_profile, build_folder_profile_from_names, rename_folder_safe,
)
from brain import (
    classify_file, classify_for_swap, classify_for_multi_swap,
    suggest_folder_rename, init_classifier, unload_model,
)
from config import (
    load_config, save_config, get_theme, set_theme, get_selected_tier,
    set_selected_tier, is_folder_rename_allowed, set_folder_rename_allowed,
)
from model_manager import (
    MODELS, is_model_downloaded, download_model, delete_model,
    get_downloaded_models, get_models_dir
)
from hardware import detect_hardware, get_available_tiers


# ── Percorsi persistenza ──────────────────────────────────────────────
APP_DATA_DIR = Path(user_data_dir("AgentOrdinatore", appauthor=False))
HISTORY_FILE = APP_DATA_DIR / "history.json"
_LEGACY_HISTORY_FILE = Path(__file__).parent / "history.json"


def _resource_path(relative_name: str) -> Path:
    """Ritorna il path di una risorsa sia in sviluppo sia in build PyInstaller."""
    candidates: list[Path] = []
    frozen_base = getattr(sys, "_MEIPASS", None)
    if frozen_base:
        candidates.append(Path(frozen_base) / relative_name)
    if getattr(sys, "frozen", False):
        candidates.append(Path(sys.executable).parent / relative_name)
    candidates.append(Path(__file__).resolve().parent / relative_name)

    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[0]


# ── Utilità persistenza ───────────────────────────────────────────────

def load_history() -> list[dict]:
    if HISTORY_FILE.exists():
        try:
            return json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    if _LEGACY_HISTORY_FILE.exists():
        try:
            return json.loads(_LEGACY_HISTORY_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return []


def save_history(history: list[dict]):
    try:
        HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
        HISTORY_FILE.write_text(json.dumps(history, indent=2, ensure_ascii=False), encoding="utf-8")
    except Exception:
        log.exception("Salvataggio cronologia fallito: %s", HISTORY_FILE)


# ── Temi QSS ─────────────────────────────────────────────────────────

DARK_THEME = """
/* ── Base ── */
QMainWindow, QWidget {
    background-color: #0a0f0a;
    color: #e0ffe0;
    font-family: "Segoe UI";
    font-size: 13px;
}

/* ── Tabs ── */
QTabWidget::pane {
    border: 1px solid #1a3a1a;
    background-color: #0a0f0a;
    border-radius: 4px;
}
QTabBar::tab {
    background-color: transparent;
    color: #4a7a4a;
    padding: 8px 20px;
    border-bottom: 2px solid transparent;
    font-family: "Segoe UI";
}
QTabBar::tab:selected {
    color: #00ff41;
    border-bottom: 2px solid #00ff41;
    font-weight: bold;
}
QTabBar::tab:hover:!selected {
    color: #e0ffe0;
}

/* ── Bottoni secondari ── */
QPushButton {
    background-color: transparent;
    color: #00ff41;
    border: 1px solid #1a3a1a;
    padding: 8px 18px;
    border-radius: 6px;
    font-family: "Segoe UI";
    font-weight: bold;
}
QPushButton:hover {
    border-color: #00ff41;
    background-color: rgba(0, 255, 65, 0.05);
}
QPushButton:pressed {
    background-color: rgba(0, 255, 65, 0.12);
}
QPushButton:disabled {
    background-color: #0f1a0f;
    color: #2a4a2a;
    border-color: #1a3a1a;
}

/* ── Bottoni primari (accent) ── */
QPushButton#accentBtn {
    background-color: #00ff41;
    color: #0a0f0a;
    border: none;
    font-family: "Segoe UI";
    font-weight: bold;
}
QPushButton#accentBtn:hover {
    background-color: #00cc33;
}
QPushButton#accentBtn:disabled {
    background-color: #1a3a1a;
    color: #2a4a2a;
}

/* ── Campo percorso ── */
QLineEdit {
    background-color: #0f1a0f;
    color: #e0ffe0;
    border: 1px solid #1a3a1a;
    padding: 6px 10px;
    border-radius: 4px;
    font-family: "Courier New";
}

/* ── Tabella dati ── */
QTableWidget {
    background-color: #0a0f0a;
    alternate-background-color: #0d160d;
    color: #e0ffe0;
    gridline-color: #1a3a1a;
    border: 1px solid #1a3a1a;
    border-radius: 4px;
    selection-background-color: rgba(0, 255, 65, 0.1);
    font-family: "Courier New";
    font-size: 12px;
}
QTableWidget::item {
    padding: 4px;
}
QHeaderView::section {
    background-color: #0f1a0f;
    color: #4a7a4a;
    padding: 6px;
    border: none;
    border-right: 1px solid #1a3a1a;
    border-bottom: 1px solid #1a3a1a;
    font-family: "Segoe UI";
    font-weight: 500;
}

/* ── Barra di progresso ── */
QProgressBar {
    border: 1px solid #1a3a1a;
    border-radius: 6px;
    background-color: #0f1a0f;
    text-align: center;
    color: #00ff41;
    height: 22px;
    font-family: "Courier New";
    font-size: 11px;
}
QProgressBar::chunk {
    background-color: #00ff41;
    border-radius: 5px;
}

/* ── Radio button ── */
QRadioButton {
    color: #e0ffe0;
    spacing: 6px;
    font-family: "Segoe UI";
}
QRadioButton::indicator {
    width: 16px; height: 16px;
    border: 2px solid #1a3a1a;
    border-radius: 9px;
    background-color: #0f1a0f;
}
QRadioButton::indicator:checked {
    background-color: #00ff41;
    border-color: #00ff41;
}

/* ── Checkbox ── */
QCheckBox {
    color: #e0ffe0;
    spacing: 6px;
    font-family: "Segoe UI";
}
QCheckBox::indicator {
    width: 16px; height: 16px;
    border: 2px solid #1a3a1a;
    border-radius: 3px;
    background-color: #0f1a0f;
}
QCheckBox::indicator:checked {
    background-color: #00ff41;
    border-color: #00ff41;
}

/* ── GroupBox ── */
QGroupBox {
    border: 1px solid #1a3a1a;
    border-radius: 6px;
    margin-top: 12px;
    padding-top: 16px;
    font-family: "Segoe UI";
    font-weight: bold;
    color: #00ff41;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 6px;
}

/* ── Tree (cronologia) ── */
QTreeWidget {
    background-color: #0a0f0a;
    alternate-background-color: #0d160d;
    color: #e0ffe0;
    border: 1px solid #1a3a1a;
    border-radius: 4px;
    font-family: "Courier New";
    font-size: 12px;
}
QTreeWidget::item {
    padding: 4px;
}
QTreeWidget::item:selected {
    background-color: rgba(0, 255, 65, 0.1);
}

/* ── Drop area ── */
QLabel#dropArea {
    border: 2px dashed #1a3a1a;
    border-radius: 10px;
    background-color: #0f1a0f;
    color: #4a7a4a;
    font-family: "Segoe UI";
    font-size: 14px;
    padding: 30px;
}
QLabel#dropArea[dragOver="true"] {
    border-color: #00ff41;
    background-color: rgba(0, 255, 65, 0.05);
    color: #00ff41;
}

/* ── Status label ── */
QLabel#statusLabel {
    font-family: "Courier New";
    font-size: 12px;
    color: #4a7a4a;
}

/* ── Scrollbar ── */
QScrollBar:vertical {
    background-color: #0f1a0f;
    width: 10px;
    border: none;
}
QScrollBar::handle:vertical {
    background-color: #1a3a1a;
    border-radius: 5px;
    min-height: 20px;
}
QScrollBar::handle:vertical:hover {
    background-color: #2a5a2a;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}
QScrollBar:horizontal {
    background-color: #0f1a0f;
    height: 10px;
    border: none;
}
QScrollBar::handle:horizontal {
    background-color: #1a3a1a;
    border-radius: 5px;
    min-width: 20px;
}
QScrollBar::handle:horizontal:hover {
    background-color: #2a5a2a;
}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    width: 0px;
}
"""

LIGHT_THEME = """
/* ── Base ── */
QMainWindow, QWidget {
    background-color: #e4e9e4;
    color: #0a1a0a;
    font-family: "Segoe UI";
    font-size: 13px;
}

/* ── Tabs ── */
QTabWidget::pane {
    border: 1px solid #b0c8b0;
    background-color: #e4e9e4;
    border-radius: 4px;
}
QTabBar::tab {
    background-color: transparent;
    color: #6a9a6a;
    padding: 8px 20px;
    border-bottom: 2px solid transparent;
    font-family: "Segoe UI";
}
QTabBar::tab:selected {
    color: #0a8a3a;
    border-bottom: 2px solid #0a8a3a;
    font-weight: bold;
}
QTabBar::tab:hover:!selected {
    color: #0a1a0a;
}

/* ── Bottoni secondari ── */
QPushButton {
    background-color: transparent;
    color: #0a8a3a;
    border: 1px solid #b0c8b0;
    padding: 8px 18px;
    border-radius: 6px;
    font-family: "Segoe UI";
    font-weight: bold;
}
QPushButton:hover {
    border-color: #0a8a3a;
    background-color: rgba(10, 138, 58, 0.05);
}
QPushButton:pressed {
    background-color: rgba(10, 138, 58, 0.12);
}
QPushButton:disabled {
    background-color: #eef2ee;
    color: #90b090;
    border-color: #b0c8b0;
}

/* ── Bottoni primari (accent) ── */
QPushButton#accentBtn {
    background-color: #0a8a3a;
    color: #ffffff;
    border: none;
    font-family: "Segoe UI";
    font-weight: bold;
}
QPushButton#accentBtn:hover {
    background-color: #087030;
}
QPushButton#accentBtn:disabled {
    background-color: #b0c8b0;
    color: #90b090;
}

/* ── Campo percorso ── */
QLineEdit {
    background-color: #eef2ee;
    color: #0a1a0a;
    border: 1px solid #b0c8b0;
    padding: 6px 10px;
    border-radius: 4px;
    font-family: "Courier New";
}

/* ── Tabella dati ── */
QTableWidget {
    background-color: #e4e9e4;
    alternate-background-color: #e8ede8;
    color: #0a1a0a;
    gridline-color: #b0c8b0;
    border: 1px solid #b0c8b0;
    border-radius: 4px;
    selection-background-color: rgba(10, 138, 58, 0.1);
    font-family: "Courier New";
    font-size: 12px;
}
QTableWidget::item {
    padding: 4px;
}
QHeaderView::section {
    background-color: #eef2ee;
    color: #6a9a6a;
    padding: 6px;
    border: none;
    border-right: 1px solid #b0c8b0;
    border-bottom: 1px solid #b0c8b0;
    font-family: "Segoe UI";
    font-weight: 500;
}

/* ── Barra di progresso ── */
QProgressBar {
    border: 1px solid #b0c8b0;
    border-radius: 6px;
    background-color: #eef2ee;
    text-align: center;
    color: #0a8a3a;
    height: 22px;
    font-family: "Courier New";
    font-size: 11px;
}
QProgressBar::chunk {
    background-color: #0a8a3a;
    border-radius: 5px;
}

/* ── Radio button ── */
QRadioButton {
    color: #0a1a0a;
    spacing: 6px;
    font-family: "Segoe UI";
}
QRadioButton::indicator {
    width: 16px; height: 16px;
    border: 2px solid #b0c8b0;
    border-radius: 9px;
    background-color: #eef2ee;
}
QRadioButton::indicator:checked {
    background-color: #0a8a3a;
    border-color: #0a8a3a;
}

/* ── Checkbox ── */
QCheckBox {
    color: #0a1a0a;
    spacing: 6px;
    font-family: "Segoe UI";
}
QCheckBox::indicator {
    width: 16px; height: 16px;
    border: 2px solid #b0c8b0;
    border-radius: 3px;
    background-color: #eef2ee;
}
QCheckBox::indicator:checked {
    background-color: #0a8a3a;
    border-color: #0a8a3a;
}

/* ── GroupBox ── */
QGroupBox {
    border: 1px solid #b0c8b0;
    border-radius: 6px;
    margin-top: 12px;
    padding-top: 16px;
    font-family: "Segoe UI";
    font-weight: bold;
    color: #0a8a3a;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 6px;
}

/* ── Tree (cronologia) ── */
QTreeWidget {
    background-color: #e4e9e4;
    alternate-background-color: #e8ede8;
    color: #0a1a0a;
    border: 1px solid #b0c8b0;
    border-radius: 4px;
    font-family: "Courier New";
    font-size: 12px;
}
QTreeWidget::item {
    padding: 4px;
}
QTreeWidget::item:selected {
    background-color: rgba(10, 138, 58, 0.1);
}

/* ── Drop area ── */
QLabel#dropArea {
    border: 2px dashed #b0c8b0;
    border-radius: 10px;
    background-color: #eef2ee;
    color: #6a9a6a;
    font-family: "Segoe UI";
    font-size: 14px;
    padding: 30px;
}
QLabel#dropArea[dragOver="true"] {
    border-color: #0a8a3a;
    background-color: rgba(10, 138, 58, 0.06);
    color: #0a8a3a;
}

/* ── Status label ── */
QLabel#statusLabel {
    font-family: "Courier New";
    font-size: 12px;
    color: #6a9a6a;
}

/* ── Scrollbar ── */
QScrollBar:vertical {
    background-color: #e4e9e4;
    width: 10px;
    border: none;
}
QScrollBar::handle:vertical {
    background-color: #b0c8b0;
    border-radius: 5px;
    min-height: 20px;
}
QScrollBar::handle:vertical:hover {
    background-color: #90a890;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}
QScrollBar:horizontal {
    background-color: #e4e9e4;
    height: 10px;
    border: none;
}
QScrollBar::handle:horizontal {
    background-color: #b0c8b0;
    border-radius: 5px;
    min-width: 20px;
}
QScrollBar::handle:horizontal:hover {
    background-color: #90a890;
}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    width: 0px;
}
"""


# ── Worker threads ────────────────────────────────────────────────────

class OrganizeAnalyzeWorker(QThread):
    """Analizza (classifica) i file di una cartella in background."""
    progress = Signal(int, str, str, str, int)  # index, filename, size_str, category, size_bytes
    finished = Signal()
    error = Signal(str)

    def __init__(self, folder: Path):
        super().__init__()
        self.folder = folder

    def run(self):
        try:
            files = scan_folder(self.folder)
            log.info("Analisi Organizza avviata: cartella=%s file=%d", self.folder, len(files))
            for i, entry in enumerate(files):
                if self.isInterruptionRequested():
                    log.info("Analisi Organizza interrotta")
                    self.error.emit("Operazione interrotta.")
                    return
                fp = entry["path"]
                size = entry["size"]
                size_str = format_size(size)
                category = classify_file(fp.name, size_str)
                self.progress.emit(i, fp.name, size_str, category, size)
            log.info("Analisi Organizza completata: %d file", len(files))
            self.finished.emit()
        except Exception as e:
            log.exception("Analisi Organizza fallita")
            self.error.emit(str(e))


class OrganizeExecuteWorker(QThread):
    """Sposta/copia i file selezionati in background."""
    progress = Signal(int, str)  # index, dest_path
    finished = Signal(int)       # count
    error = Signal(int, str)     # index, error_msg

    def __init__(self, items: list[dict], target_folder: Path, use_copy: bool):
        super().__init__()
        self.items = items
        self.target_folder = target_folder
        self.use_copy = use_copy

    def run(self):
        transfer_fn = copy_file if self.use_copy else move_file
        action = "COPY" if self.use_copy else "MOVE"
        log.info("Esecuzione Organizza avviata: %s %d file -> %s", action, len(self.items), self.target_folder)
        count = 0
        for i, item in enumerate(self.items):
            if self.isInterruptionRequested():
                log.info("Esecuzione Organizza interrotta: %d/%d riusciti", count, len(self.items))
                self.finished.emit(count)
                return
            try:
                source = Path(item["path"])
                dest_folder = self.target_folder / sanitize_category(item["category"])
                final = transfer_fn(source, dest_folder)
                self.progress.emit(i, str(final))
                count += 1
            except Exception as e:
                log.exception("Esecuzione Organizza: errore su %s", item.get("path"))
                self.error.emit(i, str(e))
        log.info("Esecuzione Organizza completata: %d/%d riusciti", count, len(self.items))
        self.finished.emit(count)


class SwapAnalyzeWorker(QThread):
    """Analizza i file di due cartelle per lo swap."""
    progress = Signal(int, str, str, str, str, str)  # idx, filename, size_str, current_folder, destination_label, origin("A"/"B")
    finished = Signal()
    error = Signal(str)

    def __init__(self, folder_a: Path, folder_b: Path):
        super().__init__()
        self.folder_a = folder_a
        self.folder_b = folder_b

    def run(self):
        try:
            files_a = scan_folder(self.folder_a)
            files_b = scan_folder(self.folder_b)
            log.info("Analisi Swap avviata: A=%s (%d file) B=%s (%d file)",
                     self.folder_a, len(files_a), self.folder_b, len(files_b))

            fa_name = self.folder_a.name
            fb_name = self.folder_b.name
            fa_filenames = [e["path"].name for e in files_a]
            fb_filenames = [e["path"].name for e in files_b]

            idx = 0
            for entry in files_a:
                if self.isInterruptionRequested():
                    log.info("Analisi Swap interrotta")
                    self.error.emit("Operazione interrotta.")
                    return
                fp = entry["path"]
                size_str = format_size(entry["size"])
                target_key = _path_key(fp)
                fa_sample = [
                    e["path"].name for e in files_a
                    if _path_key(e["path"]) != target_key
                ]
                dest = classify_for_swap(fp.name, size_str, fa_name, fb_name, fa_sample, fb_filenames)
                if dest is None or dest == "A":
                    dest_label = f"Resta in {fa_name}"
                else:
                    dest_label = fb_name
                self.progress.emit(idx, fp.name, size_str, fa_name, dest_label, "A")
                idx += 1

            for entry in files_b:
                if self.isInterruptionRequested():
                    log.info("Analisi Swap interrotta")
                    self.error.emit("Operazione interrotta.")
                    return
                fp = entry["path"]
                size_str = format_size(entry["size"])
                target_key = _path_key(fp)
                fb_sample = [
                    e["path"].name for e in files_b
                    if _path_key(e["path"]) != target_key
                ]
                dest = classify_for_swap(fp.name, size_str, fa_name, fb_name, fa_filenames, fb_sample)
                if dest is None or dest == "B":
                    dest_label = f"Resta in {fb_name}"
                else:
                    dest_label = fa_name
                self.progress.emit(idx, fp.name, size_str, fb_name, dest_label, "B")
                idx += 1

            log.info("Analisi Swap completata: %d file analizzati", idx)
            self.finished.emit()
        except Exception as e:
            log.exception("Analisi Swap fallita")
            self.error.emit(str(e))


class SwapExecuteWorker(QThread):
    """Esegue lo swap (sposta/copia) dei file selezionati."""
    progress = Signal(int, str)
    finished = Signal(int)
    error = Signal(int, str)

    def __init__(self, items: list[dict], folder_a: Path, folder_b: Path, use_copy: bool):
        super().__init__()
        self.items = items
        self.folder_a = folder_a
        self.folder_b = folder_b
        self.use_copy = use_copy

    def run(self):
        transfer_fn = copy_file if self.use_copy else move_file
        action = "COPY" if self.use_copy else "MOVE"
        log.info("Esecuzione Swap avviata: %s %d file (A=%s B=%s)",
                 action, len(self.items), self.folder_a, self.folder_b)
        count = 0
        for i, item in enumerate(self.items):
            if self.isInterruptionRequested():
                log.info("Esecuzione Swap interrotta: %d/%d riusciti", count, len(self.items))
                self.finished.emit(count)
                return
            try:
                source = Path(item["path"])
                dest_folder = self.folder_b if item["origin"] == "A" else self.folder_a
                final = transfer_fn(source, dest_folder)
                self.progress.emit(i, str(final))
                count += 1
            except Exception as e:
                log.exception("Esecuzione Swap: errore su %s", item.get("path"))
                self.error.emit(i, str(e))
        log.info("Esecuzione Swap completata: %d/%d riusciti", count, len(self.items))
        self.finished.emit(count)


class MultiSwapAnalyzeWorker(QThread):
    """Analizza i file di N cartelle per il multi-swap (torneo a chunk)."""
    # idx, filename, size_str, current_folder_name, dest_folder_name, origin_idx, dest_idx, stays
    progress = Signal(int, str, str, str, str, int, int, bool)
    finished = Signal()
    error = Signal(str)

    def __init__(self, folders: list[Path]):
        super().__init__()
        self.folders = folders

    def run(self):
        try:
            # Scansiona tutte le cartelle una sola volta
            all_files: list[list[dict]] = []
            for folder in self.folders:
                all_files.append(scan_folder(folder))

            counts = [len(f) for f in all_files]
            log.info(
                "Analisi MultiSwap avviata: %d cartelle, %d file totali (%s)",
                len(self.folders), sum(counts),
                ", ".join(f"{p.name}={c}" for p, c in zip(self.folders, counts)),
            )

            # Pre-calcola i sample completi (lista di nomi) per ogni cartella
            sample_by_folder: list[list[str]] = [
                [e["path"].name for e in files] for files in all_files
            ]

            idx_emit = 0
            stayed_count = 0
            move_count = 0
            for origin_idx, files in enumerate(all_files):
                origin_folder = self.folders[origin_idx]
                origin_name = origin_folder.name

                for entry in files:
                    if self.isInterruptionRequested():
                        log.info("Analisi MultiSwap interrotta")
                        self.error.emit("Operazione interrotta.")
                        return

                    fp: Path = entry["path"]
                    size_str = format_size(entry["size"])

                    # Costruisci folder_specs escludendo IL FILE TARGET dalla cartella di
                    # origine, confrontando per path completo (non per nome).
                    target_path_str = _path_key(fp)
                    folder_specs: list[dict] = []
                    for fi, folder in enumerate(self.folders):
                        names = sample_by_folder[fi]
                        if fi == origin_idx:
                            # Esclusione per path: prendi i nomi dei file la cui path
                            # completa risolta non coincide con il target
                            filtered = []
                            for e in all_files[fi]:
                                if _path_key(e["path"]) == target_path_str:
                                    continue
                                filtered.append(e["path"].name)
                            names = filtered
                        folder_specs.append({
                            "name": folder.name,
                            "path": str(folder),
                            "files": names,
                        })

                    dest_idx = classify_for_multi_swap(
                        fp.name, size_str, folder_specs,
                        target_path=target_path_str,
                    )

                    stays = (dest_idx == origin_idx)
                    if stays:
                        stayed_count += 1
                        dest_label = f"Resta in {origin_name}"
                        log.debug(
                            "MultiSwap: '%s' resta in '%s' (origin == winner)",
                            fp.name, origin_name,
                        )
                    else:
                        move_count += 1
                        dest_label = self.folders[dest_idx].name

                    self.progress.emit(
                        idx_emit, fp.name, size_str, origin_name, dest_label,
                        origin_idx, dest_idx, stays,
                    )
                    idx_emit += 1

            log.info(
                "Analisi MultiSwap completata: %d file, %d da spostare, %d restano",
                idx_emit, move_count, stayed_count,
            )
            self.finished.emit()
        except Exception as e:
            log.exception("Analisi MultiSwap fallita")
            self.error.emit(str(e))


class MultiSwapExecuteWorker(QThread):
    """Esegue lo spostamento/copia per il multi-swap."""
    progress = Signal(int, str)
    finished = Signal(int)
    error = Signal(int, str)

    def __init__(self, items: list[dict], folders: list[Path], use_copy: bool):
        super().__init__()
        self.items = items
        self.folders = folders
        self.use_copy = use_copy

    def run(self):
        transfer_fn = copy_file if self.use_copy else move_file
        action = "COPY" if self.use_copy else "MOVE"
        log.info(
            "Esecuzione MultiSwap avviata: %s %d file su %d cartelle",
            action, len(self.items), len(self.folders),
        )
        count = 0
        for i, item in enumerate(self.items):
            if self.isInterruptionRequested():
                log.info("Esecuzione MultiSwap interrotta: %d/%d riusciti", count, len(self.items))
                self.finished.emit(count)
                return
            try:
                source = Path(item["path"])
                dest_idx = item["dest_idx"]
                if not (0 <= dest_idx < len(self.folders)):
                    raise ValueError(f"dest_idx {dest_idx} fuori range")
                dest_folder = self.folders[dest_idx]
                final = transfer_fn(source, dest_folder)
                self.progress.emit(i, str(final))
                count += 1
            except Exception as e:
                log.exception("Esecuzione MultiSwap: errore su %s", item.get("path"))
                self.error.emit(i, str(e))
        log.info("Esecuzione MultiSwap completata: %d/%d riusciti", count, len(self.items))
        self.finished.emit(count)


class FolderRenameAnalyzeWorker(QThread):
    """Analizza cartelle e propone nomi piu' coerenti."""
    progress = Signal(int, str, str, str, float, str, str, str)
    finished = Signal()
    error = Signal(str)

    def __init__(self, root_folder: Path, include_root: bool):
        super().__init__()
        self.root_folder = root_folder
        self.include_root = include_root

    def _targets(self) -> list[Path]:
        targets: list[Path] = []
        if self.include_root:
            targets.append(self.root_folder)
        targets.extend(
            item for item in sorted(self.root_folder.iterdir())
            if item.is_dir() and not item.name.startswith(".")
        )
        return targets

    def run(self):
        try:
            targets = self._targets()
            log.info(
                "Analisi RenameFolders avviata: root=%s include_root=%s cartelle=%d",
                self.root_folder, self.include_root, len(targets),
            )
            for idx, folder in enumerate(targets):
                if self.isInterruptionRequested():
                    log.info("Analisi RenameFolders interrotta")
                    self.error.emit("Operazione interrotta.")
                    return

                profile = build_folder_profile(folder)
                suggestion = suggest_folder_rename(profile)
                self.progress.emit(
                    idx,
                    str(folder),
                    folder.name,
                    suggestion["suggested_name"],
                    float(suggestion["confidence"]),
                    suggestion["action"],
                    suggestion["reason"],
                    str(profile.get("file_count", 0)),
                )
            log.info("Analisi RenameFolders completata: %d cartelle", len(targets))
            self.finished.emit()
        except Exception as e:
            log.exception("Analisi RenameFolders fallita")
            self.error.emit(str(e))


class ProjectedFolderRenameAnalyzeWorker(QThread):
    """Analizza profili cartella gia' proiettati dopo uno swap."""
    progress = Signal(int, str, str, str, float, str, str, str)
    finished = Signal()
    error = Signal(str)

    def __init__(self, profiles: list[dict]):
        super().__init__()
        self.profiles = profiles

    def run(self):
        try:
            log.info(
                "Analisi RenameFolders post-swap avviata: %d cartelle",
                len(self.profiles),
            )
            for idx, profile in enumerate(self.profiles):
                if self.isInterruptionRequested():
                    log.info("Analisi RenameFolders post-swap interrotta")
                    self.error.emit("Operazione interrotta.")
                    return

                suggestion = suggest_folder_rename(profile)
                self.progress.emit(
                    idx,
                    str(profile["path"]),
                    str(profile["current_name"]),
                    suggestion["suggested_name"],
                    float(suggestion["confidence"]),
                    suggestion["action"],
                    suggestion["reason"],
                    str(profile.get("file_count", 0)),
                )
            log.info("Analisi RenameFolders post-swap completata")
            self.finished.emit()
        except Exception as e:
            log.exception("Analisi RenameFolders post-swap fallita")
            self.error.emit(str(e))


class FolderRenameExecuteWorker(QThread):
    """Esegue rename cartelle selezionate."""
    progress = Signal(int, str)
    finished = Signal(int)
    error = Signal(int, str)

    def __init__(self, items: list[dict]):
        super().__init__()
        self.items = items

    def run(self):
        log.info("Esecuzione RenameFolders avviata: %d cartelle", len(self.items))
        count = 0
        ordered = sorted(
            enumerate(self.items),
            key=lambda pair: len(Path(pair[1]["path"]).parts),
            reverse=True,
        )
        for original_idx, item in ordered:
            if self.isInterruptionRequested():
                log.info("Esecuzione RenameFolders interrotta: %d/%d riuscite", count, len(self.items))
                self.finished.emit(count)
                return
            try:
                source = Path(item["path"])
                final = rename_folder_safe(source, item["suggested_name"])
                self.progress.emit(original_idx, str(final))
                count += 1
            except Exception as e:
                log.exception("Esecuzione RenameFolders: errore su %s", item.get("path"))
                self.error.emit(original_idx, str(e))
        log.info("Esecuzione RenameFolders completata: %d/%d riuscite", count, len(self.items))
        self.finished.emit(count)


class ModelDownloadWorker(QThread):
    """Scarica un modello GGUF in background."""
    finished = Signal(str)   # path del file scaricato
    error = Signal(str)      # messaggio di errore

    def __init__(self, tier: str):
        super().__init__()
        self.tier = tier

    def run(self):
        try:
            if self.isInterruptionRequested():
                return
            path = download_model(self.tier)
            self.finished.emit(str(path))
        except Exception as e:
            log.exception("ModelDownloadWorker: errore tier=%s", self.tier)
            self.error.emit(str(e))


# ── Drop Area widget ─────────────────────────────────────────────────

class DropArea(QLabel):
    """Etichetta che accetta drag & drop di cartelle."""
    folder_dropped = Signal(str)

    def __init__(self, text="Trascina una cartella qui"):
        super().__init__(text)
        self.setObjectName("dropArea")
        self.setAlignment(Qt.AlignCenter)
        self.setAcceptDrops(True)
        self.setMinimumHeight(90)
        self.setProperty("dragOver", False)

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                if Path(url.toLocalFile()).is_dir():
                    event.acceptProposedAction()
                    self.setProperty("dragOver", True)
                    self.style().unpolish(self)
                    self.style().polish(self)
                    return

    def dragLeaveEvent(self, event):
        self.setProperty("dragOver", False)
        self.style().unpolish(self)
        self.style().polish(self)
        event.accept()

    def dropEvent(self, event: QDropEvent):
        self.setProperty("dragOver", False)
        self.style().unpolish(self)
        self.style().polish(self)
        for url in event.mimeData().urls():
            path = url.toLocalFile()
            if Path(path).is_dir():
                self.folder_dropped.emit(path)
                return


# ── Utilità condivise GUI ────────────────────────────────────────────

def _check_model_ready(parent: QWidget) -> bool:
    """Controlla che un modello sia scaricato prima di analizzare."""
    tier = get_selected_tier()
    if not is_model_downloaded(tier):
        QMessageBox.warning(
            parent, "Modello non scaricato",
            "Nessun modello AI scaricato.\n\n"
            "Vai nel tab Impostazioni per scaricare un modello.",
        )
        return False
    return True


def _path_key(path: Path) -> str:
    """Ritorna una chiave path stabile per confronti tra file/cartelle."""
    try:
        return str(path.resolve())
    except OSError:
        return str(path)


def _set_item_colors(item: QTableWidgetItem, foreground: str, background: str | None = None):
    """Imposta colori via data roles, piu' robusti dei setter con QSS attivo."""
    item.setData(Qt.ForegroundRole, QBrush(QColor(foreground)))
    if background is not None:
        item.setData(Qt.BackgroundRole, QBrush(QColor(background)))


def _mark_row_error(table: QTableWidget, row: int):
    for col in range(table.columnCount()):
        item = table.item(row, col)
        if item:
            _set_item_colors(item, "#ffffff", "#7f1d1d")


# ── Tab Organizza ─────────────────────────────────────────────────────

def _remove_one_name(names: list[str], target: str):
    """Rimuove una singola occorrenza per nome file, se presente."""
    try:
        names.pop(names.index(target))
    except ValueError:
        pass


def _selected_folder_rename_items(table: QTableWidget, items: list[dict]) -> list[tuple[int, dict]]:
    selected: list[tuple[int, dict]] = []
    for row in range(table.rowCount()):
        checkbox = table.item(row, 0)
        if row >= len(items) or checkbox is None:
            continue
        entry = items[row]
        if entry.get("action") == "rename" and checkbox.checkState() == Qt.Checked:
            selected.append((row, entry))
    return selected


def _append_folder_rename_row(
    table: QTableWidget,
    items: list[dict],
    idx: int,
    path: str,
    current_name: str,
    suggested_name: str,
    confidence: float,
    action: str,
    reason: str,
    file_count: str,
):
    row = table.rowCount()
    table.insertRow(row)

    should_rename = action == "rename"
    checkbox = QTableWidgetItem()
    if should_rename:
        checkbox.setCheckState(Qt.Checked)
        checkbox.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
    else:
        checkbox.setCheckState(Qt.Unchecked)
        checkbox.setFlags(Qt.ItemIsEnabled)
    table.setItem(row, 0, checkbox)

    decision = "Rinomina" if should_rename else "Mantieni"
    values = [
        current_name,
        suggested_name,
        f"{confidence:.2f}",
        decision,
        str(file_count),
        reason,
    ]
    for col, text in enumerate(values, start=1):
        table_item = QTableWidgetItem(text)
        if not should_rename:
            _set_item_colors(table_item, "#7a7a7a", None)
        table.setItem(row, col, table_item)

    items.append({
        "path": path,
        "current_name": current_name,
        "suggested_name": suggested_name,
        "confidence": confidence,
        "action": action,
        "reason": reason,
        "file_count": file_count,
    })


def _execute_folder_renames_inline(
    table: QTableWidget,
    items: list[dict],
) -> list[dict]:
    """Esegue le rinomine selezionate e ritorna quelle riuscite."""
    selected = _selected_folder_rename_items(table, items)
    successful: list[dict] = []
    ordered = sorted(
        selected,
        key=lambda pair: len(Path(pair[1]["path"]).parts),
        reverse=True,
    )

    for row, entry in ordered:
        try:
            source = Path(entry["path"])
            final = rename_folder_safe(source, entry["suggested_name"])
            done = dict(entry)
            done["final_path"] = str(final)
            done["final_name"] = final.name
            successful.append(done)

            table.setItem(row, 1, QTableWidgetItem(final.name))
            for col in range(table.columnCount()):
                item = table.item(row, col)
                if item:
                    _set_item_colors(item, "#6a9a6a", None)
        except Exception:
            log.exception("Rinomina cartella post-swap fallita: %s", entry.get("path"))
            _mark_row_error(table, row)
    return successful


class OrganizeTab(QWidget):
    operation_completed = Signal(dict)  # segnale per cronologia

    def __init__(self):
        super().__init__()
        self._worker = None
        self._exec_worker = None
        self._analyzed_items: list[dict] = []
        self._folder: Path | None = None
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        # ── Selezione cartella ──
        folder_layout = QHBoxLayout()
        self.drop_area = DropArea("Trascina una cartella qui")
        self.drop_area.folder_dropped.connect(self._set_folder)
        folder_layout.addWidget(self.drop_area, stretch=1)

        self.browse_btn = QPushButton("Sfoglia")
        self.browse_btn.clicked.connect(self._browse_folder)
        folder_layout.addWidget(self.browse_btn)
        layout.addLayout(folder_layout)

        self.path_edit = QLineEdit()
        self.path_edit.setReadOnly(True)
        self.path_edit.setPlaceholderText("Nessuna cartella selezionata")
        layout.addWidget(self.path_edit)

        # ── Opzioni ──
        opts_layout = QHBoxLayout()
        self.radio_move = QRadioButton("Sposta file")
        self.radio_copy = QRadioButton("Copia file")
        self.radio_move.setChecked(True)
        group = QButtonGroup(self)
        group.addButton(self.radio_move)
        group.addButton(self.radio_copy)
        opts_layout.addWidget(self.radio_move)
        opts_layout.addWidget(self.radio_copy)
        opts_layout.addStretch()

        self.analyze_btn = QPushButton("Analizza")
        self.analyze_btn.setObjectName("accentBtn")
        self.analyze_btn.setEnabled(False)
        self.analyze_btn.clicked.connect(self._start_analyze)
        opts_layout.addWidget(self.analyze_btn)
        layout.addLayout(opts_layout)

        # ── Tabella ──
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["", "Nome file", "Dimensione", "Categoria"])
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionMode(QAbstractItemView.NoSelection)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Fixed)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.Stretch)
        self.table.setColumnWidth(0, 40)
        # Checkbox "seleziona tutti" nell'header
        self._select_all_checked = True
        self.table.horizontalHeaderItem(0).setToolTip("Seleziona/Deseleziona tutti")
        header.sectionClicked.connect(self._toggle_select_all)
        layout.addWidget(self.table, stretch=1)

        # ── Barra progresso e bottoni ──
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        bottom_layout = QHBoxLayout()
        self.status_label = QLabel("")
        self.status_label.setObjectName("statusLabel")
        bottom_layout.addWidget(self.status_label, stretch=1)

        self.execute_btn = QPushButton("Esegui")
        self.execute_btn.setObjectName("accentBtn")
        self.execute_btn.setEnabled(False)
        self.execute_btn.clicked.connect(self._start_execute)
        bottom_layout.addWidget(self.execute_btn)
        layout.addLayout(bottom_layout)

    def _set_folder(self, path: str):
        self._folder = Path(path)
        self.path_edit.setText(path)
        self.analyze_btn.setEnabled(True)
        self.execute_btn.setEnabled(False)
        self.table.setRowCount(0)
        self._analyzed_items.clear()
        self.status_label.setText("")

    def _browse_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Seleziona cartella")
        if folder:
            self._set_folder(folder)

    def _toggle_select_all(self, index):
        if index != 0:
            return
        self._select_all_checked = not self._select_all_checked
        for row in range(self.table.rowCount()):
            item = self.table.item(row, 0)
            if item:
                item.setCheckState(Qt.Checked if self._select_all_checked else Qt.Unchecked)

    def _start_analyze(self):
        if not self._folder:
            return
        if self._worker is not None and self._worker.isRunning():
            return
        if not _check_model_ready(self):
            return

        # Inizializza il classificatore con il tier corrente
        tier = get_selected_tier()
        init_classifier(tier)

        self.table.setRowCount(0)
        self._analyzed_items.clear()
        self.analyze_btn.setEnabled(False)
        self.execute_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # indeterminata
        self.status_label.setText("Analisi in corso...")

        self._worker = OrganizeAnalyzeWorker(self._folder)
        self._worker.progress.connect(self._on_analyze_progress)
        self._worker.finished.connect(self._on_analyze_finished)
        self._worker.error.connect(self._on_analyze_error)
        self._worker.start()

    def _on_analyze_progress(self, idx, filename, size_str, category, size_bytes):
        row = self.table.rowCount()
        self.table.insertRow(row)

        # Checkbox
        chk = QTableWidgetItem()
        chk.setCheckState(Qt.Checked)
        chk.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
        self.table.setItem(row, 0, chk)

        self.table.setItem(row, 1, QTableWidgetItem(filename))
        self.table.setItem(row, 2, QTableWidgetItem(size_str))
        self.table.setItem(row, 3, QTableWidgetItem(category))

        self._analyzed_items.append({
            "path": str(self._folder / filename),
            "filename": filename,
            "size_str": size_str,
            "category": category,
        })
        self.status_label.setText(f"Classificazione {idx + 1} file...")

    def _on_analyze_finished(self):
        self._worker = None
        n = len(self._analyzed_items)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(100)
        self.status_label.setText(f"Analisi completata: {n} file classificati.")
        self.analyze_btn.setEnabled(True)
        self.execute_btn.setEnabled(n > 0)

    def _on_analyze_error(self, msg):
        self._worker = None
        self.progress_bar.setVisible(False)
        self.status_label.setText(f"Errore: {msg}")
        self.analyze_btn.setEnabled(True)

    def _start_execute(self):
        selected = []
        self._exec_success_indices = []
        self._exec_row_map = []  # mappa indice worker → riga tabella
        for row in range(self.table.rowCount()):
            if self.table.item(row, 0).checkState() == Qt.Checked:
                selected.append(self._analyzed_items[row])
                self._exec_row_map.append(row)

        if not selected:
            self.status_label.setText("Nessun file selezionato.")
            return

        use_copy = self.radio_copy.isChecked()
        self.execute_btn.setEnabled(False)
        self.analyze_btn.setEnabled(False)
        self.progress_bar.setRange(0, len(selected))
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(True)

        action = "Copia" if use_copy else "Spostamento"
        self.status_label.setText(f"{action} in corso...")

        self._exec_worker = OrganizeExecuteWorker(selected, self._folder, use_copy)
        self._exec_worker.progress.connect(self._on_exec_progress)
        self._exec_worker.finished.connect(lambda c: self._on_exec_finished(c, selected, use_copy))
        self._exec_worker.error.connect(self._on_exec_error)
        self._exec_worker.start()

    def _on_exec_progress(self, idx, dest):
        if not hasattr(self, "_exec_success_indices"):
            self._exec_success_indices = []
        self._exec_success_indices.append(idx)
        self.progress_bar.setValue(idx + 1)
        total = self.progress_bar.maximum()
        action = "Copia" if self.radio_copy.isChecked() else "Spostamento"
        self.status_label.setText(f"{action} {idx + 1}/{total}...")

    def _on_exec_finished(self, count, selected, use_copy):
        self._exec_worker = None
        action = "copiati" if use_copy else "spostati"
        self.status_label.setText(f"Completato! {count} file {action}.")
        self.analyze_btn.setEnabled(True)
        if self.progress_bar.maximum() == 0:
            self.progress_bar.setRange(0, max(count, 1))
        self.progress_bar.setValue(self.progress_bar.maximum())

        success_indices = getattr(self, "_exec_success_indices", [])
        successful = [selected[i] for i in success_indices if i < len(selected)]

        # Salva in cronologia
        entry = {
            "timestamp": datetime.now().isoformat(),
            "type": "Organizza",
            "folders": [str(self._folder)],
            "mode": "Copia" if use_copy else "Sposta",
            "file_count": count,
            "files": [
                {"file": s["filename"], "category": s["category"]}
                for s in successful
            ],
        }
        self.operation_completed.emit(entry)

    def _on_exec_error(self, idx, msg):
        # Risali alla riga reale della tabella
        table_row = self._exec_row_map[idx] if idx < len(self._exec_row_map) else idx
        _mark_row_error(self.table, table_row)


# ── Tab Swap ──────────────────────────────────────────────────────────

class SwapTab(QWidget):
    operation_completed = Signal(dict)

    def __init__(self):
        super().__init__()
        self._worker = None
        self._exec_worker = None
        self._rename_worker = None
        self._analyzed_items: list[dict] = []
        self._rename_items: list[dict] = []
        self._folder_a: Path | None = None
        self._folder_b: Path | None = None
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        # ── Selezione cartelle ──
        folders_layout = QHBoxLayout()

        # Cartella A
        col_a = QVBoxLayout()
        lbl_a = QLabel("Cartella A")
        lbl_a.setStyleSheet("font-weight: bold;")
        col_a.addWidget(lbl_a)
        self.drop_a = DropArea("Trascina cartella A")
        self.drop_a.folder_dropped.connect(lambda p: self._set_folder("A", p))
        col_a.addWidget(self.drop_a)
        browse_a = QPushButton("Sfoglia")
        browse_a.clicked.connect(lambda: self._browse("A"))
        col_a.addWidget(browse_a)
        self.path_a = QLineEdit()
        self.path_a.setReadOnly(True)
        self.path_a.setPlaceholderText("Nessuna cartella")
        col_a.addWidget(self.path_a)
        folders_layout.addLayout(col_a)

        # Icona scambio
        swap_icon = QLabel("  ⇄  ")
        swap_icon.setStyleSheet("font-size: 28px; font-weight: bold;")
        swap_icon.setAlignment(Qt.AlignCenter)
        folders_layout.addWidget(swap_icon)

        # Cartella B
        col_b = QVBoxLayout()
        lbl_b = QLabel("Cartella B")
        lbl_b.setStyleSheet("font-weight: bold;")
        col_b.addWidget(lbl_b)
        self.drop_b = DropArea("Trascina cartella B")
        self.drop_b.folder_dropped.connect(lambda p: self._set_folder("B", p))
        col_b.addWidget(self.drop_b)
        browse_b = QPushButton("Sfoglia")
        browse_b.clicked.connect(lambda: self._browse("B"))
        col_b.addWidget(browse_b)
        self.path_b = QLineEdit()
        self.path_b.setReadOnly(True)
        self.path_b.setPlaceholderText("Nessuna cartella")
        col_b.addWidget(self.path_b)
        folders_layout.addLayout(col_b)

        layout.addLayout(folders_layout)

        # ── Opzioni ──
        opts_layout = QHBoxLayout()
        self.radio_move = QRadioButton("Sposta file")
        self.radio_copy = QRadioButton("Copia file")
        self.radio_move.setChecked(True)
        group = QButtonGroup(self)
        group.addButton(self.radio_move)
        group.addButton(self.radio_copy)
        opts_layout.addWidget(self.radio_move)
        opts_layout.addWidget(self.radio_copy)
        self.rename_after_swap_chk = QCheckBox("Proponi rinomina cartelle")
        self.rename_after_swap_chk.setToolTip(
            "Dopo l'analisi dello swap propone nomi cartella basati sui file previsti."
        )
        opts_layout.addWidget(self.rename_after_swap_chk)
        opts_layout.addStretch()

        self.analyze_btn = QPushButton("Analizza scambio")
        self.analyze_btn.setObjectName("accentBtn")
        self.analyze_btn.setEnabled(False)
        self.analyze_btn.clicked.connect(self._start_analyze)
        opts_layout.addWidget(self.analyze_btn)
        layout.addLayout(opts_layout)

        # ── Tabella ──
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["", "Nome file", "Dimensione", "Posizione attuale", "Destinazione"])
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionMode(QAbstractItemView.NoSelection)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Fixed)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.table.setColumnWidth(0, 40)
        header.sectionClicked.connect(self._toggle_select_all)
        self._select_all_checked = True
        layout.addWidget(self.table, stretch=1)

        self.rename_label = QLabel("Rinomina cartelle post-swap")
        self.rename_label.setObjectName("statusLabel")
        self.rename_label.setVisible(False)
        layout.addWidget(self.rename_label)

        self.rename_table = QTableWidget(0, 7)
        self.rename_table.setHorizontalHeaderLabels([
            "", "Cartella", "Nome proposto", "Confidenza", "Decisione", "File", "Motivo"
        ])
        self.rename_table.setAlternatingRowColors(True)
        self.rename_table.setSelectionMode(QAbstractItemView.NoSelection)
        self.rename_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        rename_header = self.rename_table.horizontalHeader()
        rename_header.setSectionResizeMode(0, QHeaderView.Fixed)
        rename_header.setSectionResizeMode(1, QHeaderView.Stretch)
        rename_header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        rename_header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        rename_header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        rename_header.setSectionResizeMode(5, QHeaderView.ResizeToContents)
        rename_header.setSectionResizeMode(6, QHeaderView.Stretch)
        self.rename_table.setColumnWidth(0, 40)
        self._rename_select_all_checked = True
        rename_header.sectionClicked.connect(self._toggle_rename_select_all)
        self.rename_table.setVisible(False)
        layout.addWidget(self.rename_table, stretch=0)

        # ── Barra progresso e bottoni ──
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        bottom = QHBoxLayout()
        self.status_label = QLabel("")
        self.status_label.setObjectName("statusLabel")
        bottom.addWidget(self.status_label, stretch=1)
        self.execute_btn = QPushButton("Esegui")
        self.execute_btn.setObjectName("accentBtn")
        self.execute_btn.setEnabled(False)
        self.execute_btn.clicked.connect(self._start_execute)
        bottom.addWidget(self.execute_btn)
        layout.addLayout(bottom)

    def _set_folder(self, which, path):
        p = Path(path)
        if which == "A":
            self._folder_a = p
            self.path_a.setText(path)
        else:
            self._folder_b = p
            self.path_b.setText(path)
        self._check_ready()

    def _browse(self, which):
        folder = QFileDialog.getExistingDirectory(self, f"Seleziona cartella {which}")
        if folder:
            self._set_folder(which, folder)

    def _same_selected_folders(self) -> bool:
        if not self._folder_a or not self._folder_b:
            return False
        return self._folder_a.resolve() == self._folder_b.resolve()

    def _check_ready(self):
        ready = self._folder_a is not None and self._folder_b is not None
        if ready and self._same_selected_folders():
            self.analyze_btn.setEnabled(False)
            self.status_label.setText("Le due cartelle devono essere diverse.")
        else:
            self.analyze_btn.setEnabled(ready)
            self.status_label.setText("")
        self.execute_btn.setEnabled(False)
        self.table.setRowCount(0)
        self._analyzed_items.clear()

    def _toggle_select_all(self, index):
        if index != 0:
            return
        self._select_all_checked = not self._select_all_checked
        for row in range(self.table.rowCount()):
            item = self.table.item(row, 0)
            if item and (item.flags() & Qt.ItemIsUserCheckable):
                item.setCheckState(Qt.Checked if self._select_all_checked else Qt.Unchecked)

    def _toggle_rename_select_all(self, index):
        if index != 0:
            return
        self._rename_select_all_checked = not self._rename_select_all_checked
        for row in range(self.rename_table.rowCount()):
            item = self.rename_table.item(row, 0)
            if item and (item.flags() & Qt.ItemIsUserCheckable):
                item.setCheckState(Qt.Checked if self._rename_select_all_checked else Qt.Unchecked)

    def _clear_rename_preview(self):
        self.rename_table.setRowCount(0)
        self.rename_table.setVisible(False)
        self.rename_label.setVisible(False)
        self._rename_items.clear()

    def _projected_folder_profiles(self) -> list[dict]:
        if not self._folder_a or not self._folder_b:
            return []

        names_a = [entry["path"].name for entry in scan_folder(self._folder_a)]
        names_b = [entry["path"].name for entry in scan_folder(self._folder_b)]
        use_copy = self.radio_copy.isChecked()

        for item in self._analyzed_items:
            if item["stays"]:
                continue
            filename = item["filename"]
            if item["origin"] == "A":
                if not use_copy:
                    _remove_one_name(names_a, filename)
                names_b.append(filename)
            else:
                if not use_copy:
                    _remove_one_name(names_b, filename)
                names_a.append(filename)

        return [
            build_folder_profile_from_names(self._folder_a, names_a),
            build_folder_profile_from_names(self._folder_b, names_b),
        ]

    def _start_projected_rename_analysis(self):
        if not is_folder_rename_allowed():
            self.status_label.setText(
                self.status_label.text()
                + " Rinomina cartelle disabilitata nelle Impostazioni."
            )
            return

        profiles = self._projected_folder_profiles()
        if not profiles:
            return

        self._clear_rename_preview()
        self.rename_table.setVisible(True)
        self.rename_label.setVisible(True)
        self.execute_btn.setEnabled(False)
        self.progress_bar.setRange(0, 0)
        self.progress_bar.setVisible(True)
        self.status_label.setText("Analisi nomi cartelle post-swap...")

        self._rename_worker = ProjectedFolderRenameAnalyzeWorker(profiles)
        self._rename_worker.progress.connect(self._on_rename_analyze_progress)
        self._rename_worker.finished.connect(self._on_rename_analyze_finished)
        self._rename_worker.error.connect(self._on_rename_analyze_error)
        self._rename_worker.start()

    def _on_rename_analyze_progress(
        self, idx, path, current_name, suggested_name, confidence, action, reason, file_count
    ):
        _append_folder_rename_row(
            self.rename_table, self._rename_items, idx, path, current_name,
            suggested_name, confidence, action, reason, file_count,
        )
        self.status_label.setText(f"Analisi nome cartella {idx + 1}...")

    def _on_rename_analyze_finished(self):
        self._rename_worker = None
        to_move = sum(1 for item in self._analyzed_items if not item["stays"])
        to_rename = sum(1 for item in self._rename_items if item["action"] == "rename")
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(100)
        self.status_label.setText(
            f"Analisi completata: {len(self._analyzed_items)} file, "
            f"{to_move} da spostare, {to_rename} rinomine proposte."
        )
        self.execute_btn.setEnabled(to_move > 0 or to_rename > 0)

    def _on_rename_analyze_error(self, msg):
        self._rename_worker = None
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(100)
        to_move = sum(1 for item in self._analyzed_items if not item["stays"])
        self.execute_btn.setEnabled(to_move > 0)
        self.status_label.setText(f"Analisi file completata, rinomina non disponibile: {msg}")

    def _apply_renamed_folder_paths(self, renamed: list[dict]):
        for item in renamed:
            final_path = item.get("final_path")
            if not final_path:
                continue
            old_key = _path_key(Path(item["path"]))
            final = Path(final_path)
            if self._folder_a and _path_key(self._folder_a) == old_key:
                self._folder_a = final
                self.path_a.setText(str(final))
            if self._folder_b and _path_key(self._folder_b) == old_key:
                self._folder_b = final
                self.path_b.setText(str(final))

    def _start_analyze(self):
        if not self._folder_a or not self._folder_b:
            return
        if self._same_selected_folders():
            self.status_label.setText("Le due cartelle devono essere diverse.")
            return
        if self._worker is not None and self._worker.isRunning():
            return
        if self._rename_worker is not None and self._rename_worker.isRunning():
            return
        if not _check_model_ready(self):
            return

        tier = get_selected_tier()
        init_classifier(tier)

        self.table.setRowCount(0)
        self._analyzed_items.clear()
        self._clear_rename_preview()
        self.analyze_btn.setEnabled(False)
        self.execute_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)
        self.status_label.setText("Analisi scambio in corso...")

        self._worker = SwapAnalyzeWorker(self._folder_a, self._folder_b)
        self._worker.progress.connect(self._on_analyze_progress)
        self._worker.finished.connect(self._on_analyze_finished)
        self._worker.error.connect(self._on_analyze_error)
        self._worker.start()

    def _on_analyze_progress(self, idx, filename, size_str, current_folder, dest_label, origin):
        row = self.table.rowCount()
        self.table.insertRow(row)

        stays = dest_label.startswith("Resta in")

        # Checkbox — disabilitata se resta
        chk = QTableWidgetItem()
        if stays:
            chk.setCheckState(Qt.Unchecked)
            chk.setFlags(Qt.ItemIsEnabled)  # non checkable
        else:
            chk.setCheckState(Qt.Checked)
            chk.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
        self.table.setItem(row, 0, chk)

        items_data = [filename, size_str, current_folder, dest_label]
        for col, text in enumerate(items_data, start=1):
            ti = QTableWidgetItem(text)
            if stays:
                _set_item_colors(ti, "#6a9a6a")
            self.table.setItem(row, col, ti)

        # Salva dati interni per l'esecuzione
        source_folder = self._folder_a if origin == "A" else self._folder_b
        self._analyzed_items.append({
            "path": str(source_folder / filename),
            "filename": filename,
            "origin": origin,
            "stays": stays,
            "dest_label": dest_label,
            "current_folder": current_folder,
        })
        self.status_label.setText(f"Classificazione {idx + 1} file...")

    def _on_analyze_finished(self):
        self._worker = None
        n = len(self._analyzed_items)
        to_move = sum(1 for it in self._analyzed_items if not it["stays"])
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(100)
        self.status_label.setText(f"Analisi completata: {n} file analizzati, {to_move} da spostare.")
        self.analyze_btn.setEnabled(True)
        self.execute_btn.setEnabled(to_move > 0)
        if self.rename_after_swap_chk.isChecked():
            self._start_projected_rename_analysis()

    def _on_analyze_error(self, msg):
        self._worker = None
        self.progress_bar.setVisible(False)
        self.status_label.setText(f"Errore: {msg}")
        self.analyze_btn.setEnabled(True)

    def _start_execute(self):
        selected = []
        self._exec_row_map = []  # mappa indice worker → riga tabella
        self._exec_success_indices = []
        for row in range(self.table.rowCount()):
            item = self.table.item(row, 0)
            entry = self._analyzed_items[row]
            if not entry["stays"] and item.checkState() == Qt.Checked:
                selected.append(entry)
                self._exec_row_map.append(row)

        use_copy = self.radio_copy.isChecked()
        selected_renames = _selected_folder_rename_items(self.rename_table, self._rename_items)
        if not selected and not selected_renames:
            self.status_label.setText("Nessun file o cartella selezionata.")
            return

        self.execute_btn.setEnabled(False)
        self.analyze_btn.setEnabled(False)
        self.progress_bar.setRange(0, max(len(selected), 1))
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(True)

        if not selected:
            self.status_label.setText("Rinomina cartelle in corso...")
            renamed = []
            if is_folder_rename_allowed():
                renamed = _execute_folder_renames_inline(self.rename_table, self._rename_items)
            self._on_exec_finished(0, [], use_copy, renamed)
            return

        action = "Copia" if use_copy else "Spostamento"
        self.status_label.setText(f"{action} in corso...")

        self._exec_worker = SwapExecuteWorker(selected, self._folder_a, self._folder_b, use_copy)
        self._exec_worker.progress.connect(self._on_exec_progress)
        self._exec_worker.finished.connect(lambda c: self._on_exec_finished(c, selected, use_copy))
        self._exec_worker.error.connect(self._on_exec_error)
        self._exec_worker.start()

    def _on_exec_progress(self, idx, dest):
        if not hasattr(self, "_exec_success_indices"):
            self._exec_success_indices = []
        self._exec_success_indices.append(idx)
        self.progress_bar.setValue(idx + 1)
        total = self.progress_bar.maximum()
        action = "Copia" if self.radio_copy.isChecked() else "Spostamento"
        self.status_label.setText(f"{action} {idx + 1}/{total}...")

    def _on_exec_finished(self, count, selected, use_copy, renamed=None):
        self._exec_worker = None
        action = "copiati" if use_copy else "spostati"
        self.analyze_btn.setEnabled(True)
        if self.progress_bar.maximum() == 0:
            self.progress_bar.setRange(0, max(count, 1))
        self.progress_bar.setValue(self.progress_bar.maximum())

        success_indices = getattr(self, "_exec_success_indices", [])
        successful = [selected[i] for i in success_indices if i < len(selected)]
        if renamed is None:
            renamed = []
            if is_folder_rename_allowed():
                renamed = _execute_folder_renames_inline(self.rename_table, self._rename_items)
            elif _selected_folder_rename_items(self.rename_table, self._rename_items):
                self.status_label.setText("Rinomina cartelle disabilitata nelle Impostazioni.")

        rename_count = len(renamed)
        self._apply_renamed_folder_paths(renamed)
        rename_text = f", {rename_count} cartelle rinominate" if rename_count else ""
        self.status_label.setText(f"Completato! {count} file {action}{rename_text}.")

        file_details = [
            {"file": s["filename"], "from": s["current_folder"], "to": s["dest_label"]}
            for s in successful
        ]
        rename_details = [
            {
                "file": f"[cartella] {s['current_name']}",
                "from": s["current_name"],
                "to": s.get("final_name", s["suggested_name"]),
            }
            for s in renamed
        ]

        entry = {
            "timestamp": datetime.now().isoformat(),
            "type": "Swap",
            "folders": [str(self._folder_a), str(self._folder_b)],
            "mode": "Copia" if use_copy else "Sposta",
            "file_count": count,
            "folder_rename_count": rename_count,
            "files": file_details + rename_details,
        }
        self.operation_completed.emit(entry)

    def _on_exec_error(self, idx, msg):
        table_row = self._exec_row_map[idx] if idx < len(self._exec_row_map) else idx
        _mark_row_error(self.table, table_row)


# ── Tab Swap Multiplo ────────────────────────────────────────────────

class FolderSlot(QWidget):
    """
    Slot UI per una cartella nella tab MultiSwap. Contiene drop area, bottone
    Sfoglia, line edit e bottone Rimuovi. NON memorizza il proprio indice:
    emette segnali con `self` come riferimento, e il parent (MultiSwapTab)
    risolve l'indice corrente con `slots.index(slot)`.
    """
    folder_changed = Signal(QWidget, str)  # (self, path)
    removed = Signal(QWidget)              # (self,)

    def __init__(self, label_number: int, parent=None):
        super().__init__(parent)
        self._path: str = ""
        self._init_ui(label_number)

    def _init_ui(self, label_number: int):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        self.label = QLabel(f"#{label_number}")
        self.label.setFixedWidth(36)
        self.label.setAlignment(Qt.AlignCenter)
        self.label.setStyleSheet("font-weight: bold;")
        layout.addWidget(self.label)

        self.drop_area = DropArea("Trascina cartella")
        self.drop_area.setMinimumHeight(50)
        self.drop_area.folder_dropped.connect(self._on_folder_dropped)
        layout.addWidget(self.drop_area, stretch=1)

        self.path_edit = QLineEdit()
        self.path_edit.setReadOnly(True)
        self.path_edit.setPlaceholderText("Nessuna cartella")
        layout.addWidget(self.path_edit, stretch=2)

        self.browse_btn = QPushButton("Sfoglia")
        self.browse_btn.clicked.connect(self._on_browse)
        layout.addWidget(self.browse_btn)

        self.remove_btn = QPushButton("✕")
        self.remove_btn.setFixedWidth(32)
        self.remove_btn.setToolTip("Rimuovi questa cartella")
        self.remove_btn.clicked.connect(lambda: self.removed.emit(self))
        layout.addWidget(self.remove_btn)

    def set_label_number(self, n: int):
        self.label.setText(f"#{n}")

    def get_path(self) -> str:
        return self._path

    def set_path(self, path: str):
        self._path = path
        self.path_edit.setText(path)
        self.folder_changed.emit(self, path)

    def _on_folder_dropped(self, path: str):
        self.set_path(path)

    def _on_browse(self):
        folder = QFileDialog.getExistingDirectory(self, "Seleziona cartella")
        if folder:
            self.set_path(folder)


class MultiSwapTab(QWidget):
    """
    Tab per swap di file tra N cartelle (N >= 2). Usa il torneo a chunk
    di brain.classify_for_multi_swap per scalare con piu' di 2 cartelle.
    """
    operation_completed = Signal(dict)

    INITIAL_SLOTS = 3
    SOFT_WARN_THRESHOLD = 8  # oltre questo numero, suggerisci tier piu' alto

    def __init__(self):
        super().__init__()
        self._worker: MultiSwapAnalyzeWorker | None = None
        self._exec_worker: MultiSwapExecuteWorker | None = None
        self._rename_worker: ProjectedFolderRenameAnalyzeWorker | None = None
        self._slots: list[FolderSlot] = []
        self._analyzed_items: list[dict] = []
        self._rename_items: list[dict] = []
        self._folders: list[Path] = []
        self._init_ui()
        for _ in range(self.INITIAL_SLOTS):
            self._add_slot()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        info = QLabel(
            "Aggiungi 2 o piu' cartelle. Il modello scegliera' per ogni file "
            "la cartella piu' coerente fra tutte."
        )
        info.setObjectName("statusLabel")
        info.setWordWrap(True)
        layout.addWidget(info)

        # Area scrollabile con gli slot
        from PySide6.QtWidgets import QScrollArea  # type: ignore
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QScrollArea.NoFrame)
        self.scroll.setMinimumHeight(180)
        self.scroll.setMaximumHeight(280)
        self._slots_container = QWidget()
        self._slots_layout = QVBoxLayout(self._slots_container)
        self._slots_layout.setSpacing(6)
        self._slots_layout.addStretch()
        self.scroll.setWidget(self._slots_container)
        layout.addWidget(self.scroll)

        # Riga "+ Aggiungi cartella" e warning
        add_row = QHBoxLayout()
        self.add_btn = QPushButton("+ Aggiungi cartella")
        self.add_btn.clicked.connect(self._add_slot)
        add_row.addWidget(self.add_btn)
        self.warn_label = QLabel("")
        self.warn_label.setObjectName("statusLabel")
        self.warn_label.setWordWrap(True)
        add_row.addWidget(self.warn_label, stretch=1)
        layout.addLayout(add_row)

        # Opzioni e bottone Analizza
        opts = QHBoxLayout()
        self.radio_move = QRadioButton("Sposta file")
        self.radio_copy = QRadioButton("Copia file")
        self.radio_move.setChecked(True)
        group = QButtonGroup(self)
        group.addButton(self.radio_move)
        group.addButton(self.radio_copy)
        opts.addWidget(self.radio_move)
        opts.addWidget(self.radio_copy)
        self.rename_after_swap_chk = QCheckBox("Proponi rinomina cartelle")
        self.rename_after_swap_chk.setToolTip(
            "Dopo l'analisi propone nomi cartella basati sul contenuto finale previsto."
        )
        opts.addWidget(self.rename_after_swap_chk)
        opts.addStretch()
        self.analyze_btn = QPushButton("Analizza scambio")
        self.analyze_btn.setObjectName("accentBtn")
        self.analyze_btn.setEnabled(False)
        self.analyze_btn.clicked.connect(self._start_analyze)
        opts.addWidget(self.analyze_btn)
        layout.addLayout(opts)

        # Tabella risultati
        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(
            ["", "Nome file", "Dimensione", "Da", "A", "Esito"]
        )
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionMode(QAbstractItemView.NoSelection)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Fixed)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)
        self.table.setColumnWidth(0, 40)
        self._select_all_checked = True
        header.sectionClicked.connect(self._toggle_select_all)
        layout.addWidget(self.table, stretch=1)

        self.rename_label = QLabel("Rinomina cartelle post-swap")
        self.rename_label.setObjectName("statusLabel")
        self.rename_label.setVisible(False)
        layout.addWidget(self.rename_label)

        self.rename_table = QTableWidget(0, 7)
        self.rename_table.setHorizontalHeaderLabels([
            "", "Cartella", "Nome proposto", "Confidenza", "Decisione", "File", "Motivo"
        ])
        self.rename_table.setAlternatingRowColors(True)
        self.rename_table.setSelectionMode(QAbstractItemView.NoSelection)
        self.rename_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        rename_header = self.rename_table.horizontalHeader()
        rename_header.setSectionResizeMode(0, QHeaderView.Fixed)
        rename_header.setSectionResizeMode(1, QHeaderView.Stretch)
        rename_header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        rename_header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        rename_header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        rename_header.setSectionResizeMode(5, QHeaderView.ResizeToContents)
        rename_header.setSectionResizeMode(6, QHeaderView.Stretch)
        self.rename_table.setColumnWidth(0, 40)
        self._rename_select_all_checked = True
        rename_header.sectionClicked.connect(self._toggle_rename_select_all)
        self.rename_table.setVisible(False)
        layout.addWidget(self.rename_table, stretch=0)

        # Progress + Esegui
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        bottom = QHBoxLayout()
        self.status_label = QLabel("")
        self.status_label.setObjectName("statusLabel")
        bottom.addWidget(self.status_label, stretch=1)
        self.execute_btn = QPushButton("Esegui")
        self.execute_btn.setObjectName("accentBtn")
        self.execute_btn.setEnabled(False)
        self.execute_btn.clicked.connect(self._start_execute)
        bottom.addWidget(self.execute_btn)
        layout.addLayout(bottom)

    # ── Gestione slot dinamici ──────────────────────────────────────

    def _add_slot(self):
        slot = FolderSlot(label_number=len(self._slots) + 1, parent=self._slots_container)
        slot.folder_changed.connect(self._on_folder_changed)
        slot.removed.connect(self._on_slot_removed)
        # Inserisci PRIMA dello stretch finale
        insert_at = self._slots_layout.count() - 1
        self._slots_layout.insertWidget(insert_at, slot)
        self._slots.append(slot)
        self._update_warn_label()
        self._refresh_state()

    def _on_slot_removed(self, slot: QWidget):
        if slot not in self._slots:
            return
        self._slots.remove(slot)
        self._slots_layout.removeWidget(slot)
        slot.deleteLater()
        self._renumber_slots()
        self._update_warn_label()
        self._refresh_state()

    def _renumber_slots(self):
        for i, slot in enumerate(self._slots, start=1):
            slot.set_label_number(i)

    def _on_folder_changed(self, _slot: QWidget, _path: str):
        self._refresh_state()

    def _update_warn_label(self):
        n = len(self._slots)
        if n > self.SOFT_WARN_THRESHOLD:
            self.warn_label.setText(
                f"⚠ {n} cartelle: con tier 'lite'/'standard' la qualita' della "
                "classificazione puo' degradare. Considera 'pro' o 'ultra'."
            )
        else:
            self.warn_label.setText("")

    # ── Validazione e raccolta cartelle ─────────────────────────────

    def _collect_valid_folders(self) -> list[Path]:
        """Ritorna le cartelle valide e distinte (per resolve())."""
        seen: set[str] = set()
        result: list[Path] = []
        for slot in self._slots:
            p = slot.get_path()
            if not p:
                continue
            path = Path(p)
            if not path.is_dir():
                continue
            try:
                key = str(path.resolve())
            except OSError:
                key = str(path)
            if key in seen:
                continue
            seen.add(key)
            result.append(path)
        return result

    def _refresh_state(self):
        valid = self._collect_valid_folders()
        # Rileva duplicati per status
        total_filled = sum(1 for s in self._slots if s.get_path())
        ready = len(valid) >= 2

        if total_filled > len(valid):
            self.status_label.setText("Cartelle duplicate o non valide ignorate.")
        elif not ready:
            if total_filled < 2:
                self.status_label.setText("Servono almeno 2 cartelle distinte.")
            else:
                self.status_label.setText("")
        else:
            self.status_label.setText("")

        self.analyze_btn.setEnabled(ready)
        self.execute_btn.setEnabled(False)
        self.table.setRowCount(0)
        self._analyzed_items.clear()
        self._clear_rename_preview()

    # ── Selezione tabella ───────────────────────────────────────────

    def _toggle_select_all(self, index):
        if index != 0:
            return
        self._select_all_checked = not self._select_all_checked
        for row in range(self.table.rowCount()):
            item = self.table.item(row, 0)
            if item and (item.flags() & Qt.ItemIsUserCheckable):
                item.setCheckState(Qt.Checked if self._select_all_checked else Qt.Unchecked)

    # ── Analisi ────────────────────────────────────────────────────

    def _toggle_rename_select_all(self, index):
        if index != 0:
            return
        self._rename_select_all_checked = not self._rename_select_all_checked
        for row in range(self.rename_table.rowCount()):
            item = self.rename_table.item(row, 0)
            if item and (item.flags() & Qt.ItemIsUserCheckable):
                item.setCheckState(Qt.Checked if self._rename_select_all_checked else Qt.Unchecked)

    def _clear_rename_preview(self):
        self.rename_table.setRowCount(0)
        self.rename_table.setVisible(False)
        self.rename_label.setVisible(False)
        self._rename_items.clear()

    def _projected_folder_profiles(self) -> list[dict]:
        if not self._folders:
            return []

        projected_names: list[list[str]] = [
            [entry["path"].name for entry in scan_folder(folder)]
            for folder in self._folders
        ]
        use_copy = self.radio_copy.isChecked()

        for item in self._analyzed_items:
            if item["stays"]:
                continue
            origin_idx = item["origin_idx"]
            dest_idx = item["dest_idx"]
            filename = item["filename"]
            if not (0 <= origin_idx < len(projected_names)):
                continue
            if not (0 <= dest_idx < len(projected_names)):
                continue
            if not use_copy:
                _remove_one_name(projected_names[origin_idx], filename)
            projected_names[dest_idx].append(filename)

        return [
            build_folder_profile_from_names(folder, names)
            for folder, names in zip(self._folders, projected_names)
        ]

    def _start_projected_rename_analysis(self):
        if not is_folder_rename_allowed():
            self.status_label.setText(
                self.status_label.text()
                + " Rinomina cartelle disabilitata nelle Impostazioni."
            )
            return

        profiles = self._projected_folder_profiles()
        if not profiles:
            return

        self._clear_rename_preview()
        self.rename_table.setVisible(True)
        self.rename_label.setVisible(True)
        self.execute_btn.setEnabled(False)
        self.progress_bar.setRange(0, 0)
        self.progress_bar.setVisible(True)
        self.status_label.setText("Analisi nomi cartelle post-swap...")

        self._rename_worker = ProjectedFolderRenameAnalyzeWorker(profiles)
        self._rename_worker.progress.connect(self._on_rename_analyze_progress)
        self._rename_worker.finished.connect(self._on_rename_analyze_finished)
        self._rename_worker.error.connect(self._on_rename_analyze_error)
        self._rename_worker.start()

    def _on_rename_analyze_progress(
        self, idx, path, current_name, suggested_name, confidence, action, reason, file_count
    ):
        _append_folder_rename_row(
            self.rename_table, self._rename_items, idx, path, current_name,
            suggested_name, confidence, action, reason, file_count,
        )
        self.status_label.setText(f"Analisi nome cartella {idx + 1}...")

    def _on_rename_analyze_finished(self):
        self._rename_worker = None
        to_move = sum(1 for item in self._analyzed_items if not item["stays"])
        to_rename = sum(1 for item in self._rename_items if item["action"] == "rename")
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(100)
        self.status_label.setText(
            f"Analisi completata: {len(self._analyzed_items)} file, "
            f"{to_move} da spostare, {to_rename} rinomine proposte."
        )
        self.execute_btn.setEnabled(to_move > 0 or to_rename > 0)

    def _on_rename_analyze_error(self, msg):
        self._rename_worker = None
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(100)
        to_move = sum(1 for item in self._analyzed_items if not item["stays"])
        self.execute_btn.setEnabled(to_move > 0)
        self.status_label.setText(f"Analisi file completata, rinomina non disponibile: {msg}")

    def _apply_renamed_folder_paths(self, renamed: list[dict]):
        for item in renamed:
            final_path = item.get("final_path")
            if not final_path:
                continue
            old_key = _path_key(Path(item["path"]))
            final = Path(final_path)
            for idx, folder in enumerate(self._folders):
                if _path_key(folder) == old_key:
                    self._folders[idx] = final
            for slot in self._slots:
                slot_path = slot.get_path()
                if slot_path and _path_key(Path(slot_path)) == old_key:
                    slot._path = str(final)
                    slot.path_edit.setText(str(final))

    def _start_analyze(self):
        valid = self._collect_valid_folders()
        if len(valid) < 2:
            return
        if self._worker is not None and self._worker.isRunning():
            return
        if self._rename_worker is not None and self._rename_worker.isRunning():
            return
        if not _check_model_ready(self):
            return

        tier = get_selected_tier()
        init_classifier(tier)

        self._folders = valid
        self.table.setRowCount(0)
        self._analyzed_items.clear()
        self._clear_rename_preview()
        self.analyze_btn.setEnabled(False)
        self.execute_btn.setEnabled(False)
        self.add_btn.setEnabled(False)
        for slot in self._slots:
            slot.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)
        self.status_label.setText("Analisi multi-swap in corso...")

        self._worker = MultiSwapAnalyzeWorker(self._folders)
        self._worker.progress.connect(self._on_analyze_progress)
        self._worker.finished.connect(self._on_analyze_finished)
        self._worker.error.connect(self._on_analyze_error)
        self._worker.start()

    def _on_analyze_progress(
        self, idx, filename, size_str, current_folder, dest_label,
        origin_idx, dest_idx, stays,
    ):
        row = self.table.rowCount()
        self.table.insertRow(row)

        chk = QTableWidgetItem()
        if stays:
            chk.setCheckState(Qt.Unchecked)
            chk.setFlags(Qt.ItemIsEnabled)
        else:
            chk.setCheckState(Qt.Checked)
            chk.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
        self.table.setItem(row, 0, chk)

        outcome = "Resta" if stays else "Da spostare"
        items_data = [filename, size_str, current_folder, dest_label, outcome]
        for col, text in enumerate(items_data, start=1):
            ti = QTableWidgetItem(text)
            if stays:
                _set_item_colors(ti, "#7a7a7a", None)
            self.table.setItem(row, col, ti)

        self._analyzed_items.append({
            "path": str(self._folders[origin_idx] / filename),
            "filename": filename,
            "origin_idx": origin_idx,
            "dest_idx": dest_idx,
            "stays": stays,
            "current_folder": current_folder,
            "dest_label": dest_label,
        })
        self.status_label.setText(f"Classificazione {idx + 1} file...")

    def _on_analyze_finished(self):
        self._worker = None
        n = len(self._analyzed_items)
        to_move = sum(1 for it in self._analyzed_items if not it["stays"])
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(100)
        self.status_label.setText(
            f"Analisi completata: {n} file analizzati, {to_move} da spostare."
        )
        self.analyze_btn.setEnabled(True)
        self.add_btn.setEnabled(True)
        for slot in self._slots:
            slot.setEnabled(True)
        self.execute_btn.setEnabled(to_move > 0)
        if self.rename_after_swap_chk.isChecked():
            self._start_projected_rename_analysis()

    def _on_analyze_error(self, msg):
        self._worker = None
        self.progress_bar.setVisible(False)
        self.status_label.setText(f"Errore: {msg}")
        self.analyze_btn.setEnabled(True)
        self.add_btn.setEnabled(True)
        for slot in self._slots:
            slot.setEnabled(True)

    # ── Esecuzione ─────────────────────────────────────────────────

    def _start_execute(self):
        selected = []
        self._exec_row_map = []
        self._exec_success_indices = []
        for row in range(self.table.rowCount()):
            item = self.table.item(row, 0)
            entry = self._analyzed_items[row]
            if not entry["stays"] and item.checkState() == Qt.Checked:
                selected.append(entry)
                self._exec_row_map.append(row)

        use_copy = self.radio_copy.isChecked()
        selected_renames = _selected_folder_rename_items(self.rename_table, self._rename_items)
        if not selected and not selected_renames:
            self.status_label.setText("Nessun file o cartella selezionata.")
            return

        self.execute_btn.setEnabled(False)
        self.analyze_btn.setEnabled(False)
        self.add_btn.setEnabled(False)
        for slot in self._slots:
            slot.setEnabled(False)
        self.progress_bar.setRange(0, max(len(selected), 1))
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(True)

        if not selected:
            self.status_label.setText("Rinomina cartelle in corso...")
            renamed = []
            if is_folder_rename_allowed():
                renamed = _execute_folder_renames_inline(self.rename_table, self._rename_items)
            self._on_exec_finished(0, [], use_copy, renamed)
            return

        action = "Copia" if use_copy else "Spostamento"
        self.status_label.setText(f"{action} in corso...")

        self._exec_worker = MultiSwapExecuteWorker(selected, self._folders, use_copy)
        self._exec_worker.progress.connect(self._on_exec_progress)
        self._exec_worker.finished.connect(lambda c: self._on_exec_finished(c, selected, use_copy))
        self._exec_worker.error.connect(self._on_exec_error)
        self._exec_worker.start()

    def _on_exec_progress(self, idx, dest):
        if not hasattr(self, "_exec_success_indices"):
            self._exec_success_indices = []
        self._exec_success_indices.append(idx)
        self.progress_bar.setValue(idx + 1)
        total = self.progress_bar.maximum()
        action = "Copia" if self.radio_copy.isChecked() else "Spostamento"
        self.status_label.setText(f"{action} {idx + 1}/{total}...")

    def _on_exec_finished(self, count, selected, use_copy, renamed=None):
        self._exec_worker = None
        action = "copiati" if use_copy else "spostati"
        self.analyze_btn.setEnabled(True)
        self.add_btn.setEnabled(True)
        for slot in self._slots:
            slot.setEnabled(True)
        self.progress_bar.setValue(self.progress_bar.maximum())

        success_indices = getattr(self, "_exec_success_indices", [])
        successful = [selected[i] for i in success_indices if i < len(selected)]
        if renamed is None:
            renamed = []
            if is_folder_rename_allowed():
                renamed = _execute_folder_renames_inline(self.rename_table, self._rename_items)
            elif _selected_folder_rename_items(self.rename_table, self._rename_items):
                self.status_label.setText("Rinomina cartelle disabilitata nelle Impostazioni.")

        rename_count = len(renamed)
        self._apply_renamed_folder_paths(renamed)
        rename_text = f", {rename_count} cartelle rinominate" if rename_count else ""
        self.status_label.setText(f"Completato! {count} file {action}{rename_text}.")

        file_details = [
            {"file": s["filename"], "from": s["current_folder"], "to": s["dest_label"]}
            for s in successful
        ]
        rename_details = [
            {
                "file": f"[cartella] {s['current_name']}",
                "from": s["current_name"],
                "to": s.get("final_name", s["suggested_name"]),
            }
            for s in renamed
        ]

        entry = {
            "timestamp": datetime.now().isoformat(),
            "type": "MultiSwap",
            "folders": [str(f) for f in self._folders],
            "mode": "Copia" if use_copy else "Sposta",
            "file_count": count,
            "folder_rename_count": rename_count,
            "files": file_details + rename_details,
        }
        self.operation_completed.emit(entry)

    def _on_exec_error(self, idx, msg):
        table_row = self._exec_row_map[idx] if idx < len(self._exec_row_map) else idx
        _mark_row_error(self.table, table_row)


# ── Tab Cronologia ────────────────────────────────────────────────────

class FolderRenameTab(QWidget):
    operation_completed = Signal(dict)

    def __init__(self):
        super().__init__()
        self._worker = None
        self._exec_worker = None
        self._root_folder: Path | None = None
        self._analyzed_items: list[dict] = []
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        folder_layout = QHBoxLayout()
        self.drop_area = DropArea("Trascina una cartella madre qui")
        self.drop_area.folder_dropped.connect(self._set_folder)
        folder_layout.addWidget(self.drop_area, stretch=1)

        self.browse_btn = QPushButton("Sfoglia")
        self.browse_btn.clicked.connect(self._browse_folder)
        folder_layout.addWidget(self.browse_btn)
        layout.addLayout(folder_layout)

        self.path_edit = QLineEdit()
        self.path_edit.setReadOnly(True)
        self.path_edit.setPlaceholderText("Nessuna cartella selezionata")
        layout.addWidget(self.path_edit)

        opts = QHBoxLayout()
        self.include_root_chk = QCheckBox("Includi anche la cartella selezionata")
        opts.addWidget(self.include_root_chk)
        opts.addStretch()

        self.analyze_btn = QPushButton("Analizza nomi")
        self.analyze_btn.setObjectName("accentBtn")
        self.analyze_btn.setEnabled(False)
        self.analyze_btn.clicked.connect(self._start_analyze)
        opts.addWidget(self.analyze_btn)
        layout.addLayout(opts)

        self.table = QTableWidget(0, 7)
        self.table.setHorizontalHeaderLabels([
            "", "Cartella", "Nome proposto", "Confidenza", "Decisione", "File", "Motivo"
        ])
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionMode(QAbstractItemView.NoSelection)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Fixed)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(6, QHeaderView.Stretch)
        self.table.setColumnWidth(0, 40)
        self._select_all_checked = True
        header.sectionClicked.connect(self._toggle_select_all)
        layout.addWidget(self.table, stretch=1)

        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        bottom = QHBoxLayout()
        self.status_label = QLabel("")
        self.status_label.setObjectName("statusLabel")
        bottom.addWidget(self.status_label, stretch=1)

        self.execute_btn = QPushButton("Rinomina")
        self.execute_btn.setObjectName("accentBtn")
        self.execute_btn.setEnabled(False)
        self.execute_btn.clicked.connect(self._start_execute)
        bottom.addWidget(self.execute_btn)
        layout.addLayout(bottom)

    def _set_folder(self, path: str):
        self._root_folder = Path(path)
        self.path_edit.setText(path)
        self.analyze_btn.setEnabled(True)
        self.execute_btn.setEnabled(False)
        self.table.setRowCount(0)
        self._analyzed_items.clear()
        self.status_label.setText("")

    def _browse_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Seleziona cartella madre")
        if folder:
            self._set_folder(folder)

    def _toggle_select_all(self, index):
        if index != 0:
            return
        self._select_all_checked = not self._select_all_checked
        for row in range(self.table.rowCount()):
            item = self.table.item(row, 0)
            if item and (item.flags() & Qt.ItemIsUserCheckable):
                item.setCheckState(Qt.Checked if self._select_all_checked else Qt.Unchecked)

    def _start_analyze(self):
        if not self._root_folder:
            return
        if self._worker is not None and self._worker.isRunning():
            return
        if not is_folder_rename_allowed():
            self.status_label.setText("Rinomina cartelle disabilitata nelle Impostazioni.")
            return
        if not _check_model_ready(self):
            return

        init_classifier(get_selected_tier())
        self.table.setRowCount(0)
        self._analyzed_items.clear()
        self.analyze_btn.setEnabled(False)
        self.execute_btn.setEnabled(False)
        self.browse_btn.setEnabled(False)
        self.include_root_chk.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)
        self.status_label.setText("Analisi nomi cartelle in corso...")

        self._worker = FolderRenameAnalyzeWorker(
            self._root_folder,
            self.include_root_chk.isChecked(),
        )
        self._worker.progress.connect(self._on_analyze_progress)
        self._worker.finished.connect(self._on_analyze_finished)
        self._worker.error.connect(self._on_analyze_error)
        self._worker.start()

    def _on_analyze_progress(
        self, idx, path, current_name, suggested_name, confidence, action, reason, file_count
    ):
        row = self.table.rowCount()
        self.table.insertRow(row)

        should_rename = action == "rename"
        chk = QTableWidgetItem()
        if should_rename:
            chk.setCheckState(Qt.Checked)
            chk.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
        else:
            chk.setCheckState(Qt.Unchecked)
            chk.setFlags(Qt.ItemIsEnabled)
        self.table.setItem(row, 0, chk)

        decision = "Rinomina" if should_rename else "Mantieni"
        values = [
            current_name,
            suggested_name,
            f"{confidence:.2f}",
            decision,
            str(file_count),
            reason,
        ]
        for col, text in enumerate(values, start=1):
            table_item = QTableWidgetItem(text)
            if not should_rename:
                _set_item_colors(table_item, "#7a7a7a", None)
            self.table.setItem(row, col, table_item)

        self._analyzed_items.append({
            "path": path,
            "current_name": current_name,
            "suggested_name": suggested_name,
            "confidence": confidence,
            "action": action,
            "reason": reason,
            "file_count": file_count,
        })
        self.status_label.setText(f"Analisi {idx + 1} cartelle...")

    def _on_analyze_finished(self):
        self._worker = None
        n = len(self._analyzed_items)
        to_rename = sum(1 for item in self._analyzed_items if item["action"] == "rename")
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(100)
        self.status_label.setText(
            f"Analisi completata: {n} cartelle analizzate, {to_rename} rinomine proposte."
        )
        self.analyze_btn.setEnabled(True)
        self.browse_btn.setEnabled(True)
        self.include_root_chk.setEnabled(True)
        self.execute_btn.setEnabled(to_rename > 0)

    def _on_analyze_error(self, msg):
        self._worker = None
        self.progress_bar.setVisible(False)
        self.status_label.setText(f"Errore: {msg}")
        self.analyze_btn.setEnabled(True)
        self.browse_btn.setEnabled(True)
        self.include_root_chk.setEnabled(True)

    def _start_execute(self):
        if not is_folder_rename_allowed():
            self.status_label.setText("Rinomina cartelle disabilitata nelle Impostazioni.")
            return

        selected = []
        self._exec_row_map = []
        self._exec_success_indices = []
        for row in range(self.table.rowCount()):
            item = self.table.item(row, 0)
            entry = self._analyzed_items[row]
            if entry["action"] == "rename" and item.checkState() == Qt.Checked:
                selected.append(entry)
                self._exec_row_map.append(row)

        if not selected:
            self.status_label.setText("Nessuna cartella selezionata.")
            return

        self.execute_btn.setEnabled(False)
        self.analyze_btn.setEnabled(False)
        self.browse_btn.setEnabled(False)
        self.include_root_chk.setEnabled(False)
        self.progress_bar.setRange(0, len(selected))
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(True)
        self.status_label.setText("Rinomina cartelle in corso...")

        self._exec_worker = FolderRenameExecuteWorker(selected)
        self._exec_worker.progress.connect(self._on_exec_progress)
        self._exec_worker.finished.connect(lambda count: self._on_exec_finished(count, selected))
        self._exec_worker.error.connect(self._on_exec_error)
        self._exec_worker.start()

    def _on_exec_progress(self, idx, dest):
        if not hasattr(self, "_exec_success_indices"):
            self._exec_success_indices = []
        self._exec_success_indices.append(idx)
        self.progress_bar.setValue(len(self._exec_success_indices))
        total = self.progress_bar.maximum()
        self.status_label.setText(f"Rinomina {len(self._exec_success_indices)}/{total}...")

    def _on_exec_finished(self, count, selected):
        self._exec_worker = None
        self.status_label.setText(f"Completato! {count} cartelle rinominate.")
        self.analyze_btn.setEnabled(True)
        self.browse_btn.setEnabled(True)
        self.include_root_chk.setEnabled(True)
        self.progress_bar.setValue(self.progress_bar.maximum())

        success_indices = getattr(self, "_exec_success_indices", [])
        successful = [selected[i] for i in success_indices if i < len(selected)]
        entry = {
            "timestamp": datetime.now().isoformat(),
            "type": "Rinomina cartelle",
            "folders": [str(self._root_folder)] if self._root_folder else [],
            "mode": "Rename",
            "file_count": count,
            "files": [
                {"file": s["current_name"], "from": s["current_name"], "to": s["suggested_name"]}
                for s in successful
            ],
        }
        self.operation_completed.emit(entry)

    def _on_exec_error(self, idx, msg):
        table_row = self._exec_row_map[idx] if idx < len(self._exec_row_map) else idx
        _mark_row_error(self.table, table_row)


class HistoryTab(QWidget):
    def __init__(self):
        super().__init__()
        self._history: list[dict] = load_history()
        self._init_ui()
        self._populate()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Data/Ora", "Tipo", "Cartella(e)", "File", "Modalità"])
        self.tree.setAlternatingRowColors(True)
        header = self.tree.header()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        layout.addWidget(self.tree, stretch=1)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        self.clear_btn = QPushButton("Cancella cronologia")
        self.clear_btn.clicked.connect(self._clear_history)
        btn_layout.addWidget(self.clear_btn)
        layout.addLayout(btn_layout)

    def _populate(self):
        self.tree.clear()
        for entry in reversed(self._history):
            ts = entry.get("timestamp", "")
            try:
                dt = datetime.fromisoformat(ts)
                ts_display = dt.strftime("%d/%m/%Y %H:%M")
            except Exception:
                ts_display = ts

            folders_str = ", ".join(entry.get("folders", []))
            file_count = entry.get("file_count", 0)
            folder_rename_count = entry.get("folder_rename_count", 0)
            count_display = str(file_count)
            if folder_rename_count:
                count_display = f"{file_count} + {folder_rename_count} cartelle"
            top = QTreeWidgetItem([
                ts_display,
                entry.get("type", ""),
                folders_str,
                count_display,
                entry.get("mode", ""),
            ])

            for f in entry.get("files", []):
                if "category" in f:
                    detail = f"{f['file']}  →  {f['category']}"
                elif "from" in f and "to" in f:
                    detail = f"{f['file']}  :  {f['from']}  →  {f['to']}"
                else:
                    detail = f.get("file", "")
                child = QTreeWidgetItem([detail, "", "", "", ""])
                top.addChild(child)

            self.tree.addTopLevelItem(top)

    def add_entry(self, entry: dict):
        self._history.append(entry)
        save_history(self._history)
        self._populate()

    def _clear_history(self):
        reply = QMessageBox.question(
            self, "Conferma",
            "Cancellare tutta la cronologia?",
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            self._history.clear()
            save_history(self._history)
            self._populate()


# ── Tab Impostazioni ─────────────────────────────────────────────────

class SettingsTab(QWidget):
    def __init__(self):
        super().__init__()
        self._download_worker = None
        self._active_download_tier: str | None = None
        self._download_started_at = 0.0
        self._hw_info = None
        self._tier_radios: dict[str, QRadioButton] = {}
        self._tier_status_labels: dict[str, QLabel] = {}
        self._init_ui()
        self._detect_hardware()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(16)

        # ── Sezione Hardware Rilevato ──
        hw_group = QGroupBox("Hardware Rilevato")
        hw_layout = QVBoxLayout(hw_group)

        self.hw_cpu_label = QLabel("CPU: ...")
        self.hw_ram_label = QLabel("RAM: ...")
        self.hw_gpu_label = QLabel("GPU: ...")
        hw_layout.addWidget(self.hw_cpu_label)
        hw_layout.addWidget(self.hw_ram_label)
        hw_layout.addWidget(self.hw_gpu_label)

        hw_btn_layout = QHBoxLayout()
        hw_btn_layout.addStretch()
        self.detect_btn = QPushButton("Rileva di nuovo")
        self.detect_btn.clicked.connect(self._detect_hardware)
        hw_btn_layout.addWidget(self.detect_btn)
        hw_layout.addLayout(hw_btn_layout)

        layout.addWidget(hw_group)

        # ── Sezione Modello AI ──
        model_group = QGroupBox("Modello AI")
        model_layout = QVBoxLayout(model_group)

        self._tier_btn_group = QButtonGroup(self)
        current_tier = get_selected_tier()

        for tier_key, info in MODELS.items():
            row = QHBoxLayout()

            radio = QRadioButton()
            radio.setChecked(tier_key == current_tier)
            self._tier_btn_group.addButton(radio)
            self._tier_radios[tier_key] = radio
            row.addWidget(radio)

            size_gb = info["size_bytes"] / (1024 ** 3)
            tier_label = QLabel(
                f"<b>{tier_key.capitalize()}</b> — {info['name']} ({size_gb:.1f} GB)"
            )
            tier_label.setTextFormat(Qt.RichText)
            row.addWidget(tier_label, stretch=1)

            status_label = QLabel("")
            status_label.setObjectName("statusLabel")
            self._tier_status_labels[tier_key] = status_label
            row.addWidget(status_label)

            model_layout.addLayout(row)

        # Connetti cambio selezione
        self._tier_btn_group.buttonClicked.connect(self._on_tier_changed)

        layout.addWidget(model_group)

        # ── Sezione Download ──
        dl_group = QGroupBox("Download Modello")
        dl_layout = QVBoxLayout(dl_group)

        dl_btn_row = QHBoxLayout()
        self.download_btn = QPushButton("Scarica modello")
        self.download_btn.setObjectName("accentBtn")
        self.download_btn.clicked.connect(self._start_download)
        dl_btn_row.addWidget(self.download_btn)

        self.delete_btn = QPushButton("Elimina modello")
        self.delete_btn.clicked.connect(self._delete_model)
        dl_btn_row.addWidget(self.delete_btn)
        dl_btn_row.addStretch()
        dl_layout.addLayout(dl_btn_row)

        self.dl_progress = QProgressBar()
        self.dl_progress.setVisible(False)
        dl_layout.addWidget(self.dl_progress)

        self.dl_status = QLabel("")
        self.dl_status.setObjectName("statusLabel")
        dl_layout.addWidget(self.dl_status)

        layout.addWidget(dl_group)

        # ── Sezione GPU ──
        gpu_group = QGroupBox("Inferenza GPU")
        gpu_layout = QVBoxLayout(gpu_group)

        config = load_config()
        self.gpu_checkbox = QCheckBox("Usa GPU per inferenza (se disponibile)")
        self.gpu_checkbox.setChecked(config.get("gpu_offload", True))
        self.gpu_checkbox.stateChanged.connect(self._on_gpu_toggle)
        gpu_layout.addWidget(self.gpu_checkbox)

        gpu_info = QLabel("La GPU accelera la classificazione dei file. Se disattivata, viene usata la CPU.")
        gpu_info.setObjectName("statusLabel")
        gpu_info.setWordWrap(True)
        gpu_layout.addWidget(gpu_info)

        layout.addWidget(gpu_group)

        rename_group = QGroupBox("Rinomina cartelle")
        rename_layout = QVBoxLayout(rename_group)

        self.rename_checkbox = QCheckBox("Consenti rinomina cartelle")
        self.rename_checkbox.setChecked(config.get("allow_folder_rename", False))
        self.rename_checkbox.stateChanged.connect(self._on_folder_rename_toggle)
        rename_layout.addWidget(self.rename_checkbox)

        rename_info = QLabel(
            "Quando attiva, la tab Rinomina cartelle e le opzioni di Swap/MultiSwap "
            "possono proporre nuovi nomi in base ai file contenuti. Le rinomine "
            "restano sempre selettive e confermate."
        )
        rename_info.setObjectName("statusLabel")
        rename_info.setWordWrap(True)
        rename_layout.addWidget(rename_info)

        layout.addWidget(rename_group)

        # ── Sezione Log ──
        log_group = QGroupBox("Log")
        log_layout = QVBoxLayout(log_group)

        log_btn_row = QHBoxLayout()
        self.open_logs_btn = QPushButton("Apri cartella log")
        self.open_logs_btn.clicked.connect(self._open_logs_folder)
        log_btn_row.addWidget(self.open_logs_btn)
        log_btn_row.addStretch()
        log_layout.addLayout(log_btn_row)

        log_info = QLabel(
            "I log contengono cronologia spostamenti (moves.log), eventi e errori (app.log). "
            "Utili per verificare cosa e' stato fatto o diagnosticare problemi."
        )
        log_info.setObjectName("statusLabel")
        log_info.setWordWrap(True)
        log_layout.addWidget(log_info)

        layout.addWidget(log_group)

        layout.addStretch()

    def _open_logs_folder(self):
        """Apre la cartella dei log con il file manager del sistema."""
        logs_dir = get_logs_dir()
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(logs_dir)))

    def _detect_hardware(self):
        self._hw_info = detect_hardware()
        hw = self._hw_info

        self.hw_cpu_label.setText(f"CPU: {hw['cpu_name']}")
        self.hw_ram_label.setText(
            f"RAM: {hw['ram_total_gb']} GB totali, {hw['ram_available_gb']} GB disponibili"
        )
        if hw["gpu_name"]:
            self.hw_gpu_label.setText(
                f"GPU: {hw['gpu_name']} — VRAM: {hw['vram_total_gb']} GB totali, "
                f"{hw['vram_available_gb']} GB disponibili"
            )
            self.gpu_checkbox.setEnabled(True)
        else:
            self.hw_gpu_label.setText("GPU: Non rilevata (inferenza solo CPU)")
            self.gpu_checkbox.setEnabled(False)
            self.gpu_checkbox.blockSignals(True)
            self.gpu_checkbox.setChecked(False)
            self.gpu_checkbox.blockSignals(False)

        self._update_tier_status()

    def _update_tier_status(self):
        """Aggiorna lo stato visivo di ogni tier (disponibile, scaricato, consigliato, bloccato)."""
        if self._hw_info is None:
            return

        tiers = get_available_tiers(self._hw_info)
        for t in tiers:
            tier_key = t["tier"]
            radio = self._tier_radios.get(tier_key)
            status_lbl = self._tier_status_labels.get(tier_key)
            if not radio or not status_lbl:
                continue

            parts = []
            if t["recommended"]:
                parts.append("Consigliato")
            if is_model_downloaded(tier_key):
                parts.append("Scaricato")

            if not t["available"]:
                radio.setEnabled(False)
                status_lbl.setText("BLOCCATO — RAM insufficiente")
            else:
                radio.setEnabled(True)
                status_lbl.setText(" | ".join(parts) if parts else "")

        self._update_download_buttons()

    def _update_download_buttons(self):
        """Abilita/disabilita i bottoni download/elimina in base al tier selezionato."""
        tier = self._get_selected_tier_key()
        downloaded = is_model_downloaded(tier)
        self.download_btn.setEnabled(not downloaded and self._download_worker is None)
        self.delete_btn.setEnabled(downloaded)

    def _get_selected_tier_key(self) -> str:
        for tier_key, radio in self._tier_radios.items():
            if radio.isChecked():
                return tier_key
        return "standard"

    def _on_tier_changed(self, _btn):
        tier = self._get_selected_tier_key()
        set_selected_tier(tier)
        # Scarica il modello precedente dalla memoria per liberare RAM
        unload_model()
        self._update_download_buttons()

    def _on_gpu_toggle(self, state):
        config = load_config()
        config["gpu_offload"] = bool(state)
        save_config(config)
        # Scarica il modello dalla memoria cosi' al prossimo uso ricarica con la nuova impostazione
        unload_model()

    def _on_folder_rename_toggle(self, state):
        set_folder_rename_allowed(bool(state))

    def _start_download(self):
        # Anti-doppio-click: se un download e' gia' in corso, ignora
        if self._download_worker is not None and self._download_worker.isRunning():
            return

        tier = self._get_selected_tier_key()
        if is_model_downloaded(tier):
            self.dl_status.setText("Modello gia' scaricato.")
            return

        # Pulizia leftover di download precedenti falliti (lock orfani, file vuoti)
        self._cleanup_download_leftovers(tier)

        info = MODELS[tier]
        size_gb = info["size_bytes"] / (1024 ** 3)
        self.dl_status.setText(f"Download in corso: {info['name']} (0.0 / {size_gb:.1f} GB)...")
        self.dl_progress.setVisible(True)
        self.dl_progress.setRange(0, 100)
        self.dl_progress.setValue(0)
        self.download_btn.setEnabled(False)
        self.delete_btn.setEnabled(False)

        self._active_download_tier = tier
        self._download_started_at = datetime.now().timestamp()
        self._download_worker = ModelDownloadWorker(tier)
        self._download_worker.finished.connect(self._on_download_finished)
        self._download_worker.error.connect(self._on_download_error)
        self._download_worker.start()
        self._start_progress_timer()

    def _cleanup_download_leftovers(self, tier: str):
        """Rimuove .lock e .incomplete vuoti rimasti da download falliti."""
        info = MODELS[tier]
        download_dir = get_models_dir() / ".cache" / "huggingface" / "download"
        if not download_dir.exists():
            return
        for f in download_dir.iterdir():
            try:
                if not f.is_file():
                    continue
                # Rimuovi lock vuoti del modello corrente
                if f.name.endswith(".lock") and info["filename"] in f.name:
                    f.unlink(missing_ok=True)
                # Rimuovi incomplete vuoti (di qualsiasi modello)
                elif f.name.endswith(".incomplete") and f.stat().st_size == 0:
                    f.unlink(missing_ok=True)
            except (OSError, PermissionError):
                # File ancora in uso da altro processo: ignora
                pass

    def _start_progress_timer(self):
        if not hasattr(self, '_progress_timer'):
            self._progress_timer = QTimer(self)
            self._progress_timer.timeout.connect(self._update_dl_progress)
        self._progress_timer.start(500)

    def _update_dl_progress(self):
        if not self._download_worker:
            self._progress_timer.stop()
            return

        tier = self._download_worker.tier
        if self._active_download_tier and tier != self._active_download_tier:
            return
        info = MODELS[tier]
        total_size = info["size_bytes"]
        models_dir = get_models_dir()
        final_file = models_dir / info["filename"]

        # huggingface_hub salva il file in download come .incomplete con un
        # hash nel nome, dentro <models_dir>/.cache/huggingface/download/
        download_dir = models_dir / ".cache" / "huggingface" / "download"
        partials: list[int] = []
        if download_dir.exists():
            try:
                for f in download_dir.iterdir():
                    if not f.name.endswith(".incomplete"):
                        continue
                    try:
                        stat = f.stat()
                    except (OSError, PermissionError):
                        continue
                    if stat.st_size <= 0:
                        continue
                    is_current_file = info["filename"] in f.name
                    is_recent_file = (
                        self._download_started_at > 0
                        and stat.st_mtime >= self._download_started_at - 2
                    )
                    if is_current_file or is_recent_file:
                        partials.append(stat.st_size)
            except (OSError, PermissionError):
                pass

        if partials:
            # Prendi il piu' grande (probabilmente il download in corso)
            downloaded_size = max(partials)
            perc = min(int((downloaded_size / total_size) * 100), 100)
            self.dl_progress.setValue(perc)
            mb_down = downloaded_size / (1024 * 1024)
            mb_tot = total_size / (1024 * 1024)
            self.dl_status.setText(
                f"Download in corso: {info['name']} ({mb_down:.1f} / {mb_tot:.1f} MB)..."
            )
        elif final_file.exists():
            self.dl_progress.setValue(100)
            self.dl_status.setText("Completamento in corso...")
        else:
            # Lock acquisito ma file non ancora creato: in attesa risposta server
            self.dl_status.setText(f"Inizializzazione download: {info['name']}...")

    def _on_download_finished(self, _path):
        if hasattr(self, '_progress_timer'):
            self._progress_timer.stop()
        self._download_worker = None
        self._active_download_tier = None
        self._download_started_at = 0.0
        self.dl_progress.setRange(0, 100)
        self.dl_progress.setValue(100)
        self.dl_status.setText(f"Modello pronto!")
        self._update_tier_status()

    def _on_download_error(self, msg):
        if hasattr(self, '_progress_timer'):
            self._progress_timer.stop()
        self._download_worker = None
        self._active_download_tier = None
        self._download_started_at = 0.0
        self.dl_progress.setVisible(False)
        self.dl_status.setText(f"Errore: {msg}")
        self._update_download_buttons()

    def _delete_model(self):
        tier = self._get_selected_tier_key()
        if not is_model_downloaded(tier):
            return

        reply = QMessageBox.question(
            self, "Conferma eliminazione",
            f"Eliminare il modello {MODELS[tier]['name']}?\n\n"
            "Dovrai scaricarlo di nuovo per usarlo.",
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            unload_model()
            delete_model(tier)
            self.dl_status.setText("Modello eliminato.")
            self.dl_progress.setVisible(False)
            self._update_tier_status()


# ── Finestra principale ───────────────────────────────────────────────

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Agent Ordinatore")
        self.setWindowIcon(QIcon(str(_resource_path("icon.ico"))))
        self.resize(920, 660)

        self._dark = get_theme() == "dark"

        # Widget centrale
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(8, 8, 8, 8)

        # Header con titolo e toggle tema
        header = QHBoxLayout()
        title = QLabel("Agent Ordinatore")
        title.setStyleSheet("font-size: 18px; font-weight: bold; font-family: 'Segoe UI';")
        header.addWidget(title)
        header.addStretch()

        self.theme_btn = QPushButton()
        self.theme_btn.setFixedSize(36, 36)
        self.theme_btn.setCursor(Qt.PointingHandCursor)
        self.theme_btn.clicked.connect(self._toggle_theme)
        header.addWidget(self.theme_btn)
        main_layout.addLayout(header)

        # Tabs
        self.tabs = QTabWidget()
        self.organize_tab = OrganizeTab()
        self.swap_tab = SwapTab()
        self.multi_swap_tab = MultiSwapTab()
        self.folder_rename_tab = FolderRenameTab()
        self.history_tab = HistoryTab()
        self.settings_tab = SettingsTab()

        self.tabs.addTab(self.organize_tab, "Organizza")
        self.tabs.addTab(self.swap_tab, "Swap")
        self.tabs.addTab(self.multi_swap_tab, "Swap multiplo")
        self.tabs.addTab(self.folder_rename_tab, "Rinomina cartelle")
        self.tabs.addTab(self.history_tab, "Cronologia")
        self.tabs.addTab(self.settings_tab, "Impostazioni")
        main_layout.addWidget(self.tabs)

        # Collega segnali cronologia
        self.organize_tab.operation_completed.connect(self.history_tab.add_entry)
        self.swap_tab.operation_completed.connect(self.history_tab.add_entry)
        self.multi_swap_tab.operation_completed.connect(self.history_tab.add_entry)
        self.folder_rename_tab.operation_completed.connect(self.history_tab.add_entry)

        self._apply_theme()

        # Primo avvio: se nessun modello scaricato, apri tab Impostazioni
        if not get_downloaded_models():
            self.tabs.setCurrentWidget(self.settings_tab)

    def _toggle_theme(self):
        self._dark = not self._dark
        set_theme("dark" if self._dark else "light")
        self._apply_theme()

    def _apply_theme(self):
        qss = DARK_THEME if self._dark else LIGHT_THEME
        QApplication.instance().setStyleSheet(qss)
        self.theme_btn.setText("☀" if self._dark else "🌙")

    def _running_workers(self) -> list[QThread]:
        workers = [
            self.organize_tab._worker,
            self.organize_tab._exec_worker,
            self.swap_tab._worker,
            self.swap_tab._exec_worker,
            self.swap_tab._rename_worker,
            self.multi_swap_tab._worker,
            self.multi_swap_tab._exec_worker,
            self.multi_swap_tab._rename_worker,
            self.folder_rename_tab._worker,
            self.folder_rename_tab._exec_worker,
            self.settings_tab._download_worker,
        ]
        return [worker for worker in workers if worker is not None and worker.isRunning()]

    def _stop_worker(self, worker: QThread, timeout_ms: int = 3000) -> bool:
        worker.requestInterruption()
        worker.quit()
        return worker.wait(timeout_ms)

    def closeEvent(self, event):
        running_workers = self._running_workers()
        if running_workers:
            started_at = datetime.now()
            log.info("closeEvent: stopping %d running workers...", len(running_workers))
            all_stopped = True
            for worker in running_workers:
                if not self._stop_worker(worker):
                    all_stopped = False

            if not all_stopped:
                log.warning("closeEvent: worker shutdown timed out")
                event.ignore()
                QMessageBox.warning(
                    self,
                    "Operazione in corso",
                    "Attendi la fine dell'operazione corrente prima di chiudere l'app.",
                )
                return
            elapsed = (datetime.now() - started_at).total_seconds()
            log.info("closeEvent: all workers stopped (took %.1fs)", elapsed)

        if hasattr(self.settings_tab, "_progress_timer"):
            self.settings_tab._progress_timer.stop()
        unload_model()
        super().closeEvent(event)
        QApplication.quit()


# ── Entry point ───────────────────────────────────────────────────────

if __name__ == "__main__":
    import traceback as _traceback
    import os as _os

    def _on_startup_error(exc: Exception) -> None:
        """Logga su file e mostra un QMessageBox prima di chiudersi."""
        tb_str = _traceback.format_exc()

        # — Scrivi il log su disco ——————————————————————————————
        log_path = "avvio_error.log"
        try:
            log_dir = Path(_os.environ.get("LOCALAPPDATA", str(Path.home()))) / "AgentOrdinatore"
            log_dir.mkdir(parents=True, exist_ok=True)
            log_file = log_dir / "avvio_error.log"
            log_file.write_text(
                f"[{datetime.now().isoformat()}]\n\n{tb_str}",
                encoding="utf-8",
            )
            log_path = str(log_file)
        except Exception:
            pass

        # — Mostra QMessageBox (crea QApplication minimale se non esiste) ——
        try:
            QApplication.instance() or QApplication(sys.argv)
            QMessageBox.critical(
                None,
                "Errore di avvio — Agent Ordinatore",
                f"L'applicazione non e' riuscita ad avviarsi.\n\n"
                f"Errore:\n{exc}\n\n"
                f"Log completo salvato in:\n{log_path}\n\n"
                f"Suggerimento: esegui 'avvia_debug.bat' per vedere\n"
                f"l'errore nella console.",
            )
        except Exception:
            pass

    try:
        app = QApplication(sys.argv)
        app.setFont(QFont("Segoe UI", 10))
        window = MainWindow()
        window.show()
        sys.exit(app.exec())
    except Exception as e:
        _on_startup_error(e)
        sys.exit(1)
