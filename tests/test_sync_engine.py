"""Tests for sync engine and OSC path parsing."""

import unittest

from bridge.constants import DB_MAX, DB_MIN
from bridge.mapping import Ds100ParamKind, MappingSpec
from bridge.sync_engine import (
    SyncEngine,
    clamp_db,
    digico_aux_level_path,
    digico_aux_on_path,
    ds100_fg_routing_gain_path,
    ds100_fg_routing_mute_path,
    ds100_reverb_send_gain_path,
    osc_truthy,
    parse_digico_aux_level,
    parse_digico_aux_on,
    parse_ds100_fg_routing_gain,
    parse_ds100_fg_routing_mute,
    parse_ds100_reverb_send_gain,
)


def enspace_map(aux: int = 1, mid: str = "m1") -> MappingSpec:
    return MappingSpec(
        id=mid, digico_aux=aux, ds100_kind=Ds100ParamKind.ENSPACE_SEND.value
    )


def fg_map(aux: int = 2, fg: int = 1, mid: str = "m2") -> MappingSpec:
    return MappingSpec(
        id=mid,
        digico_aux=aux,
        ds100_kind=Ds100ParamKind.FG_ROUTING.value,
        function_group=fg,
    )


class TestClampDb(unittest.TestCase):
    def test_within_range(self) -> None:
        self.assertEqual(clamp_db(-60.0), -60.0)
        self.assertEqual(clamp_db(5.5), 5.5)

    def test_clamp_low(self) -> None:
        self.assertEqual(clamp_db(-200.0), DB_MIN)

    def test_clamp_high(self) -> None:
        self.assertEqual(clamp_db(24.0), DB_MAX)


class TestPathParsing(unittest.TestCase):
    def test_digico_aux_level(self) -> None:
        self.assertEqual(
            parse_digico_aux_level("/Input_Channels/5/Aux_Send/1/send_level"),
            (5, 1),
        )
        self.assertEqual(parse_digico_aux_level("/channel/5/send/2/level"), (5, 2))
        self.assertIsNone(parse_digico_aux_level("/channel/5/fader"))

    def test_digico_aux_on(self) -> None:
        self.assertEqual(
            parse_digico_aux_on("/Input_Channels/3/Aux_Send/1/send_on"),
            (3, 1),
        )
        self.assertEqual(
            parse_digico_aux_on("/Input_Channels/3/Aux_Send/4/On"),
            (3, 4),
        )

    def test_ds100_reverb_gain(self) -> None:
        self.assertEqual(
            parse_ds100_reverb_send_gain("/dbaudio1/matrixinput/reverbsendgain/12"),
            12,
        )
        self.assertIsNone(parse_ds100_reverb_send_gain("/dbaudio1/matrixinput/gain/12"))

    def test_ds100_fg_paths(self) -> None:
        self.assertEqual(
            parse_ds100_fg_routing_gain("/dbaudio1/soundobjectrouting/gain/3/7"),
            (3, 7),
        )
        self.assertEqual(
            parse_ds100_fg_routing_mute("/dbaudio1/soundobjectrouting/mute/3/7"),
            (3, 7),
        )
        self.assertIsNone(
            parse_ds100_fg_routing_gain("/dbaudio1/soundobjectrouting/gain/3")
        )

    def test_path_builders(self) -> None:
        self.assertEqual(
            digico_aux_level_path(3, 1),
            "/Input_Channels/3/Aux_Send/1/send_level",
        )
        self.assertEqual(
            digico_aux_on_path(3, 5),
            "/Input_Channels/3/Aux_Send/5/send_on",
        )
        self.assertEqual(
            ds100_reverb_send_gain_path(3),
            "/dbaudio1/matrixinput/reverbsendgain/3",
        )
        self.assertEqual(
            ds100_fg_routing_gain_path(2, 8),
            "/dbaudio1/soundobjectrouting/gain/2/8",
        )
        self.assertEqual(
            ds100_fg_routing_mute_path(2, 8),
            "/dbaudio1/soundobjectrouting/mute/2/8",
        )

    def test_osc_truthy(self) -> None:
        self.assertTrue(osc_truthy(1.0))
        self.assertTrue(osc_truthy(1))
        self.assertFalse(osc_truthy(0.0))
        self.assertFalse(osc_truthy(0))
        self.assertIsNone(osc_truthy("yes"))


class TestSyncEngineEnSpace(unittest.TestCase):
    def setUp(self) -> None:
        self.to_ds100_level: list[tuple[str, int, float]] = []
        self.to_ds100_mute: list[tuple[str, int, bool]] = []
        self.to_digico_level: list[tuple[int, int, float]] = []
        self.to_digico_on: list[tuple[int, int, bool]] = []
        self.engine = SyncEngine(
            start_channel=1,
            end_channel=4,
            mappings=[enspace_map(aux=1)],
            on_to_ds100_level=lambda m, ch, v: self.to_ds100_level.append(
                (m.id, ch, v)
            ),
            on_to_ds100_mute=lambda m, ch, muted: self.to_ds100_mute.append(
                (m.id, ch, muted)
            ),
            on_to_digico_level=lambda ch, aux, v: self.to_digico_level.append(
                (ch, aux, v)
            ),
            on_to_digico_on=lambda ch, aux, on: self.to_digico_on.append((ch, aux, on)),
        )

    def test_digico_to_ds100(self) -> None:
        self.engine.handle_digico_level(2, 1, -12.5)
        self.assertEqual(self.to_ds100_level, [("m1", 2, -12.5)])
        self.assertEqual(self.to_digico_level, [])

    def test_ds100_to_digico(self) -> None:
        self.engine.handle_ds100_enspace_gain(3, 4.0)
        self.assertEqual(self.to_digico_level, [(3, 1, 4.0)])
        self.assertEqual(self.to_ds100_level, [])

    def test_clamps_on_forward(self) -> None:
        self.engine.handle_digico_level(1, 1, 15.0)
        self.assertEqual(self.to_ds100_level, [("m1", 1, DB_MAX)])

        self.to_digico_level.clear()
        self.engine.handle_ds100_enspace_gain(2, -999.0)
        self.assertEqual(self.to_digico_level, [(2, 1, DB_MIN)])

    def test_channel_range_filter(self) -> None:
        self.engine.handle_digico_level(10, 1, -5.0)
        self.engine.handle_ds100_enspace_gain(0, -5.0)
        self.assertEqual(self.to_ds100_level, [])
        self.assertEqual(self.to_digico_level, [])

    def test_echo_suppression(self) -> None:
        self.engine.handle_digico_level(1, 1, -6.0)
        self.assertEqual(len(self.to_ds100_level), 1)

        self.to_ds100_level.clear()
        self.engine.handle_ds100_enspace_gain(1, -6.0)
        self.assertEqual(self.to_ds100_level, [])

    def test_aux_off_mutes_ds100_and_stores_level(self) -> None:
        self.engine.handle_digico_level(1, 1, -12.0)
        self.to_ds100_level.clear()

        self.engine.handle_digico_aux_on(1, 1, False)
        self.assertEqual(self.to_ds100_level, [("m1", 1, DB_MIN)])

        self.to_ds100_level.clear()
        self.engine.handle_digico_level(1, 1, -20.0)
        self.assertEqual(self.to_ds100_level, [])  # stored only while off

        self.engine.handle_digico_aux_on(1, 1, True)
        self.assertEqual(self.to_ds100_level, [("m1", 1, -20.0)])

    def test_ds100_while_aux_off_updates_digico_keeps_mute(self) -> None:
        self.engine.handle_digico_level(1, 1, -8.0)
        self.engine.handle_digico_aux_on(1, 1, False)
        self.to_ds100_level.clear()
        self.to_digico_level.clear()

        self.engine.handle_ds100_enspace_gain(1, -3.0)
        self.assertEqual(self.to_digico_level, [(1, 1, -3.0)])
        self.assertEqual(self.to_ds100_level, [("m1", 1, DB_MIN)])

    def test_wrong_aux_ignored(self) -> None:
        self.engine.handle_digico_level(1, 2, -5.0)
        self.assertEqual(self.to_ds100_level, [])


class TestSyncEngineFgRouting(unittest.TestCase):
    def setUp(self) -> None:
        self.to_ds100_level: list[tuple[str, int, float]] = []
        self.to_ds100_mute: list[tuple[str, int, bool]] = []
        self.to_digico_level: list[tuple[int, int, float]] = []
        self.to_digico_on: list[tuple[int, int, bool]] = []
        self.engine = SyncEngine(
            start_channel=1,
            end_channel=4,
            mappings=[fg_map(aux=3, fg=5)],
            on_to_ds100_level=lambda m, ch, v: self.to_ds100_level.append(
                (m.id, ch, v)
            ),
            on_to_ds100_mute=lambda m, ch, muted: self.to_ds100_mute.append(
                (m.id, ch, muted)
            ),
            on_to_digico_level=lambda ch, aux, v: self.to_digico_level.append(
                (ch, aux, v)
            ),
            on_to_digico_on=lambda ch, aux, on: self.to_digico_on.append((ch, aux, on)),
        )

    def test_level_forward_no_store(self) -> None:
        self.engine.handle_digico_level(2, 3, -10.0)
        self.assertEqual(self.to_ds100_level, [("m2", 2, -10.0)])

        self.to_ds100_level.clear()
        self.engine.handle_digico_aux_on(2, 3, False)
        self.assertEqual(self.to_ds100_mute, [("m2", 2, True)])
        self.assertEqual(self.to_ds100_level, [])  # no -120 store

        self.to_ds100_mute.clear()
        self.engine.handle_digico_level(2, 3, -15.0)
        self.assertEqual(self.to_ds100_level, [("m2", 2, -15.0)])  # still sends gain

        self.engine.handle_digico_aux_on(2, 3, True)
        self.assertEqual(self.to_ds100_mute[-1], ("m2", 2, False))

    def test_ds100_mute_to_digico(self) -> None:
        self.engine.handle_ds100_fg_mute(5, 1, True)
        self.assertEqual(self.to_digico_on, [(1, 3, False)])

        self.to_digico_on.clear()
        self.engine.handle_ds100_fg_mute(5, 1, False)
        self.assertEqual(self.to_digico_on, [(1, 3, True)])

    def test_ds100_fg_gain_to_digico(self) -> None:
        self.engine.handle_ds100_fg_gain(5, 2, -7.0)
        self.assertEqual(self.to_digico_level, [(2, 3, -7.0)])

    def test_other_fg_ignored(self) -> None:
        self.engine.handle_ds100_fg_gain(9, 2, -7.0)
        self.engine.handle_ds100_fg_mute(9, 2, True)
        self.assertEqual(self.to_digico_level, [])
        self.assertEqual(self.to_digico_on, [])


class TestSyncEngineMultiMapping(unittest.TestCase):
    def test_same_aux_two_targets(self) -> None:
        to_ds100: list[tuple[str, float]] = []
        engine = SyncEngine(
            start_channel=1,
            end_channel=2,
            mappings=[
                enspace_map(aux=1, mid="e"),
                fg_map(aux=1, fg=2, mid="f"),
            ],
            on_to_ds100_level=lambda m, ch, v: to_ds100.append((m.id, v)),
            on_to_ds100_mute=lambda *_: None,
            on_to_digico_level=lambda *_: None,
            on_to_digico_on=lambda *_: None,
        )
        engine.handle_digico_level(1, 1, -4.0)
        self.assertEqual(sorted(to_ds100), [("e", -4.0), ("f", -4.0)])


if __name__ == "__main__":
    unittest.main()
