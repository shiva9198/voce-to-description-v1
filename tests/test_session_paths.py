import tempfile
import unittest
from pathlib import Path

from session_paths import resolve_session_path


class ResolveSessionPathTests(unittest.TestCase):
    def test_accepts_simple_json_filename(self):
        with tempfile.TemporaryDirectory() as folder:
            resolved = resolve_session_path(folder, "session_20260823_120000.json")

            self.assertEqual(
                resolved,
                Path(folder).resolve() / "session_20260823_120000.json",
            )

    def test_rejects_parent_traversal(self):
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaises(ValueError):
                resolve_session_path(folder, "../outside.json")

    def test_rejects_non_json_filename(self):
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaises(ValueError):
                resolve_session_path(folder, "session.txt")


if __name__ == "__main__":
    unittest.main()
