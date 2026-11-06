import psycopg

from app.repositories.guest_repository import (
    delete_guest_vehicle,
    insert_guest_vehicle,
    select_guest_vehicles,
)


class DatabaseUnavailableError(Exception):
    pass


def register_guest_vehicle(plate: str, created_by: int, parking_lot_id: str) -> dict:
    try:
        return insert_guest_vehicle(
            plate=plate,
            created_by=created_by,
            parking_lot_id=parking_lot_id,
        )
    except psycopg.Error as error:
        raise DatabaseUnavailableError from error


def remove_guest_vehicle(plate: str, parking_lot_id: str) -> dict:
    try:
        return delete_guest_vehicle(
            plate=plate,
            parking_lot_id=parking_lot_id,
        )
    except psycopg.Error as error:
        raise DatabaseUnavailableError from error


def list_guest_vehicles(parking_lot_id: str) -> list[dict]:
    try:
        return select_guest_vehicles(parking_lot_id=parking_lot_id)
    except psycopg.Error as error:
        raise DatabaseUnavailableError from error
