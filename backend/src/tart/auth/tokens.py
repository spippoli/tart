"""One-time codes, session tokens, and the keyed hashes they are stored as.

The key is `SESSION_KEY`: changing it invalidates every session and live code.
"""

import hashlib
import hmac
import secrets

CODE_LENGTH = 6


def new_code() -> str:
    """A one-time code of `CODE_LENGTH` decimal digits."""
    return f"{secrets.randbelow(10**CODE_LENGTH):0{CODE_LENGTH}d}"


def new_session_token() -> str:
    return secrets.token_urlsafe(32)


def keyed_hash(key: bytes, *parts: str) -> bytes:
    """HMAC-SHA-256 of the parts, each one length-prefixed so that no two lists collide."""
    message = b"".join(len(part.encode()).to_bytes(4) + part.encode() for part in parts)
    return hmac.new(key, message, hashlib.sha256).digest()


def same(a: bytes, b: bytes) -> bool:
    return hmac.compare_digest(a, b)
