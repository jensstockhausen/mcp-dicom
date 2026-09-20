import tempfile
import unittest
from pathlib import Path

from mcp.server.mcpserver.exceptions import ToolError

from src.server import find_tag
from .test_helpers import create_dataset


class FindTagTests(unittest.TestCase):
    def test_returns_requested_tag(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "compliant.dcm"
            dataset = create_dataset(path, "Compliant^Patient")
            dataset.save_as(path, little_endian=True, implicit_vr=False)

            self.assertEqual(
                find_tag(str(path), "00100010"),
                {
                    "00100010": {
                        "vr": "PN",
                        "Value": [{"Alphabetic": "Compliant^Patient"}],
                    }
                },
            )

    def test_returns_empty_object_when_tag_is_missing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "missing_tag.dcm"
            dataset = create_dataset(path, "Test^Patient")
            dataset.save_as(path, little_endian=True, implicit_vr=False)

            self.assertEqual(find_tag(str(path), "00100020"), {})

    def test_rejects_invalid_tag(self) -> None:
        with self.assertRaisesRegex(ToolError, "Invalid DICOM tag"):
            find_tag("unused.dcm", "not-a-tag")
