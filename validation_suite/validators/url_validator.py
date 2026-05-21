"""
URL Validator Module
Provides reusable validation functions for URL and web-related fields.
"""

import re
from typing import Tuple


def validate_https_url(url: str) -> Tuple[bool, str]:
    """
    Validate HTTPS URL format.
    """
    if not url or not url.strip():
        return False, "URL cannot be empty"
    
    # Basic HTTPS URL pattern
    pattern = r'^https://[\w\-\.]+(\.[\w\-\.]+)+(/.*)?$'
    if re.match(pattern, url, re.IGNORECASE):
        return True, "Valid"
    return False, f"Invalid HTTPS URL format: {url}"


def validate_url_case_insensitive(url: str) -> Tuple[bool, str]:
    """
    Validate URL with case-insensitive domain handling.
    Strips protocol and converts to lowercase for deduplication.
    """
    if not url or not url.strip():
        return False, "URL cannot be empty"
    
    # Strip protocol
    normalized = url.lower()
    for protocol in ['https://', 'http://']:
        if normalized.startswith(protocol):
            normalized = normalized[len(protocol):]
    
    # Remove trailing slashes
    normalized = normalized.rstrip('/')
    
    # Basic validation after normalization
    if not normalized:
        return False, "URL domain cannot be empty"
    
    return True, normalized


def validate_twitter_handle(handle: str) -> Tuple[bool, str]:
    """
    Validate Twitter (X) handle format.
    Pattern: ^@?[A-Za-z0-9_]{1,15}$
    """
    if not handle or not handle.strip():
        return False, "Twitter handle cannot be empty"
    
    pattern = r'^@?[A-Za-z0-9_]{1,15}$'
    if re.match(pattern, handle):
        return True, "Valid"
    return False, f"Invalid Twitter handle format: {handle}"


def validate_email(email: str) -> Tuple[bool, str]:
    """
    Validate email format.
    Normalizes to lowercase for B2B flag validation.
    """
    if not email or not email.strip():
        return False, "Email cannot be empty"
    
    # Basic email pattern
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if re.match(pattern, email):
        # Normalize to lowercase
        return True, email.lower()
    return False, f"Invalid email format: {email}"


def validate_url_accessibility(url: str, status_code: int = 200) -> Tuple[bool, str]:
    """
    TC_URL_04: Validate working website URL.
    Simulated status check.
    """
    if status_code == 200:
        return True, "Valid (HTTP 200)"
    return False, f"URL unreachable: HTTP {status_code}"


def validate_image_url(url: str) -> Tuple[bool, str]:
    """
    TC_URL_01: Validate valid image URL extension.
    """
    pattern = r'^https?://.*\.(png|jpg|jpeg|svg|webp)$'
    if re.match(pattern, url, re.IGNORECASE):
        return True, "Valid image URL"
    return False, "Invalid image format; must be png, jpg, jpeg, svg, or webp"