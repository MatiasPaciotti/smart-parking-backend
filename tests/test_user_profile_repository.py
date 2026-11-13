import pytest

from app.repositories import user_repository


@pytest.mark.parametrize("campus_status", [True, False])
def test_get_user_profile_returns_is_on_campus(
    monkeypatch,
    campus_status,
):
    class FakeResult:
        def fetchone(self):
            return (
                10,
                "Usuario Prueba",
                "usuario@unsam.edu.ar",
                "user",
                "active",
                campus_status,
                "ABC123",
                12345678,
                True,
            )

    class FakeConnection:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_value, traceback):
            return False

        def execute(self, query, params=None):
            assert 'FROM "user"' in query
            assert "is_on_campus" in query
            assert params == (10,)
            return FakeResult()

    monkeypatch.setattr(
        user_repository,
        "get_database_connection",
        lambda: FakeConnection(),
    )

    result = user_repository.get_user_profile_by_id(10)

    assert result["is_on_campus"] is campus_status
    assert result["plate"] == "ABC123"
    assert result["dni"] == 12345678
    assert result["email_verified"] is True
    assert result["profile_complete"] is True