"""
hardware.py — Rilevamento hardware per la selezione del modello AI locale.

Rileva RAM, GPU/VRAM, CPU e OS per suggerire il tier di modello
piu' adatto al sistema dell'utente.
"""

import platform
import subprocess

import psutil


def detect_hardware() -> dict:
    """Rileva le specifiche hardware del sistema."""
    ram = psutil.virtual_memory()
    info = {
        "ram_total_gb": round(ram.total / (1024 ** 3), 1),
        "ram_available_gb": round(ram.available / (1024 ** 3), 1),
        "gpu_name": None,
        "vram_total_gb": None,
        "vram_available_gb": None,
        "os": platform.system(),
        "cpu_name": platform.processor() or "Sconosciuto",
    }

    # Tenta rilevamento GPU NVIDIA via nvidia-smi
    try:
        result = subprocess.run(
            [
                "nvidia-smi",
                "--query-gpu=name,memory.total,memory.free",
                "--format=csv,noheader,nounits",
            ],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            line = result.stdout.strip().split("\n")[0]
            parts = [p.strip() for p in line.split(",")]
            if len(parts) >= 3:
                info["gpu_name"] = parts[0]
                info["vram_total_gb"] = round(float(parts[1]) / 1024, 1)
                info["vram_available_gb"] = round(float(parts[2]) / 1024, 1)
    except (FileNotFoundError, subprocess.TimeoutExpired, ValueError):
        pass

    # Fallback: prova GPUtil se installato
    if info["gpu_name"] is None:
        try:
            import GPUtil
            gpus = GPUtil.getGPUs()
            if gpus:
                gpu = gpus[0]
                info["gpu_name"] = gpu.name
                info["vram_total_gb"] = round(gpu.memoryTotal / 1024, 1)
                info["vram_available_gb"] = round(gpu.memoryFree / 1024, 1)
        except (ImportError, Exception):
            pass

    return info


def get_recommended_tier(hardware: dict) -> str:
    """Ritorna il tier consigliato in base all'hardware rilevato."""
    vram = hardware.get("vram_total_gb") or 0
    ram = hardware.get("ram_total_gb", 0)

    if vram >= 8:
        return "ultra"
    if vram >= 4:
        return "pro"
    if ram >= 32:
        return "ultra"
    if ram >= 16:
        return "pro"
    if ram >= 8:
        return "standard"
    return "lite"


# Definizione tier per la funzione seguente
_TIERS = [
    {"tier": "lite",     "model": "Qwen3.5-0.8B", "ram_required": 4,  "size_gb": 0.5},
    {"tier": "standard", "model": "Qwen3.5-2B",   "ram_required": 6,  "size_gb": 1.3},
    {"tier": "pro",      "model": "Qwen3.5-4B",   "ram_required": 8,  "size_gb": 2.7},
    {"tier": "ultra",    "model": "Qwen3.5-9B",   "ram_required": 16, "size_gb": 5.7},
]


def get_available_tiers(hardware: dict) -> list[dict]:
    """Ritorna la lista dei tier con flag available/recommended/blocked."""
    recommended = get_recommended_tier(hardware)
    ram = hardware.get("ram_total_gb", 0)

    result = []
    for t in _TIERS:
        available = ram >= t["ram_required"]
        result.append({
            "tier": t["tier"],
            "model": t["model"],
            "ram_required": t["ram_required"],
            "size_gb": t["size_gb"],
            "available": available,
            "recommended": t["tier"] == recommended,
        })
    return result
