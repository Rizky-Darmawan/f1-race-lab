"""Tests for replaying historical race messages on a clock."""

import json
from dataclasses import asdict
from datetime import UTC, datetime

import pytest

from src.historical.interval import Interval
from src.historical.lap import Lap
from src.historical.position import Position
from src.simulation.live_simulation import HistoricalPayload, LiveSimulation
from src.simulation.mqtt_client import MqttClient

ORIGIN = datetime(2026, 3, 29, 6, 0, tzinfo=UTC)
BEFORE = "2026-03-29T05:59:50+00:00"
AT_START = "2026-03-29T06:00:00+00:00"
PLUS_10 = "2026-03-29T06:00:10+00:00"
PLUS_20 = "2026-03-29T06:00:20+00:00"
PLUS_30 = "2026-03-29T06:00:30+00:00"
OFFSET_PLUS_10 = "2026-03-29T07:00:10+01:00"
OFFSET_PLUS_20 = "2026-03-29T07:00:20+01:00"


class _RecordingMqtt(MqttClient):
    """Record session and publish calls without opening a broker connection."""

    def __init__(self) -> None:
        super().__init__()
        self.connects = 0
        self.disconnects = 0
        self.published: list[tuple[str, bytes]] = []

    def connect(self) -> None:
        self.connects += 1

    def disconnect(self) -> None:
        self.disconnects += 1

    def publish(self, topic: str, payload: bytes) -> None:
        self.published.append((topic, payload))


class _Clock:
    """Wall clock that advances only when the replay sleeps."""

    def __init__(
        self,
        readings: list[float] | None = None,
        interrupt_after: int | None = None,
    ) -> None:
        self.now = 0.0
        self.sleeps: list[float] = []
        self._readings = list(readings) if readings is not None else None
        self._interrupt_after = interrupt_after

    def perf_counter(self) -> float:
        if self._readings:
            return self._readings.pop(0)
        return self.now

    def sleep(self, seconds: float) -> None:
        self.sleeps.append(seconds)
        self.now += seconds
        if self._interrupt_after is not None and len(self.sleeps) >= self._interrupt_after:
            raise KeyboardInterrupt


def _interval(date: str, driver_number: int = 1) -> Interval:
    return Interval(
        date=date,
        driver_number=driver_number,
        gap_to_leader=1.2,
        interval=0.4,
        meeting_key=1,
        session_key=2,
    )


def _lap(date_start: str, driver_number: int = 1) -> Lap:
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


def _position(date: str, driver_number: int = 1, position: int = 1) -> Position:
    return Position(
        date=date,
        driver_number=driver_number,
        meeting_key=1,
        position=position,
        session_key=2,
    )


def _payload(
    intervals: list[Interval] | None = None,
    laps: list[Lap] | None = None,
    positions: list[Position] | None = None,
) -> HistoricalPayload:
    return HistoricalPayload(
        intervals=intervals or [],
        laps=laps or [],
        positions=positions or [],
    )


def _simulation(payload: HistoricalPayload) -> tuple[LiveSimulation, _RecordingMqtt]:
    mqtt = _RecordingMqtt()
    return LiveSimulation(payload, mqtt), mqtt


def _use_clock(monkeypatch: pytest.MonkeyPatch, clock: _Clock) -> None:
    monkeypatch.setattr("src.simulation.live_simulation.time.perf_counter", clock.perf_counter)
    monkeypatch.setattr("src.simulation.live_simulation.time.sleep", clock.sleep)


def _messages(mqtt: _RecordingMqtt) -> list[tuple[str, object]]:
    return [(topic, json.loads(payload)) for topic, payload in mqtt.published]


def _assert_session_untouched(mqtt: _RecordingMqtt) -> None:
    assert mqtt.connects == 0
    assert mqtt.disconnects == 0


def _body(row: Interval | Lap | Position) -> dict[str, object]:
    return asdict(row)


def _interval_body(date: str, driver_number: int = 1) -> dict[str, object]:
    return _body(_interval(date, driver_number))


def test_schedule_merges_feeds_in_time_order() -> None:
    """Merge interval, lap, and position timestamps into one list, earliest first."""
    simulation, _mqtt = _simulation(
        _payload(
            intervals=[_interval(PLUS_30)],
            laps=[_lap(PLUS_10)],
            positions=[_position(PLUS_20)],
        )
    )
    assert simulation._schedule(ORIGIN) == [
        (datetime(2026, 3, 29, 6, 0, 10, tzinfo=UTC), PLUS_10),
        (datetime(2026, 3, 29, 6, 0, 20, tzinfo=UTC), PLUS_20),
        (datetime(2026, 3, 29, 6, 0, 30, tzinfo=UTC), PLUS_30),
    ]


def test_schedule_lists_a_shared_timestamp_once() -> None:
    """List a timestamp shared by several feeds once."""
    simulation, _mqtt = _simulation(
        _payload(
            intervals=[_interval(PLUS_10), _interval(PLUS_30, driver_number=44)],
            laps=[_lap(PLUS_10)],
            positions=[_position(PLUS_10)],
        )
    )
    assert [stamp for _when, stamp in simulation._schedule(ORIGIN)] == [PLUS_10, PLUS_30]


def test_schedule_omits_rows_at_or_before_start() -> None:
    """Leave out rows at the start and earlier."""
    simulation, _mqtt = _simulation(
        _payload(
            intervals=[_interval(BEFORE), _interval(PLUS_10, driver_number=44)],
            laps=[_lap(AT_START)],
            positions=[_position(BEFORE)],
        )
    )
    assert [stamp for _when, stamp in simulation._schedule(ORIGIN)] == [PLUS_10]


def test_schedule_treats_naive_stamp_as_utc() -> None:
    """Treat a naive ISO stamp as UTC."""
    stamp = "2026-03-29T06:00:10"
    simulation, _mqtt = _simulation(_payload(intervals=[_interval(stamp)]))
    assert simulation._schedule(ORIGIN) == [
        (datetime(2026, 3, 29, 6, 0, 10, tzinfo=UTC), stamp),
    ]


def test_schedule_keeps_an_aware_stamp() -> None:
    """Keep an aware stamp's original text and instant."""
    simulation, _mqtt = _simulation(_payload(intervals=[_interval(OFFSET_PLUS_10)]))
    assert simulation._schedule(ORIGIN) == [
        (datetime(2026, 3, 29, 6, 0, 10, tzinfo=UTC), OFFSET_PLUS_10),
    ]


def test_schedule_is_empty_when_nothing_is_upcoming() -> None:
    """Return no timestamps when the payload is empty or every row is already due."""
    empty, _mqtt = _simulation(HistoricalPayload([], [], []))
    assert empty._schedule(ORIGIN) == []
    finished, _mqtt = _simulation(
        _payload(
            intervals=[_interval(AT_START)],
            laps=[_lap(BEFORE)],
            positions=[_position(AT_START)],
        )
    )
    assert finished._schedule(ORIGIN) == []


@pytest.mark.parametrize("speed", [0, -1])
def test_run_clock_rejects_non_positive_speed(
    monkeypatch: pytest.MonkeyPatch,
    speed: float,
) -> None:
    """Reject a speed of zero or less before connecting or publishing."""
    clock = _Clock()
    _use_clock(monkeypatch, clock)
    simulation, mqtt = _simulation(_payload(intervals=[_interval(PLUS_10)]))
    with pytest.raises(ValueError, match="speed must be greater than 0"):
        simulation.run_clock(ORIGIN, speed)
    _assert_session_untouched(mqtt)
    assert mqtt.published == []
    assert clock.sleeps == []


def test_run_clock_treats_naive_start_as_utc(monkeypatch: pytest.MonkeyPatch) -> None:
    """Treat a naive start as UTC when deciding what is already due."""
    clock = _Clock()
    _use_clock(monkeypatch, clock)
    simulation, mqtt = _simulation(
        _payload(intervals=[_interval(AT_START), _interval(PLUS_10, driver_number=44)])
    )
    simulation.run_clock(datetime(2026, 3, 29, 6, 0, 0), 1)
    _assert_session_untouched(mqtt)
    assert clock.sleeps == [10.0]
    assert _messages(mqtt) == [("interval", _interval_body(PLUS_10, driver_number=44))]


def test_run_clock_propagates_keyboard_interrupt(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Let a sleep interrupt escape without connecting or disconnecting."""
    clock = _Clock(interrupt_after=2)
    _use_clock(monkeypatch, clock)
    simulation, mqtt = _simulation(
        _payload(intervals=[_interval(PLUS_10), _interval(PLUS_30, driver_number=44)])
    )
    with pytest.raises(KeyboardInterrupt):
        simulation.run_clock(ORIGIN, 1)
    _assert_session_untouched(mqtt)
    assert clock.sleeps == [10.0, 20.0]
    assert _messages(mqtt) == [("interval", _interval_body(PLUS_10))]


def test_run_clock_publishes_each_stamp_in_feed_order(monkeypatch: pytest.MonkeyPatch) -> None:
    """Publish interval, then lap, then position, using the original stamp string."""
    clock = _Clock()
    _use_clock(monkeypatch, clock)
    first_interval = _interval(OFFSET_PLUS_10, driver_number=1)
    second_interval = _interval(OFFSET_PLUS_10, driver_number=44)
    lap = _lap(OFFSET_PLUS_10)
    position = _position(OFFSET_PLUS_10)
    next_interval = _interval(OFFSET_PLUS_20, driver_number=81)
    simulation, mqtt = _simulation(
        _payload(
            intervals=[first_interval, second_interval, next_interval],
            laps=[lap],
            positions=[position],
        )
    )
    simulation.run_clock(ORIGIN, 1)
    _assert_session_untouched(mqtt)
    assert _messages(mqtt) == [
        ("interval", _body(first_interval)),
        ("interval", _body(second_interval)),
        ("lap", _body(lap)),
        ("position", _body(position)),
        ("interval", _body(next_interval)),
    ]


def test_run_clock_skips_a_feed_with_no_row(monkeypatch: pytest.MonkeyPatch) -> None:
    """Publish nothing for a feed that has no row at the stamp."""
    clock = _Clock()
    _use_clock(monkeypatch, clock)
    simulation, mqtt = _simulation(_payload(intervals=[_interval(PLUS_10)]))
    simulation.run_clock(ORIGIN, 1)
    _assert_session_untouched(mqtt)
    assert [topic for topic, _payload in mqtt.published] == ["interval"]


@pytest.mark.parametrize(
    ("speed", "expected_sleeps"),
    [
        (1, [10.0, 20.0]),
        (2, [5.0, 10.0]),
    ],
)
def test_run_clock_waits_race_gap_divided_by_speed(
    monkeypatch: pytest.MonkeyPatch,
    speed: float,
    expected_sleeps: list[float],
) -> None:
    """Wait the race gap divided by speed before each stamp."""
    clock = _Clock()
    _use_clock(monkeypatch, clock)
    simulation, mqtt = _simulation(
        _payload(intervals=[_interval(PLUS_30), _interval(PLUS_10, driver_number=44)])
    )
    simulation.run_clock(ORIGIN, speed)
    _assert_session_untouched(mqtt)
    assert clock.sleeps == expected_sleeps


@pytest.mark.parametrize("elapsed", [10.0, 25.0])
def test_run_clock_publishes_a_due_stamp_without_sleeping(
    monkeypatch: pytest.MonkeyPatch,
    elapsed: float,
) -> None:
    """Publish a stamp whose wait has already elapsed without sleeping."""
    clock = _Clock(readings=[0.0, elapsed])
    _use_clock(monkeypatch, clock)
    simulation, mqtt = _simulation(_payload(intervals=[_interval(PLUS_10)]))
    simulation.run_clock(ORIGIN, 1)
    _assert_session_untouched(mqtt)
    assert clock.sleeps == []
    assert _messages(mqtt) == [("interval", _interval_body(PLUS_10))]


def test_run_clock_empty_schedule_does_not_connect(monkeypatch: pytest.MonkeyPatch) -> None:
    """Publish nothing and leave the session untouched when nothing is upcoming."""
    clock = _Clock()
    _use_clock(monkeypatch, clock)
    simulation, mqtt = _simulation(HistoricalPayload([], [], []))
    simulation.run_clock(ORIGIN, 1)
    _assert_session_untouched(mqtt)
    assert mqtt.published == []
    assert clock.sleeps == []

