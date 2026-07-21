from app.core.security import create_access_token, decode_access_token, hash_password, verify_password


def test_password_hash_and_verify_roundtrip():
    hashed = hash_password("correct-horse-battery-staple")
    assert verify_password("correct-horse-battery-staple", hashed)
    assert not verify_password("wrong-password", hashed)


def test_password_hashes_are_salted_and_unique():
    h1 = hash_password("same-password")
    h2 = hash_password("same-password")
    assert h1 != h2  # bcrypt salts each hash differently


def test_access_token_roundtrip():
    token = create_access_token(subject="42")
    assert decode_access_token(token) == "42"


def test_invalid_token_returns_none():
    assert decode_access_token("not-a-real-token") is None


def test_tampered_token_is_rejected():
    token = create_access_token(subject="1")
    # Flip a character in the middle of the signature segment rather than
    # the last character: the last base64url character only encodes 2
    # bits of the final byte, so some flips there don't change the
    # decoded signature bytes at all and the tamper is a no-op.
    header, payload, signature = token.split(".")
    mutated_char = "a" if signature[5] != "a" else "b"
    tampered_signature = signature[:5] + mutated_char + signature[6:]
    tampered = f"{header}.{payload}.{tampered_signature}"
    assert decode_access_token(tampered) is None
