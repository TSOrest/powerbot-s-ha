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
    ],
)
def test_frames(frame: str, expected: str) -> None:
    assert frame == expected
