import tempfile
import unittest
from pathlib import Path

try:
    from scripts.check_workflow_references import check
except ModuleNotFoundError as error:
    if error.name != "yaml":
        raise
    raise unittest.SkipTest("PyYAML is installed by the locked source-security job") from error


class WorkflowReferencesTests(unittest.TestCase):
    def inspect(self, body):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            workflows = root / ".github/workflows"
            workflows.mkdir(parents=True)
            (workflows / "example.yml").write_text(body)
            return check(root)

    def test_immutable_repository_container_and_local_references_pass(self):
        for reference in ["actions/checkout@" + "a" * 40,
                          "owner/repo/.github/workflows/job.yml@" + "b" * 40,
                          "docker://image@sha256:" + "c" * 64,
                          "./.github/actions/local", "$/.github/workflows/local.yml"]:
            with self.subTest(reference=reference):
                self.assertEqual(self.inspect(f"jobs:\n  gate:\n    uses: {reference}\n"), [])

    def test_floating_invalid_and_tagged_container_references_fail(self):
        for reference in ["actions/checkout@v7", "owner/repo@main", "null", "123",
                          "docker://image:latest", "owner/repo@" + "a" * 39]:
            with self.subTest(reference=reference):
                self.assertTrue(self.inspect(f"jobs:\n  gate:\n    steps:\n      - uses: {reference}\n"))

    def test_all_nested_steps_are_checked(self):
        body = "jobs:\n  first:\n    steps:\n      - uses: action/repo@main\n  second:\n    uses: other/repo@v1\n"
        self.assertEqual(len(self.inspect(body)), 2)
