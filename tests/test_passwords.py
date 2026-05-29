from tstlan.auth.passwords import hash_password, verify_password


def test_hash_and_verify_roundtrip() -> None:
    digest = hash_password("s3cret-pw")
    assert verify_password(digest, "s3cret-pw")


def test_verify_rejects_wrong_password() -> None:
    digest = hash_password("s3cret-pw")
    assert not verify_password(digest, "wrong-pw")


def test_hash_is_salted() -> None:
    assert hash_password("same") != hash_password("same")


def test_hash_uses_argon2id() -> None:
    assert hash_password("x").startswith("$argon2id$")
