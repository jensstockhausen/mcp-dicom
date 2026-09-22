# mcp-dicom

## Description

A Python MCP server built with v2 of the MCP Python SDK. It reads DICOM metadata
from local files without loading pixel data.

## Requirements

- Python 3.10 or newer
- [uv](https://docs.astral.sh/uv/)

Create the environment and install the locked dependencies:

```bash
uv sync
```

## Tests

Run the unit tests with verbose output:

```bash
./run_tests.sh
```


## Run

Start the server over stdio:

```bash
uv run --locked python -m src.server
```

For convenience use the 
```
start_server.bat
```
Use this to configure the mcp in your IDE.

## Skill

### `dicom-metadata-skill`

Provides basic guidance for choosing the DICOM inspection tools.
Provided as separate [skill.md](./skill.md) file 

For convenient use 
```
update_workspace_skill.bat 
```
to do the setup for copilote in the VSC.
Do use this skill to strat the interaction wit DICOM files.
e.g. `/dicom-metadata-skill find DICOM files in <path>`

## Tools

### `dicom_files_in_folder`

Scans a folder recursively and returns a sorted list of DICOM files. Each
result contains the file's absolute `path` and `filename`. Non-DICOM and
unreadable files are skipped.

```text
dicom_files_in_folder(path="/path/to/folder")
```
The search is limited to 100 files.


### `read_tags`

Reads a DICOM file and returns its metadata as a JSON object. Pixel data is
excluded so metadata inspection does not load the image payload into memory.
Files that are missing the DICOM preamble or have non-compliant file metadata
are retried in tolerant mode.

The tool accepts a local file path:

```text
read_tags(path="/path/to/image.dcm")
```

### `find_tag`

Reads a DICOM file and searches for a given DICOM tag. If the tag is found it
is returned as a single-entry JSON object. Missing tags return an empty object.
The tag accepts compact hexadecimal notation such as `00100010`.

```text
find_tag(path="/path/to/image.dcm", tag="00100010")
```

### `get_frame`

Decodes one DICOM pixel frame and returns it as a base64-encoded JPEG, along
with its shape, data type, and `image/jpeg` MIME type. Frame numbering starts
at zero; single-frame files use frame `0`.

```text
get_frame(path="/path/to/image.dcm", frame=0)
```


## Resource

### `dicom-standard`

Provides the official URI for the current DICOM standard:

```text
https://dicom.nema.org/medical/dicom/current/
```


## MCP Inspector

Start the MCP Inspector with the root launcher so `src.server` is loaded as a
package and its relative imports work correctly:

```bash
uv run mcp dev mcp_dev.py:mcp
```
