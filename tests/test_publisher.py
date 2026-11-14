"""Tests for grouping historical rows by the timestamp they are published at."""

from src.historical.interval import Interval
from src.historical.lap import Lap
from src.historical.position import Position
from src.simulation.mqtt_client import MqttClient
from src.simulation.publisher import IntervalPublisher, LapPublisher, PositionPublisher

T0 = "2026-03-29T06:00:10+00:00"
T1 = "2026-03-29T06:00:20+00:00"


def _interval(date: str, driver_number: int) -> Interval:
    return Interval(
        date=date,
        driver_number=driver_number,
        gap_to_leader=1.2,
        interval=0.4,
        meeting_key=1,
        session_key=2,
    )


def _lap(date_start: str, driver_number: int) -> Lap:
    return Lap(
        date_start=date_start,
        driver_number=driver_number,
        duration_sector_1=30.0,
        duration_sector_2=40.0,
        duration_sector_3=25.0,
        i1_speed=280,
        i2_speed=290,
        is_pit_out_lap=False,
        lap_duration=95.0,
        lap_number=3,
        meeting_key=1,
        segments_sector_1=[1],
        segments_sector_2=[2],
        segments_sector_3=[3],
        session_key=2,
        st_speed=300,
    )


def _position(date: str, driver_number: int, position: int) -> Position:
    return Position(
        date=date,
        driver_number=driver_number,
        meeting_key=1,
        position=position,
        session_key=2,
    )


def test_interval_lookup_groups_rows_by_date() -> None:
    """Group interval rows under their date and keep input order."""
    first = _interval(T0, driver_number=1)
    later = _interval(T1, driver_number=81)
    second = _interval(T0, driver_number=44)
    publisher = IntervalPublisher([first, later, second], MqttClient())
    assert publisher._lookup == {
        T0: [first, second],
        T1: [later],
    }


def test_interval_lookup_is_empty_without_rows() -> None:
    """Return no timestamps when there are no interval rows."""
    publisher = IntervalPublisher([], MqttClient())
    assert publisher._lookup == {}


def test_lap_lookup_groups_rows_by_date_start() -> None:
    """Group lap snapshots under date_start and keep input order."""
    first = _lap(T0, driver_number=1)
    later = _lap(T1, driver_number=81)
    second = _lap(T0, driver_number=44)
    publisher = LapPublisher([first, later, second], MqttClient())
    assert publisher._lookup == {
        T0: [first, second],
        T1: [later],
    }


def test_lap_lookup_is_empty_without_rows() -> None:
    """Return no timestamps when there are no lap rows."""
    publisher = LapPublisher([], MqttClient())
    assert publisher._lookup == {}


def test_position_lookup_groups_rows_by_date() -> None:
    """Group position changes under their date and keep input order."""
    first = _position(T0, driver_number=1, position=1)
    later = _position(T1, driver_number=81, position=3)
    second = _position(T0, driver_number=44, position=2)
    publisher = PositionPublisher([first, later, second], MqttClient())
    assert publisher._lookup == {
        T0: [first, second],
        T1: [later],
    }


def test_position_lookup_is_empty_without_rows() -> None:
    """Return no timestamps when there are no position rows."""
    publisher = PositionPublisher([], MqttClient())
    assert publisher._lookup == {}
