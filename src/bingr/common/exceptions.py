from __future__ import annotations


class BingrError(Exception):
    """Base for all custom Bingr exceptions."""


class ProcessingError(BingrError):
    """Base for all import/processing pipeline errors."""

    default_reason = "processing_error"

    def __init__(self, message, *, reason="", details=None):
        self.reason = reason or self.default_reason
        self.details = details or {}
        super().__init__(message)


class MissingSourceParamsError(ProcessingError):
    """Neither m3u_path nor url provided."""

    default_reason = "missing_source_params"

    def __init__(self):
        super().__init__("Either m3u_path or url must be provided")


class SourceFileNotFoundError(ProcessingError):
    """M3U file does not exist on disk."""

    default_reason = "file_not_found"

    def __init__(self, path):
        super().__init__(
            f"M3U file not found: {path}",
            details={"path": str(path)},
        )


class InvalidM3UFileError(ProcessingError):
    """File is not .m3u or .m3u8."""

    default_reason = "invalid_m3u_file"

    def __init__(self, name, suffix):
        super().__init__(
            f"Provided channels source is not an M3U file: {name}",
            details={"name": name, "suffix": suffix},
        )


class SourceAlreadyImportedError(ProcessingError):
    """Source record already exists in DB — the true duplicate check."""

    default_reason = "source_already_imported"

    def __init__(self, source_id, source_name, col_label, input_key):
        super().__init__(
            f"Source '{source_name}' (id={source_id}) already imported",
            details={
                "source_id": source_id,
                "source_name": source_name,
                col_label: input_key,
            },
        )


class DownloadError(ProcessingError):
    """HTTP download of the playlist failed."""

    default_reason = "download_failed"


class EnrichmentError(ProcessingError):
    """Segment enrichment failed (caught internally in import_m3u_to_db)."""

    default_reason = "enrichment_failed"


class ConfigurationError(BingrError):
    """Config/boot issues."""

    default_reason = "configuration_error"
