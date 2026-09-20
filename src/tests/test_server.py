import tempfile
import unittest
import base64
from io import BytesIO
from pathlib import Path

from PIL import Image
from pydicom.dataset import FileDataset, FileMetaDataset
from pydicom.uid import ExplicitVRLittleEndian, SecondaryCaptureImageStorage, generate_uid
from mcp.server.mcpserver.exceptions import ToolError

from src.server import dicom_files_in_folder, find_tag, get_frame, read_tags


class ReadTagsTests(unittest.TestCase):
    def _create_pixel_dataset(self, path: Path, frames: int = 1) -> None:
        file_meta = FileMetaDataset()
        file_meta.MediaStorageSOPClassUID = SecondaryCaptureImageStorage
        file_meta.MediaStorageSOPInstanceUID = generate_uid()
        file_meta.TransferSyntaxUID = ExplicitVRLittleEndian
        file_meta.ImplementationClassUID = generate_uid()

        dataset = FileDataset(path, {}, file_meta=file_meta, preamble=b"\0" * 128)
        dataset.Rows = 2
        dataset.Columns = 2
        dataset.SamplesPerPixel = 1
        dataset.PhotometricInterpretation = "MONOCHROME2"
        dataset.BitsAllocated = 8
        dataset.BitsStored = 8
        dataset.HighBit = 7
        dataset.PixelRepresentation = 0
        if frames > 1:
            dataset.NumberOfFrames = frames
        dataset.PixelData = bytes(range(frames * 4))
        dataset.save_as(path, little_endian=True, implicit_vr=False)

    def test_finds_dicom_files_recursively(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            nested_folder = folder / "nested"
            nested_folder.mkdir()

            for path in (folder / "first.dcm", nested_folder / "second.dcm"):
                file_meta = FileMetaDataset()
                file_meta.MediaStorageSOPClassUID = SecondaryCaptureImageStorage
                file_meta.MediaStorageSOPInstanceUID = generate_uid()
                file_meta.TransferSyntaxUID = ExplicitVRLittleEndian
                file_meta.ImplementationClassUID = generate_uid()

                dataset = FileDataset(
                    path,
                    {},
                    file_meta=file_meta,
                    preamble=b"\0" * 128,
                )
                dataset.PatientName = "Test^Patient"
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

    def test_dicom_files_in_folder_rejects_invalid_folder(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "missing"

            with self.assertRaisesRegex(ToolError, "DICOM folder not found"):
                dicom_files_in_folder(str(path))

    def test_get_frame_returns_decoded_pixel_data(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "pixels.dcm"
            self._create_pixel_dataset(path, frames=2)

            result = get_frame(str(path), frame=1)

            self.assertEqual(result["frame"], 1)
            self.assertEqual(result["shape"], [2, 2])
            self.assertEqual(result["dtype"], "uint8")
            self.assertEqual(result["mime_type"], "image/jpeg")
            with Image.open(BytesIO(base64.b64decode(result["data"]))) as image:
                self.assertEqual(image.format, "JPEG")
                self.assertEqual(image.size, (2, 2))
                self.assertEqual(image.mode, "L")

    def test_get_frame_rejects_invalid_frame(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "pixels.dcm"
            self._create_pixel_dataset(path)

            with self.assertRaisesRegex(ToolError, "out of range"):
                get_frame(str(path), frame=1)

    def test_reads_compliant_dicom_file(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "compliant.dcm"
            file_meta = FileMetaDataset()
            file_meta.MediaStorageSOPClassUID = SecondaryCaptureImageStorage
            file_meta.MediaStorageSOPInstanceUID = generate_uid()
            file_meta.TransferSyntaxUID = ExplicitVRLittleEndian
            file_meta.ImplementationClassUID = generate_uid()

            dataset = FileDataset(path, {}, file_meta=file_meta, preamble=b"\0" * 128)
            dataset.PatientName = "Compliant^Patient"
            dataset.save_as(path, little_endian=True, implicit_vr=False)

            tags = read_tags(str(path))

            self.assertEqual(
                tags["00100010"]["Value"],
                [{"Alphabetic": "Compliant^Patient"}],
            )

            self.assertEqual(
                find_tag(str(path), "00100010"),
                {
                    "00100010": {
                        "vr": "PN",
                        "Value": [{"Alphabetic": "Compliant^Patient"}],
                    }
                },
            )

    def test_find_tag_returns_empty_object_when_tag_is_missing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "missing_tag.dcm"
            file_meta = FileMetaDataset()
            file_meta.MediaStorageSOPClassUID = SecondaryCaptureImageStorage
            file_meta.MediaStorageSOPInstanceUID = generate_uid()
            file_meta.TransferSyntaxUID = ExplicitVRLittleEndian
            file_meta.ImplementationClassUID = generate_uid()

            dataset = FileDataset(path, {}, file_meta=file_meta, preamble=b"\0" * 128)
            dataset.PatientName = "Test^Patient"
            dataset.save_as(path, little_endian=True, implicit_vr=False)

            self.assertEqual(find_tag(str(path), "00100020"), {})

    def test_find_tag_rejects_invalid_tag(self) -> None:
        with self.assertRaisesRegex(ToolError, "Invalid DICOM tag"):
            find_tag("unused.dcm", "not-a-tag")

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
            file_meta = FileMetaDataset()
            file_meta.MediaStorageSOPClassUID = SecondaryCaptureImageStorage
            file_meta.MediaStorageSOPInstanceUID = generate_uid()
            file_meta.TransferSyntaxUID = ExplicitVRLittleEndian
            file_meta.ImplementationClassUID = generate_uid()

            dataset = FileDataset(path, {}, file_meta=file_meta, preamble=b"\0" * 128)
            dataset.FrameTimeVector = ["1.5", ""]
            dataset.save_as(path, little_endian=True, implicit_vr=False)

            tags = read_tags(str(path))

            self.assertEqual(tags["00181065"]["Value"], [1.5, None])

    def test_missing_file_raises_clear_error(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "missing.dcm"

            with self.assertRaisesRegex(ToolError, "DICOM file not found"):
                read_tags(str(path))

    #def test_real_file(self) -> None:
    #    # Replace 'path_to_real_dicom_file' with the actual path to a real DICOM file for testing
    #    path = "local/path/to/real_dicom_file.dcm"
    #    tags = read_tags(path)
    #    self.assertIn("00100010", tags)  # Check that the PatientName tag exists


if __name__ == "__main__":
    unittest.main()
