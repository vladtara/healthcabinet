"""
AES-256-GCM encryption utility.

IMPORTANT: encrypt_bytes/decrypt_bytes MUST only be called from repository.py files.
Never call from service.py or router.py — this is enforced by Ruff rules.
"""

import base64
import os

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from app.core.config import settings


def encrypt_bytes(plaintext: bytes, key_b64: str | None = None) -> bytes:
    """Encrypt bytes using AES-256-GCM. Returns nonce (12 bytes) + ciphertext."""
    key = base64.b64decode(key_b64 or settings.ENCRYPTION_KEY)
    nonce = os.urandom(12)
    return nonce + AESGCM(key).encrypt(nonce, plaintext, None)


def decrypt_bytes(ciphertext: bytes, key_b64: str | None = None) -> bytes:
    """Decrypt AES-256-GCM ciphertext. Expects nonce (12 bytes) prepended."""
    if len(ciphertext) < 28:  # 12 (nonce) + 16 (GCM tag) minimum
        raise ValueError("ciphertext too short")
    key = base64.b64decode(key_b64 or settings.ENCRYPTION_KEY)
    return AESGCM(key).decrypt(ciphertext[:12], ciphertext[12:], None)
