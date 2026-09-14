"""Reconnect-profile C through the unchanged raw N/E/N owner and thermal reader.

The extra slave reference models a USB link that remains attached while the
host opens/closes its observation fd. Actual link replacement is exercised in
test_s22plus_native_reconnect_v1, where no such reference masks hangup.
"""
from contextlib import contextmanager
import os
import unittest

import test_s22plus_native_thermal_roundtrip_v3 as previous
import s22plus_resident_adoption_h0_support as support
import s22plus_native_reconnect_source_v1 as source
import s22plus_native_reconnect_fixtures as fixtures
import s22plus_native_baseline_v2_candidates as catalog


class ReconnectRoundtrip(previous.ThermalRoundtripV3):
    EXPERIMENT='p392'
    SOURCE=source

    @classmethod
    def setUpClass(cls):
        cls.resources={}
        for prefix in ('p387',cls.EXPERIMENT):
            resource=type('ReconnectOwnerFixture_'+prefix,(unittest.TestCase,),{})
            options=dict(render_source=source,metrics_transform=cls.METRICS,
                native_transform=fixtures.native_fixture) if prefix==cls.EXPERIMENT else {}
            support.compile_components(resource,catalog.DECLARATIONS[prefix],**options)
            cls.addClassCleanup(resource.doClassCleanups);cls.resources[prefix]=resource
        cls.binary=cls.resources['p387'].binary

    @contextmanager
    def running(self,case='normal'):
        with support.Fixture.running(self.resources[self.current_prefix],case) as peer:
            attached=os.dup(peer.fd) if self.current_prefix==self.EXPERIMENT else None
            try:yield peer
            finally:
                if attached is not None:os.close(attached)


if __name__=='__main__':unittest.main()
