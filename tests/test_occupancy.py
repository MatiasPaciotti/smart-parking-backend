
import pytest

from app.repositories import occupancy_repository


@pytest.mark.parametrize(
    ("occupied", "capacity", "expected_light"),
    [
        (69, 100, "green"),
        (70, 100, "yellow"),
        (95, 100, "yellow"),
        (96, 100, "red"),
        (100, 100, "red"),
    ],
)
def test_occupancy_percentage_and_traffic_light(
    monkeypatch,
    occupied,
    capacity,
    expected_light,
):
    class FakeResult:
        def fetchone(self):
            return (1, "Rodríguez Peña", capacity, occupied)

    class FakeConnection:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_value, traceback):
            return False

        def execute(self, query, params=None):
            return FakeResult()

    monkeypatch.setattr(
        occupancy_repository,
        "get_database_connection",
        lambda: FakeConnection(),
    )

    result = occupancy_repository.get_parking_occupancy("rodriguez-pena")

    assert result["capacity"] == capacity
    assert result["occupied"] == occupied
    assert result["available"] == capacity - occupied
    assert result["occupancy_percentage"] == round(
        occupied / capacity * 100, 1
    )
    assert result["traffic_light"] == expected_light
