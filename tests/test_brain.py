import unittest

from brain import LocalClassifier


class FolderRenameParserTests(unittest.TestCase):
    def test_swap_parser_returns_none_when_uncertain(self):
        self.assertEqual(LocalClassifier._parse_swap("A"), "A")
        self.assertEqual(LocalClassifier._parse_swap("scegli B"), "B")
        self.assertIsNone(LocalClassifier._parse_swap("non so"))

    def test_index_parser_returns_none_when_uncertain_or_out_of_range(self):
        self.assertEqual(LocalClassifier._parse_index("1", 3), 1)
        self.assertEqual(LocalClassifier._parse_index("scelgo 2", 3), 2)
        self.assertIsNone(LocalClassifier._parse_index("9", 3))
        self.assertIsNone(LocalClassifier._parse_index("non so", 3))

    def test_parse_valid_json_and_sanitize_name(self):
        result = LocalClassifier._parse_folder_rename(
            '{"action":"rename","suggested_name":"CON/Bad","confidence":0.86,"reason":"ok"}',
            "Vecchio",
        )

        self.assertEqual(result["action"], "rename")
        self.assertEqual(result["suggested_name"], "CON_")
        self.assertEqual(result["confidence"], 0.86)
        self.assertEqual(result["reason"], "ok")

    def test_invalid_json_falls_back_to_keep(self):
        result = LocalClassifier._parse_folder_rename("not json", "Archivio")

        self.assertEqual(result["action"], "keep")
        self.assertEqual(result["suggested_name"], "Archivio")
        self.assertEqual(result["confidence"], 0.0)

    def test_invalid_action_and_confidence_are_clamped(self):
        result = LocalClassifier._parse_folder_rename(
            '{"action":"delete","suggested_name":"Foto","confidence":9,"reason":"x"}',
            "Archivio",
        )

        self.assertEqual(result["action"], "keep")
        self.assertEqual(result["suggested_name"], "Foto")
        self.assertEqual(result["confidence"], 1.0)


if __name__ == "__main__":
    unittest.main()
