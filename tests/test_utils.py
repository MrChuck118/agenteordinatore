import tempfile
import unittest
from pathlib import Path

from utils import (
    build_folder_profile,
    detect_project_markers,
    rename_folder_safe,
    sanitize_category,
    sanitize_folder_name,
)


class SanitizeCategoryTests(unittest.TestCase):
    def test_blocks_absolute_and_home_paths(self):
        self.assertEqual(sanitize_category("C:/Windows/System32"), "Altro")
        self.assertEqual(sanitize_category("~/Documents"), "Altro")
        self.assertEqual(sanitize_category("/etc/passwd"), "Altro")

    def test_removes_traversal_and_limits_depth(self):
        self.assertEqual(sanitize_category("../segreti"), "segreti")
        self.assertEqual(sanitize_category("A/B/C/D"), "A/B")

    def test_sanitizes_reserved_windows_names(self):
        self.assertEqual(sanitize_category("CON"), "CON_")
        self.assertEqual(sanitize_folder_name("LPT1"), "LPT1_")

    def test_folder_name_is_single_segment(self):
        self.assertEqual(sanitize_folder_name("Documenti/PDF"), "Documenti")


class ProjectMarkerTests(unittest.TestCase):
    def test_detects_named_project_markers(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            (folder / "package.json").write_text("{}", encoding="utf-8")

            self.assertIn("package.json", detect_project_markers(folder))
            self.assertTrue(build_folder_profile(folder)["protected"])

    def test_detects_solution_and_csproj_extensions(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            (folder / "Demo.sln").write_text("", encoding="utf-8")
            (folder / "Demo.csproj").write_text("", encoding="utf-8")

            markers = detect_project_markers(folder)
            self.assertIn(".sln", markers)
            self.assertIn(".csproj", markers)
            self.assertTrue(build_folder_profile(folder)["protected"])


class RenameFolderSafeTests(unittest.TestCase):
    def test_renames_folder_with_sanitized_name(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "Nuova cartella"
            source.mkdir()

            final = rename_folder_safe(source, "Documenti/Archivio")

            self.assertEqual(final, root / "Documenti")
            self.assertTrue(final.is_dir())
            self.assertFalse(source.exists())

    def test_resolves_name_conflicts_without_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "old"
            existing = root / "Documenti"
            source.mkdir()
            existing.mkdir()

            final = rename_folder_safe(source, "Documenti")

            self.assertEqual(final, root / "Documenti_2")
            self.assertTrue(existing.is_dir())
            self.assertTrue(final.is_dir())
            self.assertFalse(source.exists())


if __name__ == "__main__":
    unittest.main()
