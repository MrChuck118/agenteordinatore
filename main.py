"""    main.py — Orchestratore dell'agente di organizzazione file.

Uso:
  python main.py organize <cartella>                                  # Dry run (default)
  python main.py organize <cartella> --execute                        # Esecuzione reale
  python main.py organize <cartella> --copy                           # Dry run, modalità copia
  python main.py organize <cartella> --copy --execute                 # Esecuzione reale, copia
  python main.py organize <cartella> --tier pro                       # Usa modello Pro
  python main.py swap <cartella_a> <cartella_b>                       # Dry run swap binario
  python main.py swap <cartella_a> <cartella_b> --execute             # Esecuzione reale swap binario
  python main.py multiswap <c1> <c2> [<c3> ...]                       # Dry run multi-swap
  python main.py multiswap <c1> <c2> <c3> --execute                   # Esecuzione reale multi-swap
  python main.py setup                                                # Mostra hardware e modelli
  python main.py setup --download standard                            # Scarica modello standard
  python main.py setup --list                                         # Lista modelli scaricati
  python main.py setup --delete lite                                  # Elimina modello lite

Il dry run mostra le operazioni che verrebbero eseguite senza toccare il disco.
"""

import argparse
from pathlib import Path

from utils import (
    scan_folder, move_file, copy_file, format_size, sanitize_category,
    build_folder_profile, rename_folder_safe,
)
from brain import (
    classify_file, classify_for_swap, classify_for_multi_swap,
    suggest_folder_rename, init_classifier,
)
from model_manager import (
    MODELS, is_model_downloaded, download_model, delete_model,
    get_downloaded_models,
)
from config import get_selected_tier, is_folder_rename_allowed
from logger import get_app_logger

log = get_app_logger()


def _ensure_model(tier: str) -> bool:
    """Controlla che il modello sia scaricato. Ritorna True se pronto."""
    if is_model_downloaded(tier):
        return True
    print(f"  Modello '{tier}' ({MODELS[tier]['name']}) non scaricato.")
    print(f"  Esegui: python main.py setup --download {tier}")
    return False


def _path_key(path: Path) -> str:
    """Ritorna una chiave path stabile per confronti tra file/cartelle."""
    try:
        return str(path.resolve())
    except OSError:
        return str(path)


def _build_folder_specs(
    folders: list[Path],
    all_files: list[list[dict]],
    origin_idx: int,
    target_path: Path,
) -> list[dict]:
    """Costruisce i sample per multi-swap escludendo il file target per path."""
    target_key = _path_key(target_path)
    specs: list[dict] = []
    for idx, folder in enumerate(folders):
        names: list[str] = []
        for entry in all_files[idx]:
            entry_path = entry["path"]
            if idx == origin_idx and _path_key(entry_path) == target_key:
                continue
            names.append(entry_path.name)
        specs.append({
            "name": folder.name,
            "path": str(folder),
            "files": names,
        })
    return specs


def organize(target_folder: Path, dry_run: bool = True, use_copy: bool = False) -> None:
    """
    Scansiona la cartella, classifica ogni file con l'LLM
    e lo sposta/copia (o simula) nella sottocartella appropriata.
    """
    action = "copia" if use_copy else "spostamento"
    action_emoji = "📋" if use_copy else "➡"
    transfer_fn = copy_file if use_copy else move_file
    action_verb_past = "Copiato" if use_copy else "Spostato"

    log.info("CLI Organize avviato: cartella=%s dry_run=%s copy=%s",
             target_folder, dry_run, use_copy)

    print(f"\n{'=' * 60}")
    print(f"  Agente File Organizer")
    print(f"  Cartella: {target_folder.resolve()}")
    print(f"  Modalità: {'🔍 DRY RUN (simulazione)' if dry_run else '🚀 ESECUZIONE REALE'}")
    print(f"  Operazione: {action_emoji} {action}")
    print(f"{'=' * 60}\n")

    # 1. Scansiona la cartella
    files = scan_folder(target_folder)

    if not files:
        print("  Nessun file trovato nella cartella. Niente da fare!")
        return

    print(f"  Trovati {len(files)} file da classificare.\n")

    # 2. Classifica e (opzionalmente) sposta/copia ogni file
    results: list[dict] = []

    for entry in files:
        file_path = entry["path"]
        file_size = entry["size"]
        size_str = format_size(file_size)

        print(f"  📄 {file_path.name}  ({size_str})")

        # Chiedi all'LLM la categoria
        category = sanitize_category(classify_file(file_path.name, size_str))
        dest_folder = target_folder / category

        print(f"     → Categoria: {category}")

        if dry_run:
            print(f"     → [DRY RUN] Verrebbe {action} in: {dest_folder}/")
        else:
            final_path = transfer_fn(file_path, dest_folder)
            print(f"     {action_emoji} {action_verb_past} in: {final_path}")

        results.append(
            {
                "file": file_path.name,
                "category": category,
                "executed": not dry_run,
            }
        )
        print()

    # 3. Riepilogo finale
    log.info("CLI Organize completato: %d file elaborati", len(results))
    print(f"{'=' * 60}")
    print(f"  Riepilogo: {len(results)} file elaborati.")

    if dry_run:
        print("  ℹ  Nessun file è stato modificato (modalità dry run).")
        print(f"  ➡  Rilancia con --execute per eseguire.")

    print(f"{'=' * 60}\n")


def swap(folder_a: Path, folder_b: Path, dry_run: bool = True, use_copy: bool = False) -> None:
    """
    Analizza il contenuto di due cartelle e sposta/copia i file fuori posto
    nella cartella giusta in base alla "vocazione" di ciascuna.
    """
    action = "copia" if use_copy else "spostamento"
    action_emoji = "📋" if use_copy else "➡"
    transfer_fn = copy_file if use_copy else move_file

    log.info("CLI Swap avviato: A=%s B=%s dry_run=%s copy=%s",
             folder_a, folder_b, dry_run, use_copy)

    print(f"\n{'=' * 60}")
    print(f"  Agente File Organizer — Modalità SWAP")
    print(f"  Cartella A: {folder_a.resolve()}")
    print(f"  Cartella B: {folder_b.resolve()}")
    print(f"  Modalità: {'🔍 DRY RUN (simulazione)' if dry_run else '🚀 ESECUZIONE REALE'}")
    print(f"  Operazione: {action_emoji} {action}")
    print(f"{'=' * 60}\n")

    # 1. Scansiona entrambe le cartelle
    files_a = scan_folder(folder_a)
    files_b = scan_folder(folder_b)

    if not files_a and not files_b:
        print("  Entrambe le cartelle sono vuote. Niente da fare!")
        return

    folder_a_name = folder_a.name
    folder_b_name = folder_b.name
    folder_a_filenames = [e["path"].name for e in files_a]
    folder_b_filenames = [e["path"].name for e in files_b]

    total = len(files_a) + len(files_b)
    print(f"  Trovati {len(files_a)} file in '{folder_a_name}' e {len(files_b)} file in '{folder_b_name}'.")
    print(f"  Analizzo {total} file...\n")

    moved_count = 0
    stayed_count = 0

    # 2. Classifica i file della cartella A
    for entry in files_a:
        file_path = entry["path"]
        size_str = format_size(entry["size"])
        target_key = _path_key(file_path)
        folder_a_sample = [
            e["path"].name for e in files_a
            if _path_key(e["path"]) != target_key
        ]

        destination = classify_for_swap(
            file_path.name, size_str,
            folder_a_name, folder_b_name,
            folder_a_sample, folder_b_filenames,
        )

        if destination is None or destination == "A":
            print(f"  ✅ {file_path.name}: {folder_a_name} → resta in {folder_a_name}")
            stayed_count += 1
        else:
            print(f"  📁 {file_path.name}: {folder_a_name} → {folder_b_name}")
            if not dry_run:
                transfer_fn(file_path, folder_b)
                print(f"     {action_emoji} Eseguito")
            moved_count += 1

    # 3. Classifica i file della cartella B
    for entry in files_b:
        file_path = entry["path"]
        size_str = format_size(entry["size"])
        target_key = _path_key(file_path)
        folder_b_sample = [
            e["path"].name for e in files_b
            if _path_key(e["path"]) != target_key
        ]

        destination = classify_for_swap(
            file_path.name, size_str,
            folder_a_name, folder_b_name,
            folder_a_filenames, folder_b_sample,
        )

        if destination is None or destination == "B":
            print(f"  ✅ {file_path.name}: {folder_b_name} → resta in {folder_b_name}")
            stayed_count += 1
        else:
            print(f"  📁 {file_path.name}: {folder_b_name} → {folder_a_name}")
            if not dry_run:
                transfer_fn(file_path, folder_a)
                print(f"     {action_emoji} Eseguito")
            moved_count += 1

    # 4. Riepilogo finale
    log.info("CLI Swap completato: %d analizzati, %d spostati, %d restano",
             total, moved_count, stayed_count)
    print(f"\n{'=' * 60}")
    print(f"  Riepilogo: {total} file analizzati.")
    print(f"    📁 Da spostare: {moved_count}")
    print(f"    ✅ Già al posto giusto: {stayed_count}")

    if dry_run:
        print("  ℹ  Nessun file è stato modificato (modalità dry run).")
        print(f"  ➡  Rilancia con --execute per eseguire.")

    print(f"{'=' * 60}\n")


def multiswap(folders: list[Path], dry_run: bool = True, use_copy: bool = False) -> None:
    """
    Analizza N cartelle e sposta/copia ogni file nella cartella piu' coerente.

    Usa classify_for_multi_swap(), che internamente applica il torneo a chunk
    in base al tier selezionato.
    """
    action = "copia" if use_copy else "spostamento"
    transfer_fn = copy_file if use_copy else move_file

    log.info(
        "CLI MultiSwap avviato: cartelle=%s dry_run=%s copy=%s",
        [str(folder) for folder in folders], dry_run, use_copy,
    )

    print(f"\n{'=' * 60}")
    print("  Agente File Organizer - Modalita MULTI-SWAP")
    print(f"  Cartelle: {len(folders)}")
    for idx, folder in enumerate(folders):
        print(f"    [{idx}] {folder.resolve()}")
    print(f"  Modalita: {'DRY RUN (simulazione)' if dry_run else 'ESECUZIONE REALE'}")
    print(f"  Operazione: {action}")
    print(f"{'=' * 60}\n")

    all_files = [scan_folder(folder) for folder in folders]
    total = sum(len(files) for files in all_files)
    if total == 0:
        print("  Tutte le cartelle sono vuote. Niente da fare!")
        return

    print("  File trovati:")
    for folder, files in zip(folders, all_files):
        print(f"    - {folder.name}: {len(files)}")
    print(f"  Analizzo {total} file...\n")

    moved_count = 0
    stayed_count = 0
    failed_count = 0

    for origin_idx, files in enumerate(all_files):
        origin_folder = folders[origin_idx]
        origin_name = origin_folder.name

        for entry in files:
            file_path = entry["path"]
            size_str = format_size(entry["size"])
            specs = _build_folder_specs(folders, all_files, origin_idx, file_path)

            try:
                dest_idx = classify_for_multi_swap(
                    file_path.name, size_str, specs, target_path=_path_key(file_path)
                )
            except Exception as exc:
                failed_count += 1
                log.exception("CLI MultiSwap: classificazione fallita per %s", file_path)
                print(f"  [ERRORE] {file_path.name}: classificazione fallita ({exc})")
                continue

            if not (0 <= dest_idx < len(folders)):
                failed_count += 1
                log.error("CLI MultiSwap: dest_idx fuori range per %s: %s", file_path, dest_idx)
                print(f"  [ERRORE] {file_path.name}: destinazione non valida ({dest_idx})")
                continue

            dest_folder = folders[dest_idx]
            if dest_idx == origin_idx:
                print(f"  [OK] {file_path.name}: {origin_name} -> resta in {origin_name}")
                stayed_count += 1
                continue

            print(f"  [MOVE] {file_path.name}: {origin_name} -> {dest_folder.name}")
            if dry_run:
                print(f"     [DRY RUN] Verrebbe {action} in: {dest_folder}/")
            else:
                try:
                    final_path = transfer_fn(file_path, dest_folder)
                    print(f"     Eseguito: {final_path}")
                except Exception as exc:
                    failed_count += 1
                    log.exception("CLI MultiSwap: errore esecuzione su %s", file_path)
                    print(f"     [ERRORE] {exc}")
                    continue
            moved_count += 1

    log.info(
        "CLI MultiSwap completato: %d analizzati, %d spostati, %d restano, %d errori",
        total, moved_count, stayed_count, failed_count,
    )
    print(f"\n{'=' * 60}")
    print(f"  Riepilogo: {total} file analizzati.")
    print(f"    Da spostare: {moved_count}")
    print(f"    Gia' al posto giusto: {stayed_count}")
    print(f"    Errori: {failed_count}")
    if dry_run:
        print("  Nessun file e' stato modificato (modalita dry run).")
        print("  Rilancia con --execute per eseguire.")
    print(f"{'=' * 60}\n")


def _folder_rename_targets(root_folder: Path, include_root: bool = False) -> list[Path]:
    """Ritorna root opzionale + sottocartelle immediate ordinate."""
    targets: list[Path] = []
    if include_root:
        targets.append(root_folder)
    targets.extend(
        item for item in sorted(root_folder.iterdir())
        if item.is_dir() and not item.name.startswith(".")
    )
    return targets


def rename_folders(root_folder: Path, dry_run: bool = True, include_root: bool = False) -> None:
    """Propone e applica rename prudenti per cartelle esistenti."""
    if not is_folder_rename_allowed():
        print("  Rinomina cartelle disabilitata nelle Impostazioni.")
        print("  Abilita allow_folder_rename dalla GUI prima di eseguire questa modalita.")
        return

    log.info(
        "CLI RenameFolders avviato: root=%s dry_run=%s include_root=%s",
        root_folder, dry_run, include_root,
    )

    targets = _folder_rename_targets(root_folder, include_root=include_root)
    if not targets:
        print("  Nessuna cartella da analizzare.")
        return

    print(f"\n{'=' * 60}")
    print("  Agent Ordinatore - Rinomina cartelle")
    print(f"  Radice: {root_folder.resolve()}")
    print(f"  Modalita: {'DRY RUN (simulazione)' if dry_run else 'ESECUZIONE REALE'}")
    print(f"  Cartelle candidate: {len(targets)}")
    print(f"{'=' * 60}\n")

    results: list[dict] = []
    for folder in targets:
        profile = build_folder_profile(folder)
        suggestion = suggest_folder_rename(profile)
        item = {
            "path": str(folder),
            "current_name": folder.name,
            **suggestion,
        }
        results.append(item)

        action = suggestion["action"].upper()
        confidence = suggestion["confidence"]
        suggested = suggestion["suggested_name"]
        print(f"  [{action}] {folder.name} -> {suggested} ({confidence:.2f})")
        print(f"        {suggestion['reason']}")

    selected = [r for r in results if r["action"] == "rename"]
    if not selected:
        print("\n  Nessuna rinomina proposta.")
        return

    if dry_run:
        print("\n  Nessuna cartella e' stata modificata (modalita dry run).")
        print("  Rilancia con --execute per eseguire.")
        return

    renamed_count = 0
    failed_count = 0
    # Se include_root e sottocartelle sono insieme, rinomina prima i path piu' profondi.
    selected.sort(key=lambda item: len(Path(item["path"]).parts), reverse=True)
    for item in selected:
        source = Path(item["path"])
        try:
            final_path = rename_folder_safe(source, item["suggested_name"])
            renamed_count += 1
            print(f"  [OK] {source} -> {final_path}")
        except Exception as exc:
            failed_count += 1
            log.exception("CLI RenameFolders: errore rename %s", source)
            print(f"  [ERRORE] {source}: {exc}")

    log.info(
        "CLI RenameFolders completato: %d rinominate, %d errori",
        renamed_count, failed_count,
    )
    print(f"\n  Riepilogo: {renamed_count} cartelle rinominate, {failed_count} errori.\n")


def setup_command(args) -> None:
    """Gestisce il subcommand 'setup'."""

    # ── Download modello ──
    if args.download:
        tier = args.download
        if tier not in MODELS:
            print(f"  Tier '{tier}' non valido. Usa: {', '.join(MODELS.keys())}")
            return

        if is_model_downloaded(tier):
            print(f"  Il modello '{tier}' ({MODELS[tier]['name']}) è già scaricato.")
            return

        info = MODELS[tier]
        size_gb = info["size_bytes"] / (1024 ** 3)
        print(f"\n  Download modello: {info['name']} ({size_gb:.1f} GB)")
        print(f"  Repository: {info['repo']}")
        print(f"  File: {info['filename']}")
        print(f"  Download in corso...\n")

        try:
            path = download_model(tier)
            print(f"\n  Modello scaricato in: {path}")
        except Exception as e:
            print(f"\n  Errore durante il download: {e}")
        return

    # ── Elimina modello ──
    if args.delete:
        tier = args.delete
        if tier not in MODELS:
            print(f"  Tier '{tier}' non valido. Usa: {', '.join(MODELS.keys())}")
            return

        if delete_model(tier):
            print(f"  Modello '{tier}' ({MODELS[tier]['name']}) eliminato.")
        else:
            print(f"  Modello '{tier}' non presente sul disco.")
        return

    # ── Lista modelli scaricati ──
    if args.list:
        downloaded = get_downloaded_models()
        if not downloaded:
            print("  Nessun modello scaricato.")
        else:
            print("  Modelli scaricati:")
            for tier in downloaded:
                info = MODELS[tier]
                print(f"    - {tier}: {info['name']} ({info['filename']})")
        return

    # ── Default: mostra hardware e modelli ──
    from hardware import detect_hardware, get_available_tiers

    print(f"\n{'=' * 60}")
    print(f"  Agent Ordinatore — Setup")
    print(f"{'=' * 60}\n")

    hw = detect_hardware()
    print(f"  Hardware rilevato:")
    print(f"    CPU:  {hw['cpu_name']}")
    print(f"    RAM:  {hw['ram_total_gb']} GB totali, {hw['ram_available_gb']} GB disponibili")
    print(f"    OS:   {hw['os']}")
    if hw["gpu_name"]:
        print(f"    GPU:  {hw['gpu_name']}")
        print(f"    VRAM: {hw['vram_total_gb']} GB totali, {hw['vram_available_gb']} GB disponibili")
    else:
        print(f"    GPU:  Non rilevata (inferenza solo CPU)")

    print(f"\n  Modelli disponibili:")
    tiers = get_available_tiers(hw)
    for t in tiers:
        status = ""
        if is_model_downloaded(t["tier"]):
            status = " [SCARICATO]"
        elif not t["available"]:
            status = " [BLOCCATO — RAM insufficiente]"

        rec = " ⭐ CONSIGLIATO" if t["recommended"] else ""
        print(f"    {'●' if t['recommended'] else '○'} {t['tier']:10s} — {t['model']} ({t['size_gb']} GB){rec}{status}")

    print(f"\n  Per scaricare un modello: python main.py setup --download <tier>")
    print(f"{'=' * 60}\n")


def main() -> None:
    """Entry point: parsing degli argomenti e avvio."""

    parser = argparse.ArgumentParser(
        description="Agente AI per l'organizzazione automatica dei file."
    )
    subparsers = parser.add_subparsers(dest="command", help="Comando da eseguire.")

    # Subcommand: organize
    organize_parser = subparsers.add_parser(
        "organize", help="Organizza i file di una cartella in sottocartelle."
    )
    organize_parser.add_argument(
        "folder", type=str, help="Percorso della cartella da organizzare."
    )
    organize_parser.add_argument(
        "--execute", action="store_true", default=False,
        help="Esegui le operazioni per davvero (default: dry run)."
    )
    organize_parser.add_argument(
        "--copy", action="store_true", default=False,
        help="Copia i file invece di spostarli."
    )
    organize_parser.add_argument(
        "--tier", type=str, default=None,
        choices=["lite", "standard", "pro", "ultra"],
        help="Tier del modello da usare (default: da configurazione)."
    )

    # Subcommand: swap
    swap_parser = subparsers.add_parser(
        "swap", help="Scambia i file fuori posto tra due cartelle."
    )
    swap_parser.add_argument(
        "folder_a", type=str, help="Percorso della prima cartella."
    )
    swap_parser.add_argument(
        "folder_b", type=str, help="Percorso della seconda cartella."
    )
    swap_parser.add_argument(
        "--execute", action="store_true", default=False,
        help="Esegui le operazioni per davvero (default: dry run)."
    )
    swap_parser.add_argument(
        "--copy", action="store_true", default=False,
        help="Copia i file invece di spostarli."
    )
    swap_parser.add_argument(
        "--tier", type=str, default=None,
        choices=["lite", "standard", "pro", "ultra"],
        help="Tier del modello da usare (default: da configurazione)."
    )

    # Subcommand: multiswap
    multiswap_parser = subparsers.add_parser(
        "multiswap", help="Scambia i file fuori posto tra due o piu' cartelle."
    )
    multiswap_parser.add_argument(
        "folders", nargs="+", type=str,
        help="Percorsi delle cartelle da confrontare (minimo 2)."
    )
    multiswap_parser.add_argument(
        "--execute", action="store_true", default=False,
        help="Esegui le operazioni per davvero (default: dry run)."
    )
    multiswap_parser.add_argument(
        "--copy", action="store_true", default=False,
        help="Copia i file invece di spostarli."
    )
    multiswap_parser.add_argument(
        "--tier", type=str, default=None,
        choices=["lite", "standard", "pro", "ultra"],
        help="Tier del modello da usare (default: da configurazione)."
    )

    # Subcommand: rename-folders
    rename_parser = subparsers.add_parser(
        "rename-folders", help="Propone nomi coerenti per cartelle esistenti."
    )
    rename_parser.add_argument(
        "folder", type=str,
        help="Cartella madre da cui analizzare le sottocartelle immediate."
    )
    rename_parser.add_argument(
        "--include-root", action="store_true", default=False,
        help="Analizza anche la cartella indicata, oltre alle sottocartelle."
    )
    rename_parser.add_argument(
        "--execute", action="store_true", default=False,
        help="Esegui le rinomine proposte (default: dry run)."
    )
    rename_parser.add_argument(
        "--tier", type=str, default=None,
        choices=["lite", "standard", "pro", "ultra"],
        help="Tier del modello da usare (default: da configurazione)."
    )

    # Subcommand: setup
    setup_parser = subparsers.add_parser(
        "setup", help="Configura hardware e modelli AI."
    )
    setup_parser.add_argument(
        "--download", type=str, default=None, metavar="TIER",
        help="Scarica il modello del tier specificato."
    )
    setup_parser.add_argument(
        "--list", action="store_true", default=False,
        help="Lista i modelli già scaricati."
    )
    setup_parser.add_argument(
        "--delete", type=str, default=None, metavar="TIER",
        help="Elimina il modello del tier specificato."
    )

    args = parser.parse_args()

    if args.command == "organize":
        target = Path(args.folder)
        if not target.is_dir():
            log.error("CLI Organize: cartella non valida: %s", target)
            print(f"  Errore: '{target}' non è una cartella valida.")
            return
        tier = args.tier or get_selected_tier()
        if not _ensure_model(tier):
            return
        init_classifier(tier)
        organize(target_folder=target, dry_run=not args.execute, use_copy=args.copy)

    elif args.command == "swap":
        folder_a = Path(args.folder_a)
        folder_b = Path(args.folder_b)
        if not folder_a.is_dir():
            log.error("CLI Swap: cartella A non valida: %s", folder_a)
            print(f"  Errore: '{folder_a}' non è una cartella valida.")
            return
        if not folder_b.is_dir():
            log.error("CLI Swap: cartella B non valida: %s", folder_b)
            print(f"  Errore: '{folder_b}' non è una cartella valida.")
            return
        if folder_a.resolve() == folder_b.resolve():
            log.error("CLI Swap: cartelle identiche: %s", folder_a)
            print("  Errore: le due cartelle devono essere diverse.")
            return
        tier = args.tier or get_selected_tier()
        if not _ensure_model(tier):
            return
        init_classifier(tier)
        swap(folder_a, folder_b, dry_run=not args.execute, use_copy=args.copy)

    elif args.command == "multiswap":
        folders = [Path(p) for p in args.folders]
        if len(folders) < 2:
            print("  Errore: servono almeno due cartelle.")
            return

        resolved_seen: set[str] = set()
        for folder in folders:
            if not folder.is_dir():
                log.error("CLI MultiSwap: cartella non valida: %s", folder)
                print(f"  Errore: '{folder}' non e' una cartella valida.")
                return
            key = _path_key(folder)
            if key in resolved_seen:
                log.error("CLI MultiSwap: cartella duplicata: %s", folder)
                print("  Errore: le cartelle devono essere distinte.")
                return
            resolved_seen.add(key)

        tier = args.tier or get_selected_tier()
        if not _ensure_model(tier):
            return
        init_classifier(tier)
        multiswap(folders, dry_run=not args.execute, use_copy=args.copy)

    elif args.command == "rename-folders":
        root = Path(args.folder)
        if not root.is_dir():
            log.error("CLI RenameFolders: cartella non valida: %s", root)
            print(f"  Errore: '{root}' non e' una cartella valida.")
            return
        if not is_folder_rename_allowed():
            rename_folders(root, dry_run=not args.execute, include_root=args.include_root)
            return
        tier = args.tier or get_selected_tier()
        if not _ensure_model(tier):
            return
        init_classifier(tier)
        rename_folders(root, dry_run=not args.execute, include_root=args.include_root)

    elif args.command == "setup":
        setup_command(args)

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
