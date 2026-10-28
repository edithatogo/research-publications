"""Run the two library operators' offline transport suite in the normal harness."""

import shutil
import subprocess
import unittest
from pathlib import Path


class LibraryMetadataTransportTests(unittest.TestCase):
    def test_offline_transport_contracts(self):
        node = shutil.which("node")
        self.assertIsNotNone(
            node, "Node is required for the library operator source gate"
        )
        result = subprocess.run(
            [node, "--test", "tests/test_library_metadata_appliers.mjs"],
            cwd=Path(__file__).resolve().parents[1],
            capture_output=True,
            text=True,
            check=False,
            timeout=45,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
