import unittest

from brain import DeepSeekAPIError, DeepSeekClassifier, LocalClassifier


class StubDeepSeekClassifier(DeepSeekClassifier):
    def __init__(self, reply: str):
        super().__init__(model="deepseek-v4-flash", api_key="test-key")
        self.reply = reply
        self.calls = []

    def _post_chat(self, messages, max_tokens, temperature=0.1, stop=None):
        self.calls.append({
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "stop": stop,
        })
        return {"choices": [{"message": {"content": self.reply}}]}


class FallbackDeepSeekClassifier(DeepSeekClassifier):
    def __init__(self, model: str, flash_response, pro_response):
        super().__init__(model=model, api_key="test-key")
        self.flash_response = flash_response
        self.pro_response = pro_response
        self.models_called = []

    def _post_chat_once(self, model, messages, max_tokens, temperature=0.1, stop=None):
        self.models_called.append(model)
        response = self.flash_response if model == "deepseek-v4-flash" else self.pro_response
        if isinstance(response, Exception):
            raise response
        return response


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


class DeepSeekClassifierTests(unittest.TestCase):
    def test_deepseek_classify_file_reuses_category_parser(self):
        classifier = StubDeepSeekClassifier('{"category":"Documenti/PDF"}')

        category = classifier.classify_file("fattura.pdf", 1200)

        self.assertEqual(category, "Documenti/PDF")
        self.assertEqual(classifier.calls[0]["max_tokens"], 100)

    def test_deepseek_swap_reuses_swap_parser(self):
        classifier = StubDeepSeekClassifier("B")

        result = classifier.classify_for_swap(
            "foto.jpg", "1 MB", "A", "B", ["doc.pdf"], ["mare.jpg"]
        )

        self.assertEqual(result, "B")

    def test_deepseek_error_message_parser(self):
        raw = '{"error":{"message":"invalid api key","type":"auth"}}'

        self.assertEqual(
            DeepSeekClassifier._extract_error_message(raw),
            "invalid api key",
        )

    def test_flash_falls_back_to_pro_on_recoverable_error(self):
        classifier = FallbackDeepSeekClassifier(
            model="deepseek-v4-flash",
            flash_response=DeepSeekAPIError("timeout", recoverable=True),
            pro_response={"choices": [{"message": {"content": '{"category":"Documenti/PDF"}'}}]},
        )

        category = classifier.classify_file("fattura.pdf", "10 KB")

        self.assertEqual(category, "Documenti/PDF")
        self.assertEqual(classifier.models_called, ["deepseek-v4-flash", "deepseek-v4-pro"])

    def test_flash_falls_back_to_pro_on_empty_response(self):
        classifier = FallbackDeepSeekClassifier(
            model="deepseek-v4-flash",
            flash_response={"choices": [{"message": {"content": ""}}]},
            pro_response={"choices": [{"message": {"content": "B"}}]},
        )

        result = classifier.classify_for_swap("foto.jpg", "1 MB", "A", "B", [], [])

        self.assertEqual(result, "B")
        self.assertEqual(classifier.models_called, ["deepseek-v4-flash", "deepseek-v4-pro"])

    def test_pro_does_not_fallback(self):
        classifier = FallbackDeepSeekClassifier(
            model="deepseek-v4-pro",
            flash_response={"choices": [{"message": {"content": "A"}}]},
            pro_response=DeepSeekAPIError("timeout", recoverable=True),
        )

        with self.assertRaises(DeepSeekAPIError):
            classifier.classify_for_swap("foto.jpg", "1 MB", "A", "B", [], [])

        self.assertEqual(classifier.models_called, ["deepseek-v4-pro"])


if __name__ == "__main__":
    unittest.main()
