import tempfile
import unittest
from pathlib import Path

from core.resource_archive import archive_resource_path


class ResourceArchiveTests(unittest.TestCase):
    def test_directory_is_moved_to_recoverable_archive(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "MODELO_A"
            source.mkdir()
            (source / "master.png").write_bytes(b"image")

            target = archive_resource_path(
                source,
                archive_root=root / "archive",
                token="test",
            )

            self.assertFalse(source.exists())
            self.assertEqual(target.name, "MODELO_A-test")
            self.assertEqual((target / "master.png").read_bytes(), b"image")

    def test_missing_source_is_a_safe_noop(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            target = archive_resource_path(
                root / "missing",
                archive_root=root / "archive",
            )
            self.assertIsNone(target)
            self.assertFalse((root / "archive").exists())

    def test_existing_archive_target_is_not_overwritten(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "resource"
            source.mkdir()
            archive = root / "archive"
            (archive / "resource-fixed").mkdir(parents=True)

            with self.assertRaises(FileExistsError):
                archive_resource_path(source, archive, token="fixed")

            self.assertTrue(source.exists())


if __name__ == "__main__":
    unittest.main()
