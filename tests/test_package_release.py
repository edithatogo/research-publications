import hashlib
import io
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

from scripts import package_release
from scripts.package_release import (
    build_manifest,
    package,
    source_paths,
    validate_extraction,
    validate_version,
    verify_manifest,
    write_release_receipt,
    write_stable_entry,
)


class PackageReleaseTests(unittest.TestCase):
    def test_source_manifest_preserves_complete_project_licence_and_notice_bytes(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for name in ('LICENSE', 'NOTICE'):
                (root/name).write_bytes((package_release.ROOT/name).read_bytes())
            with patch('scripts.package_release.run', return_value='LICENSE\0NOTICE\0'):
                paths = source_paths(root)
            self.assertEqual({p.name for p in paths}, {'LICENSE', 'NOTICE'})
            with patch('scripts.package_release.run', side_effect=RuntimeError('no git in extracted source')):
                manifest = build_manifest(paths, '1.2.3', 'publication-platform-v1', 'fixture', root)
            verify_manifest(root, manifest)
            for row in manifest['Files']:
                original = (package_release.ROOT/row['path']).read_bytes()
                self.assertEqual(row['sha256'], hashlib.sha256(original).hexdigest())
                self.assertEqual(row['bytes'], len(original))

    def _manifest(self, files):
        return {"SoftwareVersion": "1.2.3", "SchemaVersion": "publication-platform-v1",
                "AcceptedBatchID": "batch-fixture", "SourceCommit": "source-archive",
                "DirtyBuild": False, "NativeAcceptance": False, "Files": files}

    def test_version_requires_semver_with_optional_preview(self):
        self.assertEqual(validate_version("0.3.0-rc1"), "0.3.0-rc1")
        self.assertEqual(validate_version("1.2.3-rc.1+build.7"), "1.2.3-rc.1+build.7")
        for value in ("v0.3", "01.2.3", "1.02.3", "1.2.03", "1.2.3-01",
                      "1.2.3-alpha..1", "1.2.3+build..1", "1.2.3-", None):
            with self.subTest(value=value), self.assertRaises(ValueError):
                validate_version(value)

    def test_source_paths_exclude_runtime_archives(self):
        names = {path.as_posix() for path in source_paths()}
        self.assertFalse(any("downloads/canonical_live_artifacts/" in name for name in names))
        self.assertFalse(any(name.endswith((".zip", ".bundle")) for name in names))

    def test_source_paths_exclude_native_recovery_and_deployment_packages(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            names = ["candidate.pbix", "template.pbit", "solution.msapp", "flow.msflow", "UPPER.PBIX"]
            for name in names:
                (root / name).write_bytes(b"native package")
            with patch("scripts.package_release.run", return_value="\0".join(names)):
                selected = source_paths(root)
            self.assertEqual(selected, [])

    def test_source_paths_exclude_environment_credential_files_and_private_data(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            names = ["README.md", ".env", ".env.production", "config/local.env",
                     "private/fixture.json", "Private/fixture.json",
                     ".private/binding.json", ".flowagent/backup.json",
                     "DOWNLOADS/canonical_live_artifacts/report.json"]
            for name in names:
                path = root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("fixture", encoding="utf-8")
            with patch("scripts.package_release.run", return_value="\0".join(names)):
                selected = source_paths(root)
            self.assertEqual([path.relative_to(root).as_posix() for path in selected], ["README.md"])

    def test_manifest_separates_software_schema_and_batch_identity(self):
        manifest = build_manifest([], "0.3.0-rc1", "publication-platform-v1", "batch-local")
        self.assertEqual(manifest["SoftwareVersion"], "0.3.0-rc1")
        self.assertEqual(manifest["SchemaVersion"], "publication-platform-v1")
        self.assertEqual(manifest["AcceptedBatchID"], "batch-local")
        self.assertIn("DirtyBuild", manifest)
        self.assertFalse(manifest["NativeAcceptance"])

    def test_manifest_rejects_empty_or_padded_schema_and_batch_identities(self):
        for schema, batch in (("", "batch-1"), ("schema-v1", " "),
                              (" schema-v1", "batch-1"), ("schema-v1", "batch-1 ")):
            with self.subTest(schema=schema, batch=batch), self.assertRaisesRegex(ValueError, "nonempty, unpadded"):
                build_manifest([], "1.2.3", schema, batch)

    def test_invalid_release_identity_fails_before_archive_creation(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "source"
            root.mkdir()
            output = Path(temporary) / "output"

            def fake_run(arguments, cwd):
                if arguments == ["git", "status", "--porcelain"]:
                    return ""
                if arguments == ["git", "ls-files", "-z"]:
                    return ""
                if arguments == ["git", "rev-parse", "HEAD"]:
                    return "a" * 40
                raise AssertionError(arguments)

            with patch("scripts.package_release.run", side_effect=fake_run):
                with self.assertRaisesRegex(ValueError, "SchemaVersion"):
                    package(output, version="1.2.3", schema_version=" ",
                            accepted_batch_id="batch-fixture", root=root)
            self.assertEqual(list(output.iterdir()), [])

    def test_zip_member_timestamp_is_stable(self):
        first = io.BytesIO()
        second = io.BytesIO()
        for stream in (first, second):
            with zipfile.ZipFile(stream, "w") as archive:
                write_stable_entry(archive, "example.txt", b"content")
        self.assertEqual(first.getvalue(), second.getvalue())

    def test_clean_source_archive_and_manifest_are_repeatable(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "source"
            root.mkdir()
            source = root / "module.py"
            source.write_text("VALUE = 1\n", encoding="utf-8")

            def fake_run(arguments, cwd):
                if arguments == ["git", "status", "--porcelain"]:
                    return ""
                if arguments == ["git", "ls-files", "-z"]:
                    return "module.py"
                if arguments == ["git", "rev-parse", "HEAD"]:
                    return "a" * 40
                raise AssertionError(arguments)

            with patch("scripts.package_release.run", side_effect=fake_run):
                paths = source_paths(root)
                first_manifest = build_manifest(paths, "1.2.3", "schema-v1", "batch-1", root)
                second_manifest = build_manifest(paths, "1.2.3", "schema-v1", "batch-1", root)
                self.assertEqual(first_manifest, second_manifest)
                outputs = [Path(temporary) / "release-a", Path(temporary) / "release-b"]
                with patch("scripts.package_release.validate_extraction"), patch("scripts.package_release.prepare_extraction_test_environment"):
                    first = package(outputs[0], "1.2.3", "schema-v1", "batch-1", root)
                    second = package(outputs[1], "1.2.3", "schema-v1", "batch-1", root)
            self.assertEqual(first["Archive"]["sha256"], second["Archive"]["sha256"])

    def test_release_builder_refuses_to_replace_archive_or_receipt(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary)
            for filename in (
                "CHHHS-Research-Publications-v1.2.3-Source.zip",
                "CHHHS-Research-Publications-v1.2.3-Source-receipt.json",
            ):
                with self.subTest(filename=filename):
                    existing = output / filename
                    existing.write_bytes(b"preserve published release evidence")
                    with self.assertRaisesRegex(FileExistsError, "refusing to replace"):
                        package(output, version="1.2.3")
                    self.assertEqual(existing.read_bytes(), b"preserve published release evidence")
                    existing.unlink()

    def test_receipt_writer_refuses_a_late_existing_path(self):
        with tempfile.TemporaryDirectory() as temporary:
            receipt_path = Path(temporary) / "receipt.json"
            receipt_path.write_bytes(b"preserve concurrently created receipt")
            with self.assertRaises(FileExistsError):
                write_release_receipt(receipt_path, {"status": "candidate"})
            self.assertEqual(receipt_path.read_bytes(), b"preserve concurrently created receipt")

    def test_fresh_extraction_uses_required_full_harness(self):
        extracted = Path("/tmp/fresh-release-extraction")
        with patch("scripts.package_release.run") as run:
            validate_extraction(extracted)
        run.assert_called_once_with(
            [
                str(extracted / '.venv' / 'bin' / 'python'),
                "scripts/agent_harness.py",
                "check",
                "--task",
                "all",
            ],
            extracted,
        )

    def test_extraction_fixture_requires_real_ignore_policy(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / '.gitignore').write_text('private/\n.venv/\n')
            (root / 'requirements-dev.txt').write_text('')
            original_run = package_release.run
            def fixture_run(arguments, cwd):
                return '' if arguments[0] == 'uv' else original_run(arguments, cwd)
            with patch('scripts.package_release.run', side_effect=fixture_run):
                package_release.prepare_extraction_test_environment(root)
            self.assertTrue((root / '.git').is_dir())
            self.assertTrue((root / '.venv/bin/python').exists())
            self.assertEqual(list((root / 'private/ops').iterdir()), [])
        with tempfile.TemporaryDirectory() as temporary:
            with self.assertRaises(RuntimeError):
                package_release.prepare_extraction_test_environment(Path(temporary))

    def test_omitted_runtime_dependency_fails_extracted_harness_without_receipt(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "source"
            harness = root / "scripts" / "agent_harness.py"
            harness.parent.mkdir(parents=True)
            harness.write_text("import release_required_helper\n", encoding="utf-8")
            (root / '.gitignore').write_text('private/\n.venv/\n')
            (root / 'requirements-dev.txt').write_text('')
            output = Path(temporary) / "release"
            original_run = package_release.run

            def fixture_run(arguments, cwd):
                if arguments == ["git", "status", "--porcelain"]:
                    return ""
                if arguments == ["git", "ls-files", "-z"]:
                    return "scripts/agent_harness.py\0.gitignore\0requirements-dev.txt"
                if arguments == ["git", "rev-parse", "HEAD"]:
                    return "a" * 40
                if arguments[0] == 'uv':
                    return ''
                return original_run(arguments, cwd)

            with patch("scripts.package_release.run", side_effect=fixture_run):
                with self.assertRaisesRegex(RuntimeError, "No module named 'release_required_helper'"):
                    package(output, "1.2.3", "schema-v1", "batch-1", root)

            archive = output / "CHHHS-Research-Publications-v1.2.3-Source.zip"
            receipt = output / "CHHHS-Research-Publications-v1.2.3-Source-receipt.json"
            self.assertTrue(archive.is_file(), "retain the failed candidate for diagnosis")
            self.assertFalse(receipt.exists(), "a failed extracted harness must not qualify a release")

    def test_release_manifest_detects_modified_or_missing_file(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            artifact = root / "src" / "module.py"
            artifact.parent.mkdir()
            artifact.write_bytes(b"version one")
            manifest = self._manifest([{
                "path": "src/module.py",
                "sha256": hashlib.sha256(b"version one").hexdigest(),
                "bytes": len(b"version one"),
            }])
            verify_manifest(root, manifest)
            artifact.write_bytes(b"version two")
            with self.assertRaisesRegex(ValueError, "length differs|hash differs"):
                verify_manifest(root, manifest)
            artifact.unlink()
            with self.assertRaisesRegex(ValueError, "missing"):
                verify_manifest(root, manifest)

    def test_release_manifest_rejects_path_escape_and_duplicate(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            entry = {"path": "../outside", "sha256": "0" * 64, "bytes": 0}
            with self.assertRaisesRegex(ValueError, "escapes"):
                verify_manifest(root, self._manifest([entry]))
            (root / "x").write_bytes(b"")
            entry = {"path": "x", "sha256": hashlib.sha256(b"").hexdigest(), "bytes": 0}
            with self.assertRaisesRegex(ValueError, "duplicate"):
                verify_manifest(root, self._manifest([entry, dict(entry)]))

    def test_release_manifest_rejects_non_normalized_duplicate_and_unlisted_files(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            artifact = root / "x"
            artifact.write_bytes(b"contents")
            entry = {"path": "x", "sha256": hashlib.sha256(b"contents").hexdigest(), "bytes": 8}
            alias = dict(entry, path="folder/../x")
            with self.assertRaisesRegex(ValueError, "not normalized"):
                verify_manifest(root, self._manifest([entry, alias]))

            (root / "unlisted.bin").write_bytes(b"extra")
            with self.assertRaisesRegex(ValueError, "unmanifested files"):
                verify_manifest(root, self._manifest([entry]))

    def test_release_manifest_rejects_platform_ambiguous_backslash_paths(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            artifact = root / "folder\\..\\outside"
            artifact.write_bytes(b"contents")
            entry = {"path": artifact.name,
                     "sha256": hashlib.sha256(b"contents").hexdigest(), "bytes": 8}
            with self.assertRaisesRegex(ValueError, "path is not normalized"):
                verify_manifest(root, self._manifest([entry]))

    def test_release_manifest_rejects_missing_or_invalid_identity_metadata(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            valid = self._manifest([])
            verify_manifest(root, valid)
            for field, bad_value in [
                ("SoftwareVersion", "preview"),
                ("SchemaVersion", " "),
                ("AcceptedBatchID", ""),
                ("SourceCommit", "not-a-commit"),
                ("DirtyBuild", "false"),
                ("NativeAcceptance", True),
            ]:
                with self.subTest(field=field):
                    malformed = {**valid, field: bad_value}
                    with self.assertRaisesRegex(ValueError, "release manifest"):
                        verify_manifest(root, malformed)
            for field in ("SoftwareVersion", "SchemaVersion", "AcceptedBatchID",
                          "SourceCommit", "DirtyBuild", "NativeAcceptance"):
                with self.subTest(missing=field):
                    malformed = {key: value for key, value in valid.items() if key != field}
                    with self.assertRaisesRegex(ValueError, "release manifest"):
                        verify_manifest(root, malformed)

    def test_source_allowlist_rejects_symlinked_private_target(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "repo"
            root.mkdir()
            private = Path(temporary) / "private-config.json"
            private.write_text('{"secret":"fixture"}', encoding="utf-8")
            link = root / "public-config.json"
            link.symlink_to(private)
            with patch("scripts.package_release.run", return_value="public-config.json"):
                with self.assertRaisesRegex(RuntimeError, "escapes repository root"):
                    source_paths(root)

    def test_source_paths_reject_platform_ambiguous_backslash_name(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            with patch("scripts.package_release.run", return_value="folder\\..\\outside"):
                with self.assertRaisesRegex(RuntimeError, "not portable"):
                    source_paths(root)

    def test_source_allowlist_rejects_internal_alias_to_private_material(self):
        for destination in ("private/binding.json", ".private/binding.json", ".flowagent/backup.json", ".env", "snapshot.pbix"):
            with self.subTest(destination=destination), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                target = root / destination
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text("fictional private fixture", encoding="utf-8")
                (root / "public-config.json").symlink_to(target)
                with patch("scripts.package_release.run", return_value="public-config.json"), self.assertRaisesRegex(RuntimeError, "excluded private/runtime"):
                    source_paths(root)

    def test_source_paths_reject_windows_invalid_and_colliding_names(self):
        invalid_names = ("CON.txt", "notes.", "name:stream", "tab\tname.txt")
        for name in invalid_names:
            with self.subTest(name=name), tempfile.TemporaryDirectory() as temporary:
                with patch("scripts.package_release.run", return_value=name):
                    with self.assertRaisesRegex(RuntimeError, "not portable"):
                        source_paths(Path(temporary))
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "Report.json").write_text("fixture", encoding="utf-8")
            with patch("scripts.package_release.run", return_value="Report.json\0report.JSON"):
                with self.assertRaisesRegex(RuntimeError, "case-insensitive filesystem"):
                    source_paths(root)
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "A").write_text("fixture", encoding="utf-8")
            with patch("scripts.package_release.run", return_value="A\0a/child.txt"):
                with self.assertRaisesRegex(RuntimeError, "case-insensitive filesystem"):
                    source_paths(root)

    def test_manifest_rejects_windows_invalid_and_colliding_names(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            with self.assertRaisesRegex(ValueError, "not portable to Windows"):
                verify_manifest(root, self._manifest([{
                    "path": "CON.txt", "sha256": "0" * 64, "bytes": 0,
                }]))
            artifact = root / "Report.json"
            artifact.write_text("fixture", encoding="utf-8")
            metadata = {"sha256": hashlib.sha256(b"fixture").hexdigest(), "bytes": 7}
            with self.assertRaisesRegex(ValueError, "platform-colliding path"):
                verify_manifest(root, self._manifest([
                    {"path": "Report.json", **metadata},
                    {"path": "report.JSON", **metadata},
                ]))
            (root / "Data").write_text("fixture", encoding="utf-8")
            directory_collision = {"path": "Data", **metadata}
            with self.assertRaisesRegex(ValueError, "platform-colliding path"):
                verify_manifest(root, self._manifest([
                    directory_collision,
                    {"path": "data/value.txt", **metadata},
                ]))


    def test_source_path_fallback_excludes_tool_caches(self):
        from scripts.package_release import source_paths
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "scripts").mkdir()
            (root / "scripts" / "main.py").write_text("pass\n", encoding="utf-8")
            (root / "scripts" / "__pycache__").mkdir()
            (root / "scripts" / "__pycache__" / "main.cpython-314.pyc").write_bytes(b"cache")
            (root / ".pytest_cache").mkdir()
            (root / ".pytest_cache" / "state").write_text("cache\n", encoding="utf-8")
            names = {path.relative_to(root).as_posix() for path in source_paths(root)}
            self.assertEqual(names, {"scripts/main.py"})


if __name__ == "__main__":
    unittest.main()
