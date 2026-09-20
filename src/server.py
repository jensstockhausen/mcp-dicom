"""MCP server for inspecting DICOM metadata."""

from functools import wraps

from .dicom_tools import (
    dicom_files_in_folder as _dicom_files_in_folder,
    find_tag as _find_tag,
    get_frame as _get_frame,
    read_tags as _read_tags,
)
from mcp.server import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from mcp.types import ToolAnnotations

mcp = MCPServer("mcp-dicom")

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

# Decorator to convert exceptions into ToolError for MCP tools
def _as_tool_error(function):
    @wraps(function)
    def wrapper(*args, **kwargs):
        try:
            return function(*args, **kwargs)
        except Exception as error:
            raise ToolError(str(error)) from error

    return wrapper


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
@_as_tool_error
def dicom_files_in_folder(path: str) -> list[dict[str, str]]:
    return _dicom_files_in_folder(path)


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
@_as_tool_error
def read_tags(path: str) -> dict[str, object]:
    return _read_tags(path)


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
@_as_tool_error
def find_tag(path: str, tag: str) -> dict[str, object]:
    return _find_tag(path, tag)


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
@_as_tool_error
def get_frame(path: str, frame: int = 0) -> dict[str, object]:
    return _get_frame(path, frame)


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
