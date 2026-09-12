"""Closed thermal V3 dialect; V2 keeps its original readiness interpretation."""
import s22plus_native_thermal_observer_v2 as previous

DIALECT = previous.Dialect('S22THERM3', b'RESIDENT_THERMAL3_FRAME ', False)
SENSORS = previous.SENSORS


def parse_sample(raw):
    return previous.parse_sample(raw, dialect=DIALECT)


def decode_hud(raw):
    return previous.decode_hud(raw, dialect=DIALECT)


class IO(previous.IO):
    @staticmethod
    def decode_hud(raw, run_id):
        return decode_hud(raw)


class Observer(previous.Observer):
    io_class = IO

    def __init__(self, identity, control):
        super().__init__(identity, control)
        self.__file__ = __file__
