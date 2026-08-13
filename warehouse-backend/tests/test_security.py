from core.security import create_access_token, decode_access_token, hash_password, verify_password


def test_password_and_token_roundtrip() -> None:
    password_hash = hash_password("correct horse battery staple")
    assert verify_password("correct horse battery staple", password_hash)
    assert not verify_password("wrong", password_hash)
    claims = decode_access_token(create_access_token({"user_id": "1", "role": "OWNER", "warehouse_id": None}))
    assert claims["role"] == "OWNER"
