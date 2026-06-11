"""
brain.py — Classificazione intelligente dei file.

Usa un modello locale Qwen3.5 (GGUF) tramite llama-cpp-python
oppure DeepSeek via API.
"""

import json
import re
import subprocess
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from model_manager import MODELS, get_model_path
from utils import format_size, sanitize_category, sanitize_folder_name
from logger import get_app_logger
from config import (
    AI_BACKEND_DEEPSEEK,
    AI_BACKEND_LOCAL,
    DEEPSEEK_MODELS,
    get_ai_backend,
    get_deepseek_api_key,
    get_deepseek_model,
    get_selected_tier,
)

_log = get_app_logger()


# ── Strategia per tier ──────────────────────────────────────────────
# chunk_size   : dimensione massima del chunk del torneo nel multi-swap
# n_ctx        : context window passata a llama-cpp (KV cache cresce lineare)
# sample_files : numero massimo di nomi file campione mostrati al modello
#                per ogni cartella (sia binary swap che multi-swap)

TIER_STRATEGY = {
    "lite":     {"chunk_size": 2, "n_ctx": 4096,  "sample_files": 10},
    "standard": {"chunk_size": 4, "n_ctx": 8192,  "sample_files": 20},
    "pro":      {"chunk_size": 6, "n_ctx": 8192,  "sample_files": 25},
    "ultra":    {"chunk_size": 8, "n_ctx": 16384, "sample_files": 30},
}

DEEPSEEK_STRATEGY = {
    "deepseek-v4-flash": {"chunk_size": 8, "sample_files": 30},
    "deepseek-v4-pro": {"chunk_size": 10, "sample_files": 40},
}


def get_tier_strategy(tier: str) -> dict:
    """Ritorna la strategia per il tier indicato, fallback su 'standard'."""
    return TIER_STRATEGY.get(tier, TIER_STRATEGY["standard"])


def get_deepseek_strategy(model: str) -> dict:
    """Ritorna la strategia per il modello DeepSeek indicato."""
    return DEEPSEEK_STRATEGY.get(model, DEEPSEEK_STRATEGY["deepseek-v4-flash"])


# ── Prompt di sistema per il modello locale ─────────────────────────

CLASSIFY_SYSTEM_PROMPT = """You are a file classifier. Given a filename and size, respond with ONLY a JSON object.
Rules:
- Respond ONLY with valid JSON, no other text
- Format: {"category": "FolderName/SubfolderName"}
- Use 1-2 levels max (e.g. "Images/Photos", "Documents/PDF", "Code/Python")
- 0 byte files go in "Corrupted/Empty"
- Categories in Italian or English based on filename language

Examples:
filename: "foto_vacanza_2024.jpg", size: "2.5 MB" -> {"category": "Immagini/Foto"}
filename: "report_Q3.xlsx", size: "145 KB" -> {"category": "Documenti/Fogli di calcolo"}
filename: "backup.tar.gz", size: "1.2 GB" -> {"category": "Archivi/Backup"}
filename: "main.py", size: "8 KB" -> {"category": "Codice/Python"}
filename: "song.mp3", size: "4.1 MB" -> {"category": "Audio/Musica"}
filename: "empty_file.dat", size: "0 B" -> {"category": "Corrotti/Vuoti"}"""

SWAP_SYSTEM_PROMPT = """You classify which folder a file belongs to. Given a filename, its size, two folder names, and their contents, respond ONLY with "A" or "B".
Rules:
- Respond with ONLY the letter A or B, nothing else
- Choose based on which folder's contents are most similar to the file
- Consider file extensions, naming patterns, and themes

Example:
File: "photo_beach.jpg" (3.2 MB)
Folder A "Vacanze": [sunset.jpg, mare.png, hotel.pdf]
Folder B "Lavoro": [report.docx, budget.xlsx, meeting.pdf]
-> A"""

MULTI_SWAP_SYSTEM_PROMPT = """You classify which folder a file belongs to. Given a filename, its size, and a numbered list of folders with their contents, respond ONLY with the index number of the best folder.
Rules:
- Respond with ONLY a single integer (the index), nothing else
- The index must be one of the listed indices (0, 1, 2, ...)
- Choose based on which folder's contents are most similar to the file
- Consider file extensions, naming patterns, themes, and folder name

Example with 2 folders:
File: "photo_beach.jpg" (3.2 MB)
0: Vacanze (D:/foto/Vacanze) -> [sunset.jpg, mare.png, hotel.pdf]
1: Lavoro (D:/docs/Lavoro) -> [report.docx, budget.xlsx, meeting.pdf]
-> 0

Example with 4 folders:
File: "main.py" (8 KB)
0: Documenti (C:/Users/me/Documenti) -> [cv.pdf, lettera.docx]
1: Codice (D:/dev/Codice) -> [app.js, server.py, README.md]
2: Foto (E:/media/Foto) -> [vacanza.jpg, ritratto.png]
3: Musica (E:/media/Musica) -> [song.mp3, album.flac]
-> 1

Example with 3 folders:
File: "report_Q3.xlsx" (145 KB)
0: Vacanze2024 (D:/foto/Vacanze2024) -> [mare.jpg, hotel.pdf]
1: Lavoro (D:/docs/Lavoro) -> [budget.xlsx, contratto.pdf]
2: Backup (E:/backup) -> [archive.tar.gz, dump.sql]
-> 1"""

FOLDER_RENAME_SYSTEM_PROMPT = """You suggest whether a folder should keep its current name or be renamed based on its file names.
Respond ONLY with valid JSON, no other text.

Rules:
- Output format: {"action":"keep|rename","suggested_name":"Single Folder Name","confidence":0.0,"reason":"short reason"}
- The suggested_name must be a single folder name, not a path.
- Do not suggest renaming project folders or intentional names unless the content is clearly different.
- If the current name is coherent with the contents, use action "keep".
- If the current name is generic/confusing and contents are homogeneous, use action "rename".
- Prefer concise Italian names when file names look Italian, otherwise concise English names.
- Never use reserved Windows names, slashes, drive letters, or punctuation-heavy names.

Examples:
Current folder: "Video"
Weak name: false
Project markers: []
Extensions: {".mp4": 12, ".mkv": 3}
Files: [vacanza.mp4, compleanno.mkv, clip.mov]
-> {"action":"keep","suggested_name":"Video","confidence":0.92,"reason":"Il nome attuale e' coerente con file video."}

Current folder: "Nuova cartella (2)"
Weak name: true
Project markers: []
Extensions: {".pdf": 9, ".docx": 2}
Files: [fattura_aprile.pdf, bolletta_luce.pdf, contratto_affitto.docx]
-> {"action":"rename","suggested_name":"Amministrazione","confidence":0.86,"reason":"Contiene soprattutto documenti amministrativi."}

Current folder: "Progetto Cliente X"
Weak name: false
Project markers: ["pyproject.toml", ".git"]
Extensions: {".py": 12, ".md": 2}
Files: [main.py, README.md, pyproject.toml]
-> {"action":"keep","suggested_name":"Progetto Cliente X","confidence":0.95,"reason":"Sembra un progetto intenzionale."}"""


# ── Classificatore locale ───────────────────────────────────────────

class LocalClassifier:
    def __init__(self, tier: str = "standard"):
        self.tier = tier
        self.model = None

    def _get_gpu_layers(self) -> int:
        """Ritorna -1 solo se la VRAM libera sembra sufficiente per il tier."""
        required_gb = MODELS[self.tier]["size_bytes"] / (1024 ** 3) + 0.5
        try:
            result = subprocess.run(
                [
                    "nvidia-smi",
                    "--query-gpu=memory.total,memory.free",
                    "--format=csv,noheader,nounits",
                ],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                best_free_gb = 0.0
                for line in result.stdout.strip().splitlines():
                    parts = [p.strip() for p in line.split(",")]
                    if len(parts) < 2:
                        continue
                    best_free_gb = max(best_free_gb, float(parts[1]) / 1024)

                if best_free_gb >= required_gb:
                    return -1

                _log.warning(
                    "GPU offload disattivato: VRAM libera %.1f GB, richiesta stimata %.1f GB",
                    best_free_gb,
                    required_gb,
                )
        except (FileNotFoundError, subprocess.TimeoutExpired, ValueError):
            pass
        return 0

    def _ensure_loaded(self):
        """Carica il modello se non gia' in memoria."""
        if self.model is not None:
            return

        from llama_cpp import Llama

        model_path = get_model_path(self.tier)
        if not model_path.exists():
            _log.error("Modello tier=%s non trovato in %s", self.tier, model_path)
            raise FileNotFoundError(
                f"Modello {self.tier} non scaricato. "
                "Scaricalo prima dalle Impostazioni."
            )

        from config import load_config
        config = load_config()
        gpu_layers = self._get_gpu_layers() if config.get("gpu_offload", True) else 0

        strategy = get_tier_strategy(self.tier)
        n_ctx_target = strategy["n_ctx"]

        _log.info(
            "Caricamento modello tier=%s gpu_layers=%s n_ctx=%d chunk_size=%d sample_files=%d",
            self.tier, gpu_layers, n_ctx_target,
            strategy["chunk_size"], strategy["sample_files"],
        )

        # Tentativo di caricamento con fallback graceful: se il context richiesto
        # non sta in memoria (RAM/VRAM insufficiente), riprova dimezzando finche'
        # non scende sotto un minimo ragionevole.
        n_ctx_min = 2048
        n_ctx = n_ctx_target
        last_exc = None
        while n_ctx >= n_ctx_min:
            try:
                self.model = Llama(
                    model_path=str(model_path),
                    n_ctx=n_ctx,
                    n_threads=None,
                    n_gpu_layers=gpu_layers,
                    verbose=False,
                )
                if n_ctx != n_ctx_target:
                    _log.warning(
                        "Caricamento Llama riuscito con n_ctx=%d (richiesto=%d) dopo fallback",
                        n_ctx, n_ctx_target,
                    )
                else:
                    _log.info("Modello tier=%s caricato (n_ctx=%d)", self.tier, n_ctx)
                self._effective_n_ctx = n_ctx
                return
            except Exception as e:
                last_exc = e
                next_ctx = n_ctx // 2
                if next_ctx < n_ctx_min:
                    break
                _log.warning(
                    "Caricamento Llama con n_ctx=%d fallito (%s), retry con n_ctx=%d",
                    n_ctx, type(e).__name__, next_ctx,
                )
                n_ctx = next_ctx

        if last_exc is not None:
            _log.error(
                "Caricamento modello fallito (tier=%s, n_ctx=%d)",
                self.tier,
                n_ctx_target,
                exc_info=(type(last_exc), last_exc, last_exc.__traceback__),
            )
        else:
            _log.error("Caricamento modello fallito (tier=%s, n_ctx=%d)", self.tier, n_ctx_target)
        raise last_exc if last_exc is not None else RuntimeError("Caricamento modello fallito")

    def unload(self):
        """Scarica il modello dalla memoria."""
        self.model = None

    @staticmethod
    def _parse_category(response_text: str) -> str:
        """Estrae la categoria dalla risposta del modello, con fallback robusti."""
        text = response_text.strip()

        # Tentativo 1: parse JSON diretto
        try:
            data = json.loads(text)
            if isinstance(data, dict) and "category" in data:
                return data["category"]
        except json.JSONDecodeError:
            pass

        # Tentativo 2: trova JSON dentro testo sporco
        json_match = re.search(r'\{[^}]+\}', text)
        if json_match:
            try:
                data = json.loads(json_match.group())
                if isinstance(data, dict) and "category" in data:
                    return data["category"]
            except json.JSONDecodeError:
                pass

        # Tentativo 3: cerca pattern "category": "valore"
        cat_match = re.search(r'"category"\s*:\s*"([^"]+)"', text)
        if cat_match:
            return cat_match.group(1)

        _log.warning("Parsing categoria fallito, fallback 'Altro'. Risposta modello: %r", text[:200])
        return "Altro"

    @staticmethod
    def _parse_swap(response_text: str) -> str | None:
        """Estrae A o B dalla risposta. Ritorna None se la risposta e' incerta."""
        text = response_text.strip().upper()
        if text in ("A", "B"):
            return text

        match = re.search(r"\b([AB])\b", text)
        if match:
            return match.group(1)

        _log.warning("Parsing swap ambiguo, classificazione incerta. Risposta modello: %r", text[:200])
        return None

    @staticmethod
    def _parse_index(response_text: str, valid_count: int) -> int | None:
        """
        Estrae un indice intero dalla risposta del modello, con range check.

        Pipeline:
            1) int diretto del testo strip()
            2) regex \\b(\\d+)\\b sul testo
            3) range check: 0 <= idx < valid_count
            4) None con warning se la risposta resta incerta

        Args:
            response_text: testo prodotto dal modello.
            valid_count: numero di opzioni proposte (es. len(folder_specs)).

        Returns:
            Indice intero valido nell'intervallo [0, valid_count - 1], oppure None.
        """
        text = response_text.strip()

        # Tentativo 1: int diretto
        try:
            idx = int(text)
            if 0 <= idx < valid_count:
                return idx
            _log.warning(
                "Indice modello fuori range (got=%d, max=%d) - classificazione incerta. Risposta: %r",
                idx, valid_count - 1, text[:200],
            )
            return None
        except ValueError:
            pass

        # Tentativo 2: regex su numero nel testo
        match = re.search(r"\b(\d+)\b", text)
        if match:
            try:
                idx = int(match.group(1))
                if 0 <= idx < valid_count:
                    return idx
                _log.warning(
                    "Indice modello fuori range (got=%d, max=%d) - classificazione incerta. Risposta: %r",
                    idx, valid_count - 1, text[:200],
                )
                return None
            except ValueError:
                pass

        _log.warning("Parsing indice fallito - classificazione incerta. Risposta modello: %r", text[:200])
        return None

    @staticmethod
    def _parse_folder_rename(response_text: str, current_name: str) -> dict:
        """Estrae una proposta rename cartella da JSON, con fallback keep."""
        text = response_text.strip()
        data = None

        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            json_match = re.search(r"\{[^}]+\}", text)
            if json_match:
                try:
                    data = json.loads(json_match.group())
                except json.JSONDecodeError:
                    data = None

        if not isinstance(data, dict):
            _log.warning("Parsing rename cartella fallito, fallback keep. Risposta: %r", text[:200])
            return {
                "action": "keep",
                "suggested_name": current_name,
                "confidence": 0.0,
                "reason": "Risposta modello non valida.",
            }

        action = str(data.get("action", "keep")).strip().lower()
        if action not in {"keep", "rename"}:
            action = "keep"

        try:
            confidence = float(data.get("confidence", 0.0))
        except (TypeError, ValueError):
            confidence = 0.0
        confidence = max(0.0, min(1.0, confidence))

        suggested = sanitize_folder_name(data.get("suggested_name") or current_name, fallback=current_name)
        reason = str(data.get("reason") or "").strip()
        if not reason:
            reason = "Nessuna motivazione fornita."

        return {
            "action": action,
            "suggested_name": suggested,
            "confidence": confidence,
            "reason": reason[:240],
        }

    def classify_file(self, filename: str, file_size) -> str:
        """Classifica un file e ritorna la categoria."""
        self._ensure_loaded()

        if isinstance(file_size, int):
            size_str = format_size(file_size)
        else:
            size_str = str(file_size) if file_size else "0 B"

        user_message = f'filename: "{filename}", size: "{size_str}"'

        response = self.model.create_chat_completion(
            messages=[
                {"role": "system", "content": CLASSIFY_SYSTEM_PROMPT},
                {"role": "user", "content": user_message},
            ],
            max_tokens=100,
            temperature=0.1,
            stop=["\n\n"],
        )

        result_text = response["choices"][0]["message"]["content"]
        category = sanitize_category(self._parse_category(result_text))
        _log.debug("classify_file: %s (%s) -> %s", filename, size_str, category)
        return category

    def classify_for_swap(
        self, filename, file_size, folder_a_name, folder_b_name,
        folder_a_files, folder_b_files
    ) -> str | None:
        """Classifica per swap. Ritorna 'A', 'B' o None se incerto."""
        self._ensure_loaded()

        if isinstance(file_size, int):
            size_str = format_size(file_size)
        else:
            size_str = str(file_size) if file_size else "0 B"

        sample_files = get_tier_strategy(self.tier)["sample_files"]
        files_a = ", ".join(folder_a_files[:sample_files])
        files_b = ", ".join(folder_b_files[:sample_files])

        user_message = (
            f'File: "{filename}" ({size_str})\n'
            f'Folder A "{folder_a_name}": [{files_a}]\n'
            f'Folder B "{folder_b_name}": [{files_b}]'
        )

        response = self.model.create_chat_completion(
            messages=[
                {"role": "system", "content": SWAP_SYSTEM_PROMPT},
                {"role": "user", "content": user_message},
            ],
            max_tokens=10,
            temperature=0.1,
            stop=["\n"],
        )

        result_text = response["choices"][0]["message"]["content"]
        choice = self._parse_swap(result_text)
        _log.debug("classify_for_swap: %s -> %s", filename, choice)
        return choice

    @staticmethod
    def _short_path(path_str: str, segments: int = 3) -> str:
        """
        Restituisce gli ultimi `segments` segmenti di un path, prefissati con '...'
        se il path ne ha di piu'. Serve per disambiguare cartelle con stesso nome
        nel prompt senza saturare il context con path lunghissimi.
        """
        if not path_str:
            return ""
        # Normalizza separatori
        norm = path_str.replace("\\", "/").rstrip("/")
        parts = [p for p in norm.split("/") if p]
        if len(parts) <= segments:
            # Mantieni il prefisso (es. drive su Windows o '/' su POSIX)
            return path_str
        tail = "/".join(parts[-segments:])
        return f".../{tail}"

    def classify_best_of_n(
        self, filename: str, file_size,
        folder_specs: list[dict],
    ) -> int | None:
        """
        Singola chiamata K-aria: dato un file e una lista di K cartelle candidate,
        ritorna l'indice (0..K-1) della cartella scelta dal modello.

        Args:
            filename: nome del file da classificare.
            file_size: dimensione (int) o stringa formattata.
            folder_specs: lista di dict con chiavi:
                - "name": nome leggibile della cartella
                - "path": path completo (per disambiguare cartelle con stesso nome)
                - "files": lista di nomi file campione (senza il file target)

        Returns:
            Indice intero in [0, len(folder_specs) - 1], oppure None se incerto.
        """
        self._ensure_loaded()

        if not folder_specs:
            raise ValueError("folder_specs vuoto")
        if len(folder_specs) == 1:
            return 0

        if isinstance(file_size, int):
            size_str = format_size(file_size)
        else:
            size_str = str(file_size) if file_size else "0 B"

        sample_files = get_tier_strategy(self.tier)["sample_files"]

        lines = [f'File: "{filename}" ({size_str})']
        for idx, spec in enumerate(folder_specs):
            name = spec.get("name", "")
            short = self._short_path(spec.get("path", ""))
            files_sample = ", ".join((spec.get("files") or [])[:sample_files])
            label = f"{name} ({short})" if short else name
            lines.append(f"{idx}: {label} -> [{files_sample}]")
        user_message = "\n".join(lines)

        response = self.model.create_chat_completion(
            messages=[
                {"role": "system", "content": MULTI_SWAP_SYSTEM_PROMPT},
                {"role": "user", "content": user_message},
            ],
            max_tokens=10,
            temperature=0.1,
            stop=["\n"],
        )
        result_text = response["choices"][0]["message"]["content"]
        idx = self._parse_index(result_text, len(folder_specs))
        if idx is None:
            _log.debug("classify_best_of_n: '%s' -> incerto", filename)
            return None
        _log.debug(
            "classify_best_of_n: '%s' -> idx=%d (%s)",
            filename, idx, folder_specs[idx].get("name", "?"),
        )
        return idx

    def classify_for_multi_swap(
        self, filename: str, file_size,
        folder_specs: list[dict],
        target_path: str | None = None,
    ) -> int | None:
        """
        Decide la cartella di destinazione di un file tra N candidate, usando
        un torneo a chunk se N supera il chunk_size del tier.

        Args:
            filename: nome del file.
            file_size: dimensione.
            folder_specs: lista (almeno 1 elemento) di dict come in classify_best_of_n.
                Il chiamante DEVE gia' aver escluso il file target dai sample
                (per path completo, non solo per nome).
            target_path: opzionale, path completo del file target. Solo per logging.

        Returns:
            Indice intero in [0, len(folder_specs) - 1] della cartella scelta
            nella lista ORIGINALE (non nei chunk), oppure None se incerto.
        """
        self._ensure_loaded()

        n = len(folder_specs)
        if n == 0:
            raise ValueError("folder_specs vuoto")
        if n == 1:
            return 0

        chunk_size = max(2, get_tier_strategy(self.tier)["chunk_size"])

        # Caso semplice: tutto in un chunk solo
        if n <= chunk_size:
            _log.debug(
                "Tournament for '%s' start: %d candidate folders (single chunk)",
                filename, n,
            )
            winner = self.classify_best_of_n(filename, file_size, folder_specs)
            if winner is None:
                _log.debug("MultiSwap: '%s' -> incerto [1 call]", filename)
                return None
            _log.debug(
                "MultiSwap: '%s' -> idx=%d (%s) [1 call]",
                filename, winner, folder_specs[winner].get("name", "?"),
            )
            return winner

        # Torneo a piu' round
        _log.debug(
            "Tournament for '%s' start: %d candidate folders, chunk_size=%d",
            filename, n, chunk_size,
        )

        # Mantieni mappa indice-corrente -> indice-originale
        active_indices = list(range(n))
        round_num = 0
        total_calls = 0

        while len(active_indices) > 1:
            round_num += 1
            next_active: list[int] = []
            chunks_count = (len(active_indices) + chunk_size - 1) // chunk_size

            for ci in range(chunks_count):
                chunk_orig = active_indices[ci * chunk_size:(ci + 1) * chunk_size]
                if len(chunk_orig) == 1:
                    next_active.append(chunk_orig[0])
                    continue
                chunk_specs = [folder_specs[i] for i in chunk_orig]
                local_winner = self.classify_best_of_n(filename, file_size, chunk_specs)
                if local_winner is None:
                    _log.debug(
                        "Tournament round %d chunk %d/%d: %s -> incerto",
                        round_num, ci + 1, chunks_count,
                        [folder_specs[i].get("name", "?") for i in chunk_orig],
                    )
                    return None
                total_calls += 1
                orig_winner = chunk_orig[local_winner]
                _log.debug(
                    "Tournament round %d chunk %d/%d: %s -> winner orig_idx=%d (%s)",
                    round_num, ci + 1, chunks_count,
                    [folder_specs[i].get("name", "?") for i in chunk_orig],
                    orig_winner, folder_specs[orig_winner].get("name", "?"),
                )
                next_active.append(orig_winner)

            active_indices = next_active

        final_idx = active_indices[0]
        _log.debug(
            "MultiSwap: '%s' -> idx=%d (%s) [%d calls, %d rounds]",
            filename, final_idx, folder_specs[final_idx].get("name", "?"),
            total_calls, round_num,
        )
        return final_idx

    def suggest_folder_rename(self, profile: dict) -> dict:
        """
        Suggerisce se rinominare una cartella in base al profilo contenuti.

        Ritorna un dict con action, suggested_name, confidence e reason.
        Le cartelle protette da marker progetto vengono preservate localmente.
        """
        current_name = str(profile.get("current_name") or "Cartella")
        if profile.get("protected"):
            markers = ", ".join(profile.get("project_markers") or [])
            return {
                "action": "keep",
                "suggested_name": current_name,
                "confidence": 1.0,
                "reason": f"Cartella protetta: marker progetto rilevati ({markers}).",
            }

        if int(profile.get("file_count") or 0) == 0:
            return {
                "action": "keep",
                "suggested_name": current_name,
                "confidence": 1.0,
                "reason": "Cartella vuota: rinomina non proposta.",
            }

        self._ensure_loaded()

        extensions = profile.get("extensions") or {}
        files = profile.get("sample_files") or []
        marker_text = ", ".join(profile.get("project_markers") or [])
        extensions_text = json.dumps(extensions, ensure_ascii=False)
        files_text = ", ".join(files)
        user_message = (
            f'Current folder: "{current_name}"\n'
            f"Weak name: {bool(profile.get('weak_name'))}\n"
            f"Project markers: [{marker_text}]\n"
            f"File count: {profile.get('file_count', 0)}\n"
            f"Total size: {profile.get('total_size_str', '')}\n"
            f"Extensions: {extensions_text}\n"
            f"Files: [{files_text}]"
        )

        response = self.model.create_chat_completion(
            messages=[
                {"role": "system", "content": FOLDER_RENAME_SYSTEM_PROMPT},
                {"role": "user", "content": user_message},
            ],
            max_tokens=160,
            temperature=0.1,
            stop=["\n\n"],
        )

        result_text = response["choices"][0]["message"]["content"]
        result = self._parse_folder_rename(result_text, current_name)

        suggested = sanitize_folder_name(result["suggested_name"], fallback=current_name)
        result["suggested_name"] = suggested

        same_name = suggested.lower() == current_name.lower()
        threshold = 0.65 if profile.get("weak_name") else 0.88
        if result["action"] == "rename" and (same_name or result["confidence"] < threshold):
            result["action"] = "keep"
            if same_name:
                result["reason"] = "Il nome suggerito coincide con quello attuale."
            else:
                result["reason"] = (
                    f"Confidenza {result['confidence']:.2f} sotto soglia {threshold:.2f}."
                )

        _log.debug(
            "suggest_folder_rename: %s -> %s %s %.2f",
            current_name, result["action"], result["suggested_name"], result["confidence"],
        )
        return result


# ── Istanza globale e interfaccia pubblica ──────────────────────────

class DeepSeekAPIError(RuntimeError):
    def __init__(self, message: str, recoverable: bool = False):
        super().__init__(message)
        self.recoverable = recoverable


class DeepSeekClassifier:
    """Classificatore remoto DeepSeek compatibile con l'interfaccia locale."""

    BASE_URL = "https://api.deepseek.com/chat/completions"
    FALLBACK_MODEL = "deepseek-v4-pro"

    def __init__(self, model: str = "deepseek-v4-flash", api_key: str | None = None):
        self.model = model if model in DEEPSEEK_MODELS else "deepseek-v4-flash"
        self.tier = self.model
        self.api_key = (api_key or "").strip()
        self.timeout = 60

    def _get_api_key(self) -> str:
        api_key = self.api_key or get_deepseek_api_key()
        if not api_key:
            raise RuntimeError(
                "API key DeepSeek non configurata. Inseriscila nelle Impostazioni "
                "o in un file .env con DEEPSEEK_API_KEY."
            )
        return api_key

    def unload(self):
        """Nessuna risorsa locale da scaricare."""
        return None

    def _can_fallback(self, model: str) -> bool:
        return model == "deepseek-v4-flash"

    @staticmethod
    def _is_recoverable_http_error(code: int, message: str) -> bool:
        if code in {408, 409, 425, 429} or code >= 500:
            return True
        lowered = message.lower()
        recoverable_markers = (
            "busy",
            "model",
            "overload",
            "rate",
            "temporar",
            "timeout",
            "unavailable",
        )
        return code == 400 and any(marker in lowered for marker in recoverable_markers)

    @staticmethod
    def _is_response_usable(response: dict) -> bool:
        return bool(DeepSeekClassifier._message_content(response).strip())

    def _post_chat_fallback(
        self,
        messages: list[dict],
        max_tokens: int,
        temperature: float | None,
        stop: list[str] | None,
    ) -> dict:
        response = self._post_chat_once(
            self.FALLBACK_MODEL,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
            stop=stop,
        )
        if not self._is_response_usable(response):
            raise DeepSeekAPIError("Risposta DeepSeek fallback vuota o non utilizzabile.")
        return response

    def _post_chat(
        self,
        messages: list[dict],
        max_tokens: int,
        temperature: float | None = 0.1,
        stop: list[str] | None = None,
    ) -> dict:
        try:
            response = self._post_chat_once(
                self.model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
                stop=stop,
            )
            if self._is_response_usable(response):
                return response
            if self._can_fallback(self.model):
                _log.warning(
                    "DeepSeek response empty, fallback model=%s -> %s",
                    self.model,
                    self.FALLBACK_MODEL,
                )
                return self._post_chat_fallback(messages, max_tokens, temperature, stop)
            raise DeepSeekAPIError("Risposta DeepSeek vuota o non utilizzabile.")
        except DeepSeekAPIError as exc:
            if not exc.recoverable or not self._can_fallback(self.model):
                raise
            _log.warning(
                "DeepSeek fallback model=%s -> %s: %s",
                self.model,
                self.FALLBACK_MODEL,
                exc,
            )
            return self._post_chat_fallback(messages, max_tokens, temperature, stop)

    def _post_chat_once(
        self,
        model: str,
        messages: list[dict],
        max_tokens: int,
        temperature: float | None = 0.1,
        stop: list[str] | None = None,
    ) -> dict:
        payload = {
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens,
            "stream": False,
            "thinking": {"type": "disabled"},
        }
        if temperature is not None:
            payload["temperature"] = temperature
        if stop:
            payload["stop"] = stop

        body = json.dumps(payload).encode("utf-8")
        request = Request(
            self.BASE_URL,
            data=body,
            headers={
                "Authorization": f"Bearer {self._get_api_key()}",
                "Content-Type": "application/json",
            },
            method="POST",
        )

        try:
            with urlopen(request, timeout=self.timeout) as response:
                raw = response.read().decode("utf-8")
        except HTTPError as exc:
            detail = ""
            try:
                detail = exc.read().decode("utf-8", errors="replace")
            except Exception:
                detail = ""
            message = self._extract_error_message(detail) or exc.reason
            recoverable = self._is_recoverable_http_error(exc.code, message)
            raise DeepSeekAPIError(
                f"DeepSeek API HTTP {exc.code}: {message}",
                recoverable=recoverable,
            ) from exc
        except URLError as exc:
            raise DeepSeekAPIError(
                f"Connessione DeepSeek fallita: {exc.reason}",
                recoverable=True,
            ) from exc
        except TimeoutError as exc:
            raise DeepSeekAPIError("Timeout DeepSeek.", recoverable=True) from exc

        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise DeepSeekAPIError("Risposta DeepSeek non valida.", recoverable=True) from exc

        if "error" in data:
            message = self._extract_error_message(json.dumps(data["error"], ensure_ascii=False))
            recoverable = any(
                marker in message.lower()
                for marker in ("busy", "overload", "rate", "temporar", "timeout", "unavailable")
            )
            raise DeepSeekAPIError(
                f"DeepSeek API: {message or 'errore sconosciuto'}",
                recoverable=recoverable,
            )
        return data

    @staticmethod
    def _extract_error_message(raw: str) -> str:
        if not raw:
            return ""
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            return raw[:240]
        if isinstance(data, dict):
            error = data.get("error", data)
            if isinstance(error, dict):
                return str(error.get("message") or error.get("type") or "")[:240]
            return str(error)[:240]
        return str(data)[:240]

    @staticmethod
    def _message_content(response: dict) -> str:
        try:
            content = response["choices"][0]["message"].get("content", "")
        except (KeyError, IndexError, TypeError, AttributeError):
            content = ""
        if content is None:
            return ""
        return str(content)

    def classify_file(self, filename: str, file_size) -> str:
        if isinstance(file_size, int):
            size_str = format_size(file_size)
        else:
            size_str = str(file_size) if file_size else "0 B"

        user_message = f'filename: "{filename}", size: "{size_str}"'
        response = self._post_chat(
            messages=[
                {"role": "system", "content": CLASSIFY_SYSTEM_PROMPT},
                {"role": "user", "content": user_message},
            ],
            max_tokens=100,
            temperature=0.1,
            stop=["\n\n"],
        )
        result_text = self._message_content(response)
        category = sanitize_category(LocalClassifier._parse_category(result_text))
        _log.debug("deepseek classify_file: %s (%s) -> %s", filename, size_str, category)
        return category

    def classify_for_swap(
        self, filename, file_size, folder_a_name, folder_b_name,
        folder_a_files, folder_b_files
    ) -> str | None:
        if isinstance(file_size, int):
            size_str = format_size(file_size)
        else:
            size_str = str(file_size) if file_size else "0 B"

        sample_files = get_deepseek_strategy(self.model)["sample_files"]
        files_a = ", ".join(folder_a_files[:sample_files])
        files_b = ", ".join(folder_b_files[:sample_files])
        user_message = (
            f'File: "{filename}" ({size_str})\n'
            f'Folder A "{folder_a_name}": [{files_a}]\n'
            f'Folder B "{folder_b_name}": [{files_b}]'
        )

        response = self._post_chat(
            messages=[
                {"role": "system", "content": SWAP_SYSTEM_PROMPT},
                {"role": "user", "content": user_message},
            ],
            max_tokens=10,
            temperature=0.1,
            stop=["\n"],
        )
        choice = LocalClassifier._parse_swap(self._message_content(response))
        _log.debug("deepseek classify_for_swap: %s -> %s", filename, choice)
        return choice

    @staticmethod
    def _short_path(path_str: str, segments: int = 3) -> str:
        return LocalClassifier._short_path(path_str, segments=segments)

    def classify_best_of_n(
        self, filename: str, file_size,
        folder_specs: list[dict],
    ) -> int | None:
        if not folder_specs:
            raise ValueError("folder_specs vuoto")
        if len(folder_specs) == 1:
            return 0

        if isinstance(file_size, int):
            size_str = format_size(file_size)
        else:
            size_str = str(file_size) if file_size else "0 B"

        sample_files = get_deepseek_strategy(self.model)["sample_files"]
        lines = [f'File: "{filename}" ({size_str})']
        for idx, spec in enumerate(folder_specs):
            name = spec.get("name", "")
            short = self._short_path(spec.get("path", ""))
            files_sample = ", ".join((spec.get("files") or [])[:sample_files])
            label = f"{name} ({short})" if short else name
            lines.append(f"{idx}: {label} -> [{files_sample}]")
        user_message = "\n".join(lines)

        response = self._post_chat(
            messages=[
                {"role": "system", "content": MULTI_SWAP_SYSTEM_PROMPT},
                {"role": "user", "content": user_message},
            ],
            max_tokens=10,
            temperature=0.1,
            stop=["\n"],
        )
        idx = LocalClassifier._parse_index(self._message_content(response), len(folder_specs))
        if idx is None:
            _log.debug("deepseek classify_best_of_n: '%s' -> incerto", filename)
            return None
        _log.debug("deepseek classify_best_of_n: '%s' -> idx=%d", filename, idx)
        return idx

    def classify_for_multi_swap(
        self, filename: str, file_size,
        folder_specs: list[dict],
        target_path: str | None = None,
    ) -> int | None:
        n = len(folder_specs)
        if n == 0:
            raise ValueError("folder_specs vuoto")
        if n == 1:
            return 0

        chunk_size = max(2, get_deepseek_strategy(self.model)["chunk_size"])
        if n <= chunk_size:
            return self.classify_best_of_n(filename, file_size, folder_specs)

        active_indices = list(range(n))
        while len(active_indices) > 1:
            next_active: list[int] = []
            for start in range(0, len(active_indices), chunk_size):
                chunk_orig = active_indices[start:start + chunk_size]
                if len(chunk_orig) == 1:
                    next_active.append(chunk_orig[0])
                    continue
                chunk_specs = [folder_specs[i] for i in chunk_orig]
                local_winner = self.classify_best_of_n(filename, file_size, chunk_specs)
                if local_winner is None:
                    return None
                next_active.append(chunk_orig[local_winner])
            active_indices = next_active
        return active_indices[0]

    def suggest_folder_rename(self, profile: dict) -> dict:
        current_name = str(profile.get("current_name") or "Cartella")
        if profile.get("protected"):
            markers = ", ".join(profile.get("project_markers") or [])
            return {
                "action": "keep",
                "suggested_name": current_name,
                "confidence": 1.0,
                "reason": f"Cartella protetta: marker progetto rilevati ({markers}).",
            }

        if int(profile.get("file_count") or 0) == 0:
            return {
                "action": "keep",
                "suggested_name": current_name,
                "confidence": 1.0,
                "reason": "Cartella vuota: rinomina non proposta.",
            }

        extensions = profile.get("extensions") or {}
        files = profile.get("sample_files") or []
        marker_text = ", ".join(profile.get("project_markers") or [])
        extensions_text = json.dumps(extensions, ensure_ascii=False)
        files_text = ", ".join(files[:get_deepseek_strategy(self.model)["sample_files"]])
        user_message = (
            f'Current folder: "{current_name}"\n'
            f"Weak name: {bool(profile.get('weak_name'))}\n"
            f"Project markers: [{marker_text}]\n"
            f"File count: {profile.get('file_count', 0)}\n"
            f"Total size: {profile.get('total_size_str', '')}\n"
            f"Extensions: {extensions_text}\n"
            f"Files: [{files_text}]"
        )

        response = self._post_chat(
            messages=[
                {"role": "system", "content": FOLDER_RENAME_SYSTEM_PROMPT},
                {"role": "user", "content": user_message},
            ],
            max_tokens=160,
            temperature=0.1,
            stop=["\n\n"],
        )

        result = LocalClassifier._parse_folder_rename(
            self._message_content(response),
            current_name,
        )
        suggested = sanitize_folder_name(result["suggested_name"], fallback=current_name)
        result["suggested_name"] = suggested

        same_name = suggested.lower() == current_name.lower()
        threshold = 0.65 if profile.get("weak_name") else 0.88
        if result["action"] == "rename" and (same_name or result["confidence"] < threshold):
            result["action"] = "keep"
            if same_name:
                result["reason"] = "Il nome suggerito coincide con quello attuale."
            else:
                result["reason"] = (
                    f"Confidenza {result['confidence']:.2f} sotto soglia {threshold:.2f}."
                )
        return result


def test_deepseek_connection(model: str | None = None, api_key: str | None = None) -> str:
    """Esegue una chiamata minima a DeepSeek e ritorna il testo di risposta."""
    classifier = DeepSeekClassifier(model=model or get_deepseek_model(), api_key=api_key)
    response = classifier._post_chat(
        messages=[
            {"role": "system", "content": "Rispondi solo con OK."},
            {"role": "user", "content": "Test connessione"},
        ],
        max_tokens=10,
        temperature=0.0,
        stop=["\n"],
    )
    content = classifier._message_content(response).strip()
    return content or "OK"


_classifier = None


def init_classifier(
    tier: str | None = None,
    backend: str | None = None,
    deepseek_model: str | None = None,
):
    """Inizializza il classificatore con il backend configurato."""
    global _classifier
    selected_backend = backend or get_ai_backend()

    if selected_backend == AI_BACKEND_DEEPSEEK:
        model = deepseek_model or get_deepseek_model()
        if (
            _classifier is not None
            and isinstance(_classifier, DeepSeekClassifier)
            and _classifier.model == model
        ):
            return
        if _classifier is not None:
            _classifier.unload()
        _classifier = DeepSeekClassifier(model=model)
        _log.info("Classificatore DeepSeek inizializzato: model=%s", model)
        return

    selected_tier = tier or get_selected_tier()
    if (
        _classifier is not None
        and isinstance(_classifier, LocalClassifier)
        and _classifier.tier == selected_tier
    ):
        return
    if _classifier is not None:
        _classifier.unload()
    _classifier = LocalClassifier(tier=selected_tier)
    _log.info("Classificatore locale inizializzato: tier=%s", selected_tier)


def classify_file(filename: str, file_size="") -> str:
    """Classifica un file e ritorna la categoria."""
    global _classifier
    if _classifier is None:
        init_classifier()
    return _classifier.classify_file(filename, file_size)


def classify_for_swap(
    filename, file_size, folder_a_name, folder_b_name,
    folder_a_files, folder_b_files
) -> str | None:
    """Classifica per swap. Ritorna 'A', 'B' o None se incerto."""
    global _classifier
    if _classifier is None:
        init_classifier()
    return _classifier.classify_for_swap(
        filename, file_size, folder_a_name, folder_b_name,
        folder_a_files, folder_b_files,
    )


def classify_for_multi_swap(
    filename: str, file_size,
    folder_specs: list[dict],
    target_path: str | None = None,
) -> int | None:
    """
    Wrapper modulo: ritorna l'indice della cartella scelta tra N candidate
    usando il torneo a chunk del tier corrente, oppure None se incerto.

    `folder_specs` deve gia' contenere `files` privi del file target.
    """
    global _classifier
    if _classifier is None:
        init_classifier()
    return _classifier.classify_for_multi_swap(
        filename, file_size, folder_specs, target_path=target_path,
    )


def suggest_folder_rename(profile: dict) -> dict:
    """Wrapper modulo: suggerisce se rinominare una cartella."""
    global _classifier
    if _classifier is None:
        init_classifier()
    return _classifier.suggest_folder_rename(profile)


def unload_model():
    """Libera la memoria del modello."""
    global _classifier
    if _classifier:
        _classifier.unload()
