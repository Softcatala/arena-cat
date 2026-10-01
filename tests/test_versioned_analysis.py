import io
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

import yaml

from scripts import analitza_inferencies as analyzer


class TestVersionedAnalysis(unittest.TestCase):
    def test_latest_revision_never_borrows_old_answers(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            for version, codes in {
                "v1": ["correccio_1", "traduccio_1"],
                "v2": ["correccio_1"],
            }.items():
                prompts = root / "data/prompts" / version
                prompts.mkdir(parents=True)
                for code in codes:
                    (prompts / f"{code}.txt").write_text(f"{code} {version}")
                    for model in analyzer.MODEL_IDS[:2]:
                        if version == "v2" and model == analyzer.MODEL_IDS[1]:
                            continue
                        target = root / "data/inferencies" / version / model
                        target.mkdir(parents=True, exist_ok=True)
                        (target / f"{code}.yaml").write_text(
                            yaml.safe_dump(
                                {
                                    "prompt": {
                                        "path": f"data/prompts/{version}/{code}.txt"
                                    },
                                    "output": {"answer": f"Resposta {version}"},
                                }
                            )
                        )

            with patch.object(analyzer, "REPO_ROOT", root):
                output = io.StringIO()
                with redirect_stdout(output):
                    analyzer.main([])
                report = (root / "results.txt").read_text()
                self.assertIn("correccio_1/v2", output.getvalue())
                self.assertNotIn("PROMPT correccio_1", report)
                self.assertIn("PROMPT traduccio_1", report)
                self.assertIn("Versió: v1", report)

                with redirect_stdout(io.StringIO()):
                    analyzer.main(["--inferencies", "data/inferencies/v1"])
                report = (root / "results.txt").read_text()
                self.assertIn("PROMPT correccio_1", report)
