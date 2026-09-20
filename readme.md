# mcp-dicom

## Description

A Python MCP server built with v2 of the MCP Python SDK. It reads DICOM metadata
from local files without loading pixel data.

## Requirements

- Python 3.10 or newer
- The dependencies in `requirements.txt`

Install the pinned dependencies in a virtual environment:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

## Run

Start the server over stdio:

```bash
python server.py
```

The MCP host launches the process and calls the tool below.

## Tests

Run the unit tests with verbose output:

```bash
./run_tests.sh
```

## Tool


### `dicom_files_in_folder`

Scans a folder recursively and returns a sorted list of DICOM files. Each
result contains the file's absolute `path` and `filename`. Non-DICOM and
unreadable files are skipped.

```text
dicom_files_in_folder(path="/path/to/folder")
```


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

## Skill

### `dicom_metadata_skill`

Provides basic guidance for choosing the DICOM inspection tools and identifies
the tags commonly used for Modality (`00080060`) and SOP Class UID (`00080016`).

## Resource

### `dicom-standard`

Provides the official URI for the current DICOM standard:

```text
https://dicom.nema.org/medical/dicom/current/
```


## MCP Inspector

With Node.js and `npx` available, inspect the server interactively:

```bash
npx @modelcontextprotocol/inspector python server.py
```

The VS Code MCP configuration is in `.vscode/mcp.json`.

