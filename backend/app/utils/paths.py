"""Path helpers used by the backend service layer."""

from pathlib import Path


def get_source_directories(source_files: list[str]) -> list[str]:
    """Return the unique parent directories for discovered source files."""

    return sorted({
        str(Path(file_path).parent)
        for file_path in source_files
    })