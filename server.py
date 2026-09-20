"""MCP server for inspecting DICOM metadata."""

from collections.abc import Iterable
from pathlib import Path

import pydicom
from pydicom.dataset import Dataset
from pydicom.tag import Tag
from mcp.server import MCPServer
from mcp.types import ToolAnnotations
from pydicom.errors import InvalidDicomError

mcp = MCPServer("mcp-dicom")

_NUMERIC_VRS = {"AT", "DS", "FD", "FL", "IS", "SL", "SS", "SV", "UL", "US", "UV"}

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
    return _read_dataset(path).to_json_dict()

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
        raise ValueError(f"Invalid DICOM tag: {tag}") from error

    dataset = _read_dataset(path)
    element = dataset.get(normalized_tag)
    if element is None:
        return {}

    tag_key = f"{normalized_tag.group:04X}{normalized_tag.element:04X}"
    return {tag_key: element.to_json_dict(None, 1024)}


if __name__ == "__main__":
    mcp.run()
