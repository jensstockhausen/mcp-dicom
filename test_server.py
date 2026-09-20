import tempfile
import unittest
from pathlib import Path

from pydicom.dataset import FileDataset, FileMetaDataset
from pydicom.uid import ExplicitVRLittleEndian, SecondaryCaptureImageStorage, generate_uid

from server import find_tag, read_tags


class ReadTagsTests(unittest.TestCase):
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
        with self.assertRaisesRegex(ValueError, "Invalid DICOM tag"):
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

            with self.assertRaisesRegex(FileNotFoundError, "DICOM file not found"):
                read_tags(str(path))

    def test_real_file(self) -> None:
        # Replace 'path_to_real_dicom_file' with the actual path to a real DICOM file for testing
        path = "/Users/jens/Develop/dicom/data/20140410152449000_2D.dcm"
        tags = read_tags(path)
        self.assertIn("00100010", tags)  # Check that the PatientName tag exists


if __name__ == "__main__":
    unittest.main()
