from pathlib import Path

from pydicom.dataset import FileDataset, FileMetaDataset
from pydicom.uid import ExplicitVRLittleEndian, SecondaryCaptureImageStorage, generate_uid


def create_dataset(path: Path, patient_name: str | None = None) -> FileDataset:
    file_meta = FileMetaDataset()
    file_meta.MediaStorageSOPClassUID = SecondaryCaptureImageStorage
    file_meta.MediaStorageSOPInstanceUID = generate_uid()
    file_meta.TransferSyntaxUID = ExplicitVRLittleEndian
    file_meta.ImplementationClassUID = generate_uid()

    dataset = FileDataset(path, {}, file_meta=file_meta, preamble=b"\0" * 128)
    if patient_name is not None:
        dataset.PatientName = patient_name
    return dataset


def save_pixel_dataset(path: Path, frames: int = 1) -> None:
    dataset = create_dataset(path)
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
