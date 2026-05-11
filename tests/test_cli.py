import io
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

import main


class CliDryRunTests(unittest.TestCase):
    def test_organize_dry_run_does_not_move_or_create_destination(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            source = folder / "fattura.pdf"
            source.write_text("demo", encoding="utf-8")

            with patch("main.classify_file", return_value="Documenti/PDF"):
                with redirect_stdout(io.StringIO()):
                    main.organize(folder, dry_run=True)

            self.assertTrue(source.exists())
            self.assertFalse((folder / "Documenti").exists())

    def test_rename_folders_dry_run_does_not_rename(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "Nuova cartella"
            source.mkdir()
            (source / "fattura.pdf").write_text("demo", encoding="utf-8")

            suggestion = {
                "action": "rename",
                "suggested_name": "Amministrazione",
                "confidence": 0.9,
                "reason": "Contiene fatture.",
            }

            with (
                patch("main.is_folder_rename_allowed", return_value=True),
                patch("main.suggest_folder_rename", return_value=suggestion),
            ):
                with redirect_stdout(io.StringIO()):
                    main.rename_folders(root, dry_run=True)

            self.assertTrue(source.exists())
            self.assertFalse((root / "Amministrazione").exists())

    def test_rename_folders_execute_renames_when_allowed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "Nuova cartella"
            source.mkdir()
            (source / "fattura.pdf").write_text("demo", encoding="utf-8")

            suggestion = {
                "action": "rename",
                "suggested_name": "Amministrazione",
                "confidence": 0.9,
                "reason": "Contiene fatture.",
            }

            with (
                patch("main.is_folder_rename_allowed", return_value=True),
                patch("main.suggest_folder_rename", return_value=suggestion),
            ):
                with redirect_stdout(io.StringIO()):
                    main.rename_folders(root, dry_run=False)

            self.assertFalse(source.exists())
            self.assertTrue((root / "Amministrazione").is_dir())

    def test_swap_uncertain_classification_does_not_move(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            folder_a = root / "A"
            folder_b = root / "B"
            folder_a.mkdir()
            folder_b.mkdir()
            source = folder_a / "incerto.txt"
            source.write_text("demo", encoding="utf-8")

            with patch("main.classify_for_swap", return_value=None):
                with redirect_stdout(io.StringIO()) as out:
                    main.swap(folder_a, folder_b, dry_run=False)

            self.assertTrue(source.exists())
            self.assertFalse((folder_b / "incerto.txt").exists())
            self.assertIn("[INCERTO]", out.getvalue())

    def test_nested_folder_selection_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            parent = root / "Parent"
            child = parent / "Child"
            child.mkdir(parents=True)

            message = main._nested_folder_error([parent, child])

            self.assertIsNotNone(message)
            self.assertIn("annidate", message)


if __name__ == "__main__":
    unittest.main()
