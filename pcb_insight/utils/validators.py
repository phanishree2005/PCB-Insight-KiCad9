"""Input validation routines for PCB Insight."""

import re
from typing import Tuple


def validate_reference_format(reference: str) -> Tuple[bool, str]:
    """Validates if a reference designator matches standard electronics conventions.
    
    Valid: R1, C12, U3, D4, SW1, TP1.
    Invalid: R?, REF**, empty, ?, or numeric-only strings.
    """
    if not reference or not reference.strip():
        return False, "Reference designator is empty."
    
    cleaned = reference.strip()
    if "?" in cleaned or "*" in cleaned:
        return False, f"Reference '{cleaned}' contains unannotated placeholder characters ('?' or '*')."
    
    match = re.match(r"^([A-Za-z]+)(\d+)$", cleaned)
    if not match:
        return False, f"Reference '{cleaned}' does not match standard Prefix+Index pattern (e.g., R1, C2)."
    
    return True, "Valid"


def sanitize_string(val: str) -> str:
    """Cleans up raw parsed strings from S-expressions or IPC strings."""
    if not val:
        return ""
    # Strip quotes if present
    s = val.strip()
    if (s.startswith('"') and s.endswith('"')) or (s.startswith("'") and s.endswith("'")):
        s = s[1:-1]
    return s.strip()
