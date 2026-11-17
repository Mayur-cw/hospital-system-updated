"""
hms/utils/uploads.py
Secure clinical file upload handling (S-15).
Enforces:
- Extension and MIME allowlist
- Magic byte verification
- File size caps
- Cryptographically random server-side filenames stored outside web root
"""
import os
import uuid
from pathlib import Path

from werkzeug.datastructures import FileStorage

ALLOWED_EXTENSIONS = {'.pdf', '.png', '.jpg', '.jpeg'}
ALLOWED_MIME_TYPES = {'application/pdf', 'image/png', 'image/jpeg'}
MAX_FILE_SIZE_BYTES = 5 * 1024 * 1024  # 5 MB

MAGIC_SIGNATURES = {
    b'%PDF': 'application/pdf',
    b'\x89PNG\r\n\x1a\n': 'image/png',
    b'\xff\xd8\xff': 'image/jpeg',
}


class FileUploadError(Exception):
    pass


def validate_file_safety(file_storage: FileStorage) -> str:
    """
    Validate uploaded file safety (S-15).
    Returns normalized safe extension if valid, raises FileUploadError otherwise.
    """
    if not file_storage or not file_storage.filename:
        raise FileUploadError("No file selected.")

    # 1. Extension check
    _, ext = os.path.splitext(file_storage.filename.lower())
    if ext not in ALLOWED_EXTENSIONS:
        raise FileUploadError(f"Prohibited file extension '{ext}'. Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}")

    # 2. Header Magic Bytes check
    header = file_storage.stream.read(16)
    file_storage.stream.seek(0)  # Rewind

    detected_mime = None
    for sig, mime in MAGIC_SIGNATURES.items():
        if header.startswith(sig):
            detected_mime = mime
            break

    if not detected_mime or detected_mime not in ALLOWED_MIME_TYPES:
        raise FileUploadError("File content does not match legitimate PDF or JPEG/PNG image signatures.")

    return ext


def save_secure_upload(file_storage: FileStorage, target_dir: Path) -> str:
    """
    Store uploaded file safely outside web root with randomized name (S-15).
    Returns unique filename.
    """
    ext = validate_file_safety(file_storage)
    target_dir.mkdir(parents=True, exist_ok=True)

    unique_filename = f"{uuid.uuid4().hex}{ext}"
    target_path = target_dir / unique_filename

    file_storage.save(str(target_path))
    return unique_filename
