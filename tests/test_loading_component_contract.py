import os
import unittest


class LoadingComponentContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        base = os.path.join(os.getcwd(), "static")
        with open(os.path.join(base, "index.html"), "r", encoding="utf-8") as f:
            cls.html = f.read()
        with open(os.path.join(base, "app.js"), "r", encoding="utf-8") as f:
            cls.js = f.read()
        with open(os.path.join(base, "styles", "overlays.css"), "r", encoding="utf-8") as f:
            cls.css = f.read()

    def test_overlay_aria_contract(self):
        required = [
            'id="loading"', 'role="status"', 'aria-live="polite"',
            'aria-atomic="true"', 'aria-hidden="true"', 'aria-busy="false"',
        ]
        for token in required:
            self.assertIn(token, self.html, f"Missing in index.html: {token}")

    def test_loading_component_api_exists(self):
        required = [
            "class LoadingComponent",
            "setOptions(partial)",
            "setText(text)",
            "show(text, opts = {})",
            "hide(token = null)",
            "async withLoading(promiseFactory, opts = {})",
            "async fetchJson(url, options = {}, loadingOpts = {})",
        ]
        for token in required:
            self.assertIn(token, self.js, f"Missing in app.js: {token}")

    def test_overlay_css_present(self):
        required = [
            ".loading-overlay",
            ".loading-indicator",
            ".loading-text",
            ".snackbar-stack",
            ".snack",
            ".modal-overlay",
        ]
        for token in required:
            self.assertIn(token, self.css, f"Missing in overlays.css: {token}")

    def test_global_loading_helpers_exist(self):
        required = [
            "function showLoading",
            "function hideLoading",
            "async function requestJson",
        ]
        for token in required:
            self.assertIn(token, self.js, f"Missing in app.js: {token}")


if __name__ == "__main__":
    unittest.main()
