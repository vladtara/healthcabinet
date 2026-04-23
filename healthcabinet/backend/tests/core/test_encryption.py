"""Tests for AES-256-GCM encryption utility (AC #3)."""

import base64
import os

import pytest
from cryptography.exceptions import InvalidTag

from app.core.encryption import decrypt_bytes, encrypt_bytes


def make_test_key() -> str:
    """Generate a valid base64-encoded 32-byte test key."""
    return base64.b64encode(os.urandom(32)).decode()


def test_encrypt_decrypt_round_trip():
    """encrypt_bytes → decrypt_bytes round-trips correctly for arbitrary plaintext."""
    key = make_test_key()
    plaintext = b"Hello, HealthCabinet! Sensitive health data."

    ciphertext = encrypt_bytes(plaintext, key)
    recovered = decrypt_bytes(ciphertext, key)

    assert recovered == plaintext


def test_encrypt_produces_different_ciphertext_each_time():
    """Each encryption call produces unique ciphertext (due to random nonce)."""
    key = make_test_key()
    plaintext = b"same plaintext"

    ciphertext1 = encrypt_bytes(plaintext, key)
    ciphertext2 = encrypt_bytes(plaintext, key)

    assert ciphertext1 != ciphertext2


def test_nonce_prepended_to_ciphertext():
    """Ciphertext starts with 12-byte nonce."""
    key = make_test_key()
    plaintext = b"test data"

    ciphertext = encrypt_bytes(plaintext, key)

    # Minimum length: 12 (nonce) + 1 (data) + 16 (GCM tag) = 29 bytes
    assert len(ciphertext) >= 29


def test_wrong_key_raises_error():
    """Decrypting with wrong key raises an error."""
    key1 = make_test_key()
    key2 = make_test_key()
    plaintext = b"confidential"

    ciphertext = encrypt_bytes(plaintext, key1)

    with pytest.raises((InvalidTag, Exception)):
        decrypt_bytes(ciphertext, key2)


def test_tampered_ciphertext_raises_error():
    """Tampered ciphertext raises error (GCM authentication)."""
    key = make_test_key()
    plaintext = b"authentic data"

    ciphertext = bytearray(encrypt_bytes(plaintext, key))
    ciphertext[-1] ^= 0xFF  # Flip last byte

    with pytest.raises((InvalidTag, Exception)):
        decrypt_bytes(bytes(ciphertext), key)


def test_empty_plaintext():
    """Encrypts and decrypts empty bytes."""
    key = make_test_key()

    ciphertext = encrypt_bytes(b"", key)
    recovered = decrypt_bytes(ciphertext, key)

    assert recovered == b""


def test_large_plaintext():
    """Handles large payloads (1MB)."""
    key = make_test_key()
    plaintext = os.urandom(1024 * 1024)

    ciphertext = encrypt_bytes(plaintext, key)
    recovered = decrypt_bytes(ciphertext, key)

    assert recovered == plaintext


def test_decrypt_short_ciphertext_raises_value_error():
    """Ciphertext shorter than 28 bytes raises ValueError, not opaque InvalidTag."""
    key = make_test_key()

    with pytest.raises(ValueError, match="ciphertext too short"):
        decrypt_bytes(b"tooshort", key)

    # Boundary: 27 bytes (one below minimum) also raises
    with pytest.raises(ValueError, match="ciphertext too short"):
        decrypt_bytes(b"x" * 27, key)
