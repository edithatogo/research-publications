"""Fictional runner manifests; no runtime downloads or promotion."""
import unittest

from scripts.runtime_candidate import finalize, select_python_preview, version_key


def release(version, platform="26.04", arch="x64"):
    return {"version": version, "files": [{"platform": "linux", "platform_version": platform, "arch": arch}]}


class RuntimeCandidateTests(unittest.TestCase):
    def test_newest_runnable_same_series_only(self):
        result = select_python_preview([
            release("3.15.1"), release("3.15.2rc1"), release("3.15.2"),
            release("3.15.3", "24.04"), release("3.15.4", arch="x64-freethreaded"),
            release("3.16.0"), release("3.14.9"),
        ], baseline="3.15.1", platform_version="26.04")
        self.assertEqual(result["candidate"], "3.15.2")
        self.assertFalse(result["promoted"])

    def test_absent_build_is_explicitly_unavailable(self):
        result = select_python_preview([release("3.15.2", "24.04")], baseline="3.15.1", platform_version="26.04")
        self.assertIsNone(result["candidate"])
        self.assertEqual(result["state"], "candidate-unavailable")

    def test_prerelease_order_and_invalid_version(self):
        self.assertLess(version_key("3.15.2rc2"), version_key("3.15.2"))
        for version in ("3.14.9", "3.15.02", "3.15.2\n", "3.15.2+arbitrary"):
            with self.subTest(version=version), self.assertRaises(ValueError):
                version_key(version)

    def test_failure_without_receipt_is_retained(self):
        result = finalize({}, discovery_outcome="failure", outcome="skipped")
        self.assertEqual(result["state"], "discovery-failed")
        self.assertFalse(result["runtimeTestsExecuted"])

    def test_setup_or_skipped_tests_never_qualify(self):
        for outcome in ("skipped", "cancelled", ""):
            result = finalize({"candidate": "3.15.2"}, discovery_outcome="success", outcome=outcome)
            self.assertEqual(result["state"], "runtime-tests-not-executed")
        result = finalize({"candidate": "3.15.2"}, discovery_outcome="success", outcome="failure")
        self.assertEqual(result["state"], "runtime-tests-failed")
        result = finalize({"candidate": "3.15.2"}, discovery_outcome="success", outcome="success")
        self.assertEqual(result["state"], "qualified-runtime-candidate")
        self.assertFalse(result["promoted"])

    def test_malformed_file_list_fails_closed(self):
        with self.assertRaises(ValueError):
            select_python_preview([{"version": "3.15.2", "files": None}], baseline="3.15.1", platform_version="26.04")
