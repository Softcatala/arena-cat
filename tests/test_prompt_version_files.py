import tempfile
import unittest
from pathlib import Path

from scripts.lib.prompt_versions import (
    inference_directory,
    latest_prompt_files,
    version_directories,
)


class TestPromptVersionFiles(unittest.TestCase):
    def test_latest_files_keep_unchanged_prompts_and_use_numeric_versions(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            for version, codes in {
                "v1": ["correccio_1", "traduccio_1"],
                "v9": ["correccio_1"],
                "v10": ["correccio_1"],
                "v01": ["correccio_1"],
            }.items():
                (root / version).mkdir()
                for code in codes:
                    (root / version / f"{code}.txt").write_text(version)

            self.assertEqual(
                latest_prompt_files(root),
                [root / "v10/correccio_1.txt", root / "v1/traduccio_1.txt"],
            )
            self.assertEqual(
                [p.name for p in version_directories(root)], ["v10", "v9", "v1"]
            )
            self.assertEqual(
                latest_prompt_files(root / "v9"), [root / "v9/correccio_1.txt"]
            )
            self.assertEqual(latest_prompt_files(root / "missing"), [])

    def test_directory_with_txt_extension_is_not_a_prompt(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "v2/correccio_1.txt").mkdir(parents=True)
            (root / "v1").mkdir()
            original = root / "v1/correccio_1.txt"
            original.write_text("Prompt")
            self.assertEqual(latest_prompt_files(root), [original])
            self.assertEqual(latest_prompt_files(root / "v2"), [])

    def test_inference_directory_preserves_version_and_rejects_mismatch(self):
        root = Path("data/inferencies")
        self.assertEqual(inference_directory(root, "v2"), root / "v2")
        self.assertEqual(inference_directory(root / "v2", "v2"), root / "v2")
        with self.assertRaises(ValueError):
            inference_directory(root / "v1", "v2")
