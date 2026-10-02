"""Proves de la publicació additiva d'inferències."""

import subprocess
import tempfile
import unittest
from pathlib import Path

from scripts.publish_inferences import copy_new_inferences


class PublishInferencesTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        self.source = root / "source"
        self.source.mkdir()
        self.repo = root / "repo"
        self.repo.mkdir()
        self.destination = self.repo / "data/inferencies"
        self.destination.mkdir(parents=True)
        self.git("init", "-q")
        self.git("config", "user.name", "Test")
        self.git("config", "user.email", "test@example.com")
        self.write(self.destination, "v1/model/prompt.yaml", "original")
        self.git("add", ".")
        self.git("commit", "-qm", "data: initial inferences")

    def git(self, *args):
        return subprocess.check_output(
            ["git", "-C", str(self.repo), *args], text=True
        ).strip()

    def write(self, directory, name, content):
        path = directory / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)

    def test_adds_new_versions_and_models_and_keeps_identical_files(self):
        self.write(self.source, "v1/model/prompt.yaml", "original")
        self.write(self.source, "v2/model/prompt.yaml", "revision")
        self.write(self.source, "v1/new-model/prompt.yaml", "new model")
        copy_new_inferences(self.source, self.destination, self.repo)
        self.assertEqual(
            (self.destination / "v2/model/prompt.yaml").read_text(), "revision"
        )
        self.assertEqual(
            (self.destination / "v1/new-model/prompt.yaml").read_text(), "new model"
        )
        self.assertEqual(self.git("diff"), "")
        self.assertTrue((self.destination / "v1/model/prompt.yaml").exists())

    def test_rejects_changed_committed_file_before_copying_any_files(self):
        self.write(self.source, "v1/model/prompt.yaml", "changed")
        self.write(self.source, "v2/model/prompt.yaml", "new")
        with self.assertRaisesRegex(ValueError, "versió nova"):
            copy_new_inferences(self.source, self.destination, self.repo)
        self.assertEqual(self.git("status", "--porcelain"), "")
        self.assertFalse((self.destination / "v2/model/prompt.yaml").exists())

    def test_rejects_staged_changes(self):
        self.write(self.destination, "v1/model/prompt.yaml", "changed")
        self.git("add", ".")
        with self.assertRaisesRegex(ValueError, "canvis locals"):
            copy_new_inferences(self.source, self.destination, self.repo)

    def test_rejects_untracked_files(self):
        self.write(self.destination, "v1/model/other.yaml", "untracked")
        with self.assertRaisesRegex(ValueError, "canvis locals"):
            copy_new_inferences(self.source, self.destination, self.repo)

    def publish(self):
        remote = Path(self.temp.name) / "remote.git"
        subprocess.run(["git", "init", "--bare", "-q", str(remote)], check=True)
        self.git("remote", "add", "origin", str(remote))
        self.git("push", "-u", "origin", "HEAD")
        return subprocess.run(
            [
                "make",
                "publish_inferences",
                f"REFERENCE_INFERENCES_WORKTREE={self.repo}",
                f"REFERENCE_INFERENCES_DIR={self.destination}",
                f"PUBLISH_INFERENCES_DIR={self.source}",
            ],
            cwd=Path(__file__).resolve().parents[1],
            capture_output=True,
            text=True,
        )

    def test_make_rejects_overwrite_without_committing_or_pushing(self):
        original_head = self.git("rev-parse", "HEAD")
        self.write(self.source, "v1/model/prompt.yaml", "changed")
        self.write(self.source, "v2/model/prompt.yaml", "new")
        result = self.publish()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("versió nova", result.stderr)
        self.assertEqual(self.git("rev-parse", "HEAD"), original_head)
        self.assertEqual(self.git("rev-parse", "@{upstream}"), original_head)
        self.assertEqual(self.git("status", "--porcelain"), "")

    def test_make_commits_and_pushes_new_inferences(self):
        self.write(self.source, "v2/model/prompt.yaml", "new")
        result = self.publish()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual((self.destination / "v2/model/prompt.yaml").read_text(), "new")
        self.assertEqual(
            self.git("rev-parse", "HEAD"), self.git("rev-parse", "@{upstream}")
        )
        self.assertEqual(self.git("status", "--porcelain"), "")

    def test_make_identical_files_do_not_create_commit(self):
        original_head = self.git("rev-parse", "HEAD")
        self.write(self.source, "v1/model/prompt.yaml", "original")
        result = self.publish()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("No hi ha inferències noves", result.stdout)
        self.assertEqual(self.git("rev-parse", "HEAD"), original_head)


if __name__ == "__main__":
    unittest.main()
