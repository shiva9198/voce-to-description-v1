from pathlib import Path


def resolve_session_path(data_folder: str, filename: str) -> Path:
    """Resolve a session filename without allowing traversal outside data_folder."""
    if not isinstance(filename, str) or not filename:
        raise ValueError("A session filename is required")

    candidate_name = Path(filename).name
    if candidate_name != filename or not candidate_name.endswith(".json"):
        raise ValueError("Session filename must be a simple .json filename")

    root = Path(data_folder).resolve()
    candidate = (root / candidate_name).resolve()
    if candidate.parent != root:
        raise ValueError("Session filename resolves outside the data directory")

    return candidate
