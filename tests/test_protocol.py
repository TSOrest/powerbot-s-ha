"""Command frames must match the ones verified on a real VR7700."""
import pytest

from custom_components.powerbot_s import protocol

# Frames from the app's control plugin, tested live on 2026-10-15
FAN = {"off": 0, "soft": 1, "normal": 2, "high": 3, "low": 4, "max": 5}
WATER = {"off": 0, "low": 1, "normal": 2, "high": 3}


@pytest.mark.parametrize(
    ("frame", "expected"),
    [
        (protocol.start(3, 3), "AA15B8000000000000022202000200080300030000FD"),
        (protocol.dock(), "AA0DB80000000000000222010016"),
        (protocol.stop(), "AA0DB80000000000000222030014"),
        (protocol.pause(), "AA0DB800000000000002221B00FC"),
        (protocol.resume(), "AA0DB800000000000002221C00FB"),
        (protocol.set_suction(FAN["off"], 3), "AA10B8000000000000022204000003010C"),
        (protocol.set_suction(FAN["max"], 3), "AA10B80000000000000222040500030107"),
        (protocol.set_suction(3, WATER["low"]), "AA10B8000000000000022204030001010B"),
        (protocol.carpet_mode(False), "AA0DB800000000000002220C000B"),
        (protocol.carpet_mode(True), "AA0DB800000000000002220C010A"),
        (protocol.locate(), "AA11B80000000000000335070000000000F8"),
        (protocol.volume(50), "AA0DB800000000000002220A32DB"),
        (protocol.do_not_disturb(True, (22, 0), (8, 0)), "AA11B80000000000000222060116000800EE"),
        (protocol.select_voice(1), "AA0DB800000000000002220B010B"),
        (protocol.query_work_state(), "AA0CB800000000000003320106"),
        (protocol.query_dnd(), "AA0CB800000000000003320502"),
        (protocol.query_voice(), "AA0BB8000000000000033604"),
    ],
)
def test_frames(frame: str, expected: str) -> None:
    assert frame == expected


def test_parse_replies() -> None:
    from datetime import time

    from .conftest import REPLIES

    work = protocol.parse_work_state(REPLIES[protocol.query_work_state()])
    assert work == protocol.WorkState(
        fan=1, water=3, volume=99, carpet=True, has_mop=True, work_mode=8, area=0, work_time=0,
        child_lock=False,
    )
    dnd = protocol.parse_dnd(REPLIES[protocol.query_dnd()])
    assert dnd == protocol.DoNotDisturb(enabled=True, start=time(22, 0), end=time(8, 0))
    assert protocol.parse_voice(REPLIES[protocol.query_voice()]) == 128


@pytest.mark.parametrize("reply", [None, "", "zz", "aa0cb8", "aa0cb800000000000103368082"])
def test_parse_rejects_other_frames(reply) -> None:
    assert protocol.parse_work_state(reply) is None
    assert protocol.parse_dnd(reply) is None


def test_work_state_area_and_time_high_bits() -> None:
    from .conftest import REPLIES

    frame = bytearray.fromhex(REPLIES[protocol.query_work_state()])
    frame[18], frame[23], frame[33] = 10, 5, 0x21  # time high nibble 2, area high nibble 1
    frame[25], frame[26] = 1, 7
    work = protocol.parse_work_state(frame.hex())
    assert (work.area, work.work_time) == (265, 515)
    assert (work.fault_class, work.fault_code) == (1, 7)


def test_fault_key() -> None:
    from custom_components.powerbot_s.const import FAULT_OPTIONS, fault_key

    assert fault_key(0, 0) == "none"
    assert fault_key(1, 10) == "none"  # hidden by the app
    assert fault_key(99, 99) == "unknown_error"
    for key in (fault_key(c, k) for c in range(1, 8) for k in range(1, 40)):
        assert key in FAULT_OPTIONS


def test_manual_and_mode_frames_match_app() -> None:
    assert protocol.manual(1) == "AA15B80000000000000222020001010000000000000B"
    assert protocol.manual(0) == "AA15B80000000000000222020001000000000000000C"
    assert protocol.start(2, 2, mode=3) == "AA15B800000000000002220200020003020002000004"


def test_schedule_frames_match_app() -> None:
    assert protocol.query_schedules() == "AA0CB800000000000003340104"
    assert protocol.schedule_enabled(1, True) == "AA19B80000000000000224000600000000000000000000000102"
    assert protocol.schedule_enabled(1, False) == "AA19B80000000000000224000500000000000000000000000103"


def test_parse_schedules() -> None:
    from datetime import time

    # Recorded from the robot: one daily schedule at 10:00, turned off
    reply = "aa2ab800000000000003340100ff0a001e08020201010000000000000000000000000000000000000000b1"
    (schedule,) = protocol.parse_schedules(reply)
    assert schedule.task_id == 1
    assert schedule.days == (0, 1, 2, 3, 4, 5, 6)
    assert schedule.repeat
    assert schedule.start == time(10, 0)
    assert schedule.duration == 30
    assert (schedule.work_mode, schedule.fan, schedule.water) == (8, 2, 2)
    assert not schedule.enabled
    # No schedules: just the header
    assert protocol.parse_schedules("aa0db80000000000000334010003") == []
    assert protocol.parse_schedules(None) is None
