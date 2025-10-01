"""
Validation utilities for Recall AI
"""
import os
import re
from typing import List, Tuple
from config import config
from exceptions import FileSizeError, UnsupportedFileTypeError


def validate_file_size(file_size: int) -> None:
    """Validate file size against configured limits"""
    max_size_bytes = config.app.max_file_size_mb * 1024 * 1024
    if file_size > max_size_bytes:
        raise FileSizeError(
            f"File size {file_size} exceeds maximum allowed size of {max_size_bytes} bytes")


def validate_file_type(filename: str) -> None:
    """Validate file type against allowed types"""
    if not filename:
        raise UnsupportedFileTypeError("Filename cannot be empty")

    file_extension = filename.lower().split('.')[-1] if '.' in filename else ''
    if file_extension not in config.app.allowed_file_types:
        raise UnsupportedFileTypeError(
            f"File type '{file_extension}' not supported. "
            f"Allowed types: {', '.join(config.app.allowed_file_types)}"
        )


def validate_text_input(text: str, max_length: int = 10000) -> str:
    """Validate and sanitize text input"""
    if not text or not text.strip():
        raise ValueError("Text input cannot be empty")

    text = text.strip()
    if len(text) > max_length:
        raise ValueError(f"Text input too long. Maximum length: {max_length}")

    # Basic sanitization
    text = re.sub(r'[^\w\s\.\,\!\?\-\:\;\(\)\"\'\/\\\n\r]', '', text)
    return text


def validate_license_key(license_key: str) -> bool:
    """Validate license key format"""
    if not license_key:
        return False

    # License key should be 16 characters, alphanumeric
    pattern = r'^[A-Z0-9]{16}$'
    return bool(re.match(pattern, license_key.upper()))


def validate_username(username: str) -> bool:
    """Validate Telegram username"""
    if not username:
        return False

    # Telegram usernames are 5-32 characters, alphanumeric and underscores
    pattern = r'^[a-zA-Z0-9_]{5,32}$'
    return bool(re.match(pattern, username))


def sanitize_filename(filename: str) -> str:
    """Sanitize filename for safe storage"""
    if not filename:
        return "unknown_file"

    # Remove path components and dangerous characters
    filename = os.path.basename(filename)
    filename = re.sub(r'[^\w\-_\.]', '_', filename)

    # Ensure it's not too long
    if len(filename) > 255:
        name, ext = os.path.splitext(filename)
        filename = name[:250] + ext

    return filename
