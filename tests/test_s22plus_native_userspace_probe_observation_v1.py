"""Actual C/PTY wire proof and raw rederivation for the selected child workload."""
import unittest
from unittest import mock

import test_s22plus_native_root_inspect_observation_v1 as inspection
import test_s22plus_native_observation_v3 as base
import s22plus_native_observation_v3 as observation
import s22plus_native_userspace_probe_profile_v1 as profile
from test_s22plus_native_userspace_probe_v1 import BINDING, fixture


class UserspaceObservationTests(inspection.RootInspectionObservationTests):
    profile = profile
    fixture = staticmethod(fixture)
    binding = BINDING
    command_prefix = 'exec /s22-userspace-probe probe '
    result_key = 'userspace_probe'
    expected_status = 'PASS_PROBE_COMPLETED'

    def test_complete_negative_child_is_not_promoted_by_outer_zero_exit(self):
        with mock.patch.object(profile,'image_binding',return_value=BINDING),self.running() as ctx:
            (ctx.folder/'inspection.bin').write_bytes(fixture(output=b'wrong\n'))
            result=observation.observe(ctx.folder/'negative-output',self.image,base.HostFixture(ctx),ending='detach',hud=False,
                guard=lambda:None,before_terminal=lambda:None,before_extra=lambda value:None,first_boot=True,
                profile=profile.SELECTION)
            child=result['proof']['userspace_probe']
            self.assertEqual(child['status'],'PASS_PROBE_COMPLETED');self.assertFalse(child['userspace_proved'])
            self.assertTrue(result['proof']['native_health_proved']);self.assertTrue(result['proof']['detach_ack_observed'])


if __name__=='__main__':unittest.main()
