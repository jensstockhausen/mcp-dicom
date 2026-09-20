import base64
from io import BytesIO
import tempfile
import unittest
from pathlib import Path

from PIL import Image
from mcp.server.mcpserver.exceptions import ToolError

from src.server import get_frame
from .test_helpers import save_pixel_dataset


class GetFrameTests(unittest.TestCase):
    def test_returns_decoded_pixel_data(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "pixels.dcm"
            save_pixel_dataset(path, frames=2)

            result = get_frame(str(path), frame=1)

            self.assertEqual(result["frame"], 1)
            self.assertEqual(result["shape"], [2, 2])
            self.assertEqual(result["dtype"], "uint8")
            self.assertEqual(result["mime_type"], "image/jpeg")
            with Image.open(BytesIO(base64.b64decode(result["data"]))) as image:
                self.assertEqual(image.format, "JPEG")
                self.assertEqual(image.size, (2, 2))
                self.assertEqual(image.mode, "L")

    def test_rejects_invalid_frame(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "pixels.dcm"
            save_pixel_dataset(path)

            with self.assertRaisesRegex(ToolError, "out of range"):
                get_frame(str(path), frame=1)
