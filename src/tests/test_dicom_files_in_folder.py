import tempfile
import unittest
from pathlib import Path

from mcp.server.mcpserver.exceptions import ToolError

from src.server import dicom_files_in_folder
from .test_helpers import create_dataset


class DicomFilesInFolderTests(unittest.TestCase):
    def test_finds_dicom_files_recursively(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            nested_folder = folder / "nested"
            nested_folder.mkdir()

            for path in (folder / "first.dcm", nested_folder / "second.dcm"):
                dataset = create_dataset(path, "Test^Patient")
                dataset.save_as(path, little_endian=True, implicit_vr=False)

            (folder / "not-dicom.txt").write_text("not a DICOM file")

            self.assertEqual(
                dicom_files_in_folder(str(folder)),
                [
                    {"path": str((folder / "first.dcm").resolve()), "filename": "first.dcm"},
                    {
                        "path": str((nested_folder / "second.dcm").resolve()),
                        "filename": "second.dcm",
                    },
                ],
            )

    def test_rejects_invalid_folder(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "missing"

            with self.assertRaisesRegex(ToolError, "DICOM folder not found"):
                dicom_files_in_folder(str(path))
