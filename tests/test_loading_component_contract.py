import os
import re
import unittest


class LoadingComponentContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.index_path = os.path.join(os.getcwd(), "static", "index.html")
        with open(cls.index_path, "r", encoding="utf-8") as f:
            cls.html = f.read()

    def test_has_aria_attributes_and_status_role(self):
        required = [
            'id="loading"',
            'role="status"',
            'aria-live="polite"',
            'aria-atomic="true"',
            'aria-hidden="true"',
            'aria-busy="false"',
        ]
        for token in required:
            self.assertIn(token, self.html)

    def test_loading_component_api_exists(self):
        required = [
            "class LoadingComponent",
            "setOptions(partial)",
            "setText(text)",
            "show(text, opts = {})",
            "hide(token = null)",
            "async withLoading(promiseFactory, opts = {})",
            "async fetchJson(url, options = {}, loadingOpts = {})",
            "function showLoading(text, options = {})",
            "function hideLoading(token = null)",
            "async function requestJson(url, options = {}, loadingOptions = {})",
        ]
        for token in required:
            self.assertIn(token, self.html)

    def test_transition_timings_are_in_required_ranges(self):
        self.assertIn("fadeInMs: 400", self.html)
        self.assertIn("fadeOutMs: 250", self.html)
        self.assertIn("Math.max(300, Math.min(500", self.html)
        self.assertIn("Math.max(200, Math.min(300", self.html)

    def test_has_theme_and_responsive_loading_styles(self):
        required_styles = [
            ".loading-overlay.loading-color-primary",
            ".loading-overlay.loading-color-secondary",
            ".loading-overlay.loading-color-custom",
            ".loading-overlay.loading-size-small",
            ".loading-overlay.loading-size-medium",
            ".loading-overlay.loading-size-large",
            ".loading-overlay.loading-mode-circular",
            ".loading-overlay.loading-mode-linear",
            "@media (max-width: 768px)",
        ]
        for token in required_styles:
            self.assertIn(token, self.html)

    def test_loading_is_integrated_with_async_capture_and_upload(self):
        self.assertRegex(self.html, r"captureFrame\(\)[\s\S]*showLoading\('Capturando rosto e indexando embeddings\.\.\.'")
        self.assertRegex(self.html, r"uploadPhotos\(files\)[\s\S]*showLoading\('Enviando foto e indexando embeddings\.\.\.'")
        self.assertRegex(self.html, r"requestJson\('/api/session/select'")
        self.assertRegex(self.html, r"requestJson\('/api/compose'")
        self.assertRegex(self.html, r"requestJson\('/api/print'")


if __name__ == "__main__":
    unittest.main()
