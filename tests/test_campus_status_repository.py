import pytest

from app.repositories import campus_status_repository


@pytest.mark.parametrize("is_on_campus", [True, False])
def test_get_campus_status_returns_correct_state(
    monkeypatch,
    is_on_campus,
):
    class FakeResult:
        def fetchone(self):
            return ("active", is_on_campus)

    class FakeConnection:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_value, traceback):
            return False

        def execute(self, query, params=None):
            assert 'FROM "user"' in query
            assert "account_status" in query
            assert "is_on_campus" in query
            assert params == (10,)
            return FakeResult()

    monkeypatch.setattr(
        campus_status_repository,
        "get_database_connection",
        lambda: FakeConnection(),
    )

    result = campus_status_repository.get_campus_status_by_user_id(10)

    assert result == {
        "account_status": "active",
        "is_on_campus": is_on_campus,
    }


def test_get_campus_status_returns_none_when_user_does_not_exist(
    monkeypatch,
):
    class FakeResult:
        def fetchone(self):
            return None

    class FakeConnection:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_value, traceback):
            return False

        def execute(self, query, params=None):
            return FakeResult()

    monkeypatch.setattr(
        campus_status_repository,
        "get_database_connection",
        lambda: FakeConnection(),
    )

    result = campus_status_repository.get_campus_status_by_user_id(10)

    assert result is None