import tempfile
import unittest
from pathlib import Path

from mcp.server.mcpserver.exceptions import ToolError

from src.server import read_tags
from .test_helpers import create_dataset


class ReadTagsTests(unittest.TestCase):
    def test_reads_compliant_dicom_file(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "compliant.dcm"
            dataset = create_dataset(path, "Compliant^Patient")
            dataset.save_as(path, little_endian=True, implicit_vr=False)

            tags = read_tags(str(path))

            self.assertEqual(
                tags["00100010"]["Value"],
                [{"Alphabetic": "Compliant^Patient"}],
            )

    def test_reads_non_compliant_dicom_file(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "non_compliant.dcm"
            path.write_bytes(bytes.fromhex("100010000c000000546573745e50617469656e74"))

            tags = read_tags(str(path))

            self.assertEqual(
                tags["00100010"]["Value"],
                [{"Alphabetic": "Test^Patient"}],
            )

    def test_tolerates_empty_numeric_value(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "empty_numeric_value.dcm"
            dataset = create_dataset(path)
            dataset.FrameTimeVector = ["1.5", ""]
            dataset.save_as(path, little_endian=True, implicit_vr=False)

            tags = read_tags(str(path))

            self.assertEqual(tags["00181065"]["Value"], [1.5, None])

    def test_missing_file_raises_clear_error(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "missing.dcm"

            with self.assertRaisesRegex(ToolError, "DICOM file not found"):
                read_tags(str(path))
