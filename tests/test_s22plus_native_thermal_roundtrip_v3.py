"""Actual V3 PID1/collector/renderer with TRDY-clear valid temperatures."""
import unittest

import test_s22plus_native_thermal_roundtrip_v2 as previous
import s22plus_native_thermal_source_v3 as source


def metrics_fixture(text):
    raw=previous.metrics_fixture(text).encode()
    raw=source.resident.replace(raw,b'.ready={1,1}',b'.ready={0,8}')
    raw=source.resident.replace(raw,b'strstr(row,"S22THERM2 ")',b'strstr(row,"S22THERM3 ")')
    raw=source.resident.replace(raw,b'old.magic=0x31525353U;return send(fd,&old,128,flags);',
        b'old.magic=0x32525353U;return send(fd,&old,sizeof(old),flags);')
    return raw.decode()


class ThermalRoundtripV3(previous.ThermalRoundtripV2):
    EXPERIMENT='p391'
    SOURCE=source
    METRICS=staticmethod(metrics_fixture)


if __name__=='__main__':unittest.main()
