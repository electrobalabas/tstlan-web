from tstlan.auth.passwords import hash_password, verify_password


def test_correct_password_verifies() -> None:
    assert verify_password(hash_password("s3cret"), "s3cret")


def test_wrong_password_is_rejected() -> None:
    assert not verify_password(hash_password("s3cret"), "guess")


def test_same_password_produces_different_hashes() -> None:
    assert hash_password("s3cret") != hash_password("s3cret")
