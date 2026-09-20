"""MCP server for inspecting DICOM metadata."""

import base64
import io
from collections.abc import Iterable
from pathlib import Path

import pydicom
from PIL import Image
from pydicom.dataset import Dataset
from pydicom.tag import Tag
from mcp.server import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from mcp.types import ToolAnnotations
from pydicom.errors import InvalidDicomError

mcp = MCPServer("mcp-dicom")

_NUMERIC_VRS = {"AT", "DS", "FD", "FL", "IS", "SL", "SS", "SV", "UL", "US", "UV"}

@mcp.resource(
    "https://dicom.nema.org/medical/dicom/current/",
    name="dicom-standard",
    title="DICOM Standard",
    description="Official current DICOM standard published by NEMA.",
    mime_type="text/uri-list",
)
def dicom_standard_uri() -> str:
    """Return the official URI for the current DICOM standard."""
    return "https://dicom.nema.org/medical/dicom/current/"

@mcp.prompt(
    title="DICOM Metadata Skill",
    description="Guide an assistant through locating and inspecting DICOM metadata.",
)
def dicom_metadata_skill() -> str:
    """Provide basic guidance for using the DICOM inspection tools."""
    return (
        "You are a DICOM metadata assistant. Use dicom_files_in_folder to find "
        "DICOM files recursively, read_tags to inspect all metadata for one file, "
        "and find_tag to retrieve a specific element. E.g. use tag 00080060 for "
        "Modality and 00080016 for SOPClassUID. Report file names and values "
        "clearly, and do not infer metadata that is absent from the file."
        "Always rely on the actual metadata present in the DICOM files and the "
        "DICOM standard."
    )

def _normalize_empty_numeric_values(dataset: Dataset) -> None:
    """Replace malformed empty numeric values before JSON conversion."""
    for element in dataset:
        if element.VR == "SQ":
            for item in element.value:
                _normalize_empty_numeric_values(item)
        elif element.VR in _NUMERIC_VRS:
            value = element.value
            if isinstance(value, Iterable) and not isinstance(value, (str, bytes)):
                element.value = [None if item == "" else item for item in value]
            elif value == "":
                element.value = None

def _read_dataset(path: str) -> Dataset:
    file_path = Path(path).expanduser()
    if not file_path.is_file():
        raise FileNotFoundError(f"DICOM file not found: {file_path}")

    try:
        dataset = pydicom.dcmread(file_path, stop_before_pixels=True)
    except InvalidDicomError:
        try:
            dataset = pydicom.dcmread(
                file_path,
                force=True,
                stop_before_pixels=True,
            )
        except (OSError, EOFError, InvalidDicomError, ValueError) as error:
            raise ValueError(f"Unable to read DICOM file: {file_path}") from error
    except (OSError, EOFError, ValueError) as error:
        raise ValueError(f"Unable to read DICOM file: {file_path}") from error

    _normalize_empty_numeric_values(dataset)
    return dataset

def _is_dicom_file(path: Path) -> bool:
    try:
        pydicom.dcmread(path, stop_before_pixels=True)
        return True
    except InvalidDicomError:
        try:
            dataset = pydicom.dcmread(path, force=True, stop_before_pixels=True)
            file_size = path.stat().st_size
            for element in dataset._dict.values():
                value_tell = getattr(element, "value_tell", None)
                length = getattr(element, "length", None)
                if (
                    value_tell is not None
                    and length is not None
                    and length != 0xFFFFFFFF
                    and value_tell + length > file_size
                ):
                    return False
            return bool(dataset)
        except (OSError, EOFError, InvalidDicomError, ValueError):
            return False
    except (OSError, EOFError, ValueError):
        return False

@mcp.tool(
    title="Find DICOM Files in Folder",
    description=(
        "Recursively scan a local folder for DICOM files. Returns a sorted "
        "list of objects containing each file's absolute path and filename. "
        "Unreadable and non-DICOM files are skipped."
    ),
    annotations=ToolAnnotations(
        readOnlyHint=True,
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=False,
    ),
    structured_output=True,
)
def dicom_files_in_folder(path: str) -> list[dict[str, str]]:
    """Recursively find DICOM files and return their paths and filenames."""
    try:
        folder = Path(path).expanduser()
        if not folder.exists():
            raise FileNotFoundError(f"DICOM folder not found: {folder}")
        if not folder.is_dir():
            raise NotADirectoryError(f"DICOM folder is not a directory: {folder}")

        files = []
        for file_path in sorted(folder.rglob("*")):
            if file_path.is_file() and _is_dicom_file(file_path):
                absolute_path = file_path.resolve()
                files.append({"path": str(absolute_path), "filename": file_path.name})
        return files
    except (OSError, TypeError, ValueError) as error:
        raise ToolError(str(error)) from error

@mcp.tool(
    title="Read DICOM Metadata",
    description=(
        "Read all available DICOM metadata from a local file as a JSON object. "
        "Pixel data is excluded, and files without a standard DICOM preamble "
        "are read in tolerant mode when possible."
    ),
    annotations=ToolAnnotations(
        readOnlyHint=True,
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=False,
    ),
    structured_output=True,
)
def read_tags(path: str) -> dict[str, object]:
    """Read all DICOM metadata except pixel data from a local file."""
    try:
        return _read_dataset(path).to_json_dict()
    except (OSError, TypeError, ValueError) as error:
        raise ToolError(str(error)) from error

@mcp.tool(
    title="Find DICOM Tag",
    description=(
        "Find one DICOM metadata element in a local file. The tag must be "
        "provided as eight hexadecimal digits, such as 00080060 for Modality. "
        "Returns a single-entry JSON object, or an empty object when absent."
    ),
    annotations=ToolAnnotations(
        readOnlyHint=True,
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=False,
    ),
    structured_output=True,
)
def find_tag(path: str, tag: str) -> dict[str, object]:
    """Find one DICOM metadata element by its eight-digit hexadecimal tag."""
    try:
        normalized_tag = Tag(tag)
    except (TypeError, ValueError) as error:
        raise ToolError(f"Invalid DICOM tag: {tag}") from error

    try:
        dataset = _read_dataset(path)
        element = dataset.get(normalized_tag)
        if element is None:
            return {}

        tag_key = f"{normalized_tag.group:04X}{normalized_tag.element:04X}"
        return {tag_key: element.to_json_dict(None, 1024)}
    except (OSError, TypeError, ValueError) as error:
        raise ToolError(str(error)) from error

@mcp.tool(
    title="Get DICOM Frame",
    description=(
        "Decode one DICOM pixel frame and return it as a base64-encoded JPEG, "
        "along with the frame shape and NumPy data type. Frame numbering starts "
        "at zero."
    ),
    annotations=ToolAnnotations(
        readOnlyHint=True,
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=False,
    ),
    structured_output=True,
)
def get_frame(path: str, frame: int = 0) -> dict[str, object]:
    """Decode and return one DICOM pixel frame as a base64-encoded JPEG."""
    try:
        if not isinstance(frame, int) or isinstance(frame, bool):
            raise TypeError("Frame must be a non-negative integer")
        if frame < 0:
            raise ValueError("Frame must be a non-negative integer")

        file_path = Path(path).expanduser()
        if not file_path.is_file():
            raise FileNotFoundError(f"DICOM file not found: {file_path}")

        dataset = pydicom.dcmread(file_path)
        if "PixelData" not in dataset:
            raise ValueError(f"DICOM file has no pixel data: {file_path}")

        pixel_array = dataset.pixel_array
        number_of_frames = int(getattr(dataset, "NumberOfFrames", 1))
        if frame >= number_of_frames:
            raise IndexError(
                f"Frame {frame} is out of range; DICOM contains "
                f"{number_of_frames} frame(s)"
            )

        selected_frame = pixel_array if number_of_frames == 1 else pixel_array[frame]
        image = Image.fromarray(selected_frame)
        jpeg_buffer = io.BytesIO()
        image.save(jpeg_buffer, format="JPEG")
        return {
            "frame": frame,
            "shape": list(selected_frame.shape),
            "dtype": str(selected_frame.dtype),
            "mime_type": "image/jpeg",
            "data": base64.b64encode(jpeg_buffer.getvalue()).decode("ascii"),
        }
    except Exception as error:
        raise ToolError(str(error)) from error


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
