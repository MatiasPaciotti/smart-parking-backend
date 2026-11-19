from app.repositories.qr_code_store import QrCodeStore


def test_created_code_returns_its_record_until_used():
    store = QrCodeStore()

    code, _ = store.create({"user_id": 10, "plate": "ABC123"}, 5)

    assert store.get_active(code) == {"user_id": 10, "plate": "ABC123"}

    store.mark_used(code)

    assert store.get_active(code) is None


def test_expired_code_is_not_active():
    store = QrCodeStore()

    code, _ = store.create({"user_id": 10, "plate": "ABC123"}, 0)

    assert store.get_active(code) is None


def test_unknown_code_is_not_active():
    store = QrCodeStore()

    assert store.get_active("NOEXISTE") is None
