"""Initial-inventory failure remains fatal but now has a durable stage record."""
from pathlib import Path
import json
import tempfile
import unittest
from unittest import mock
import test_s22plus_odin_transition_core as previous


class InitialInventoryDiagnostics(unittest.TestCase):
    def test_real_inventory_departure_is_preserved_before_any_odin_call(self):
        module = previous.load_module()
        usb = module.usbfs_identity
        cases = [
            (lambda: usb.UsbfsEndpointDeparture(previous.USB_008), 'usbfs-endpoint-departed'),
            (lambda: usb.UsbfsIdentityError('private identity detail'), 'usbfs-identity-failed'),
            (lambda: PermissionError(13, 'private permission detail'), 'direct-io-failed'),
            (lambda: usb.UsbfsInventoryMembershipChanged((previous.USB_008,),()), 'inventory-membership-changed'),
        ]
        for make_error, kind in cases:
            with self.subTest(kind=kind), tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                node = root / 'usb/002/008'
                node.parent.mkdir(parents=True)
                node.touch()
                calls=[]
                def inventory():
                    calls.append('inventory')
                    def snapshotter(path):
                        if kind == 'usbfs-endpoint-departed':
                            with mock.patch.object(usb.os,'stat',side_effect=FileNotFoundError(2,'private')):
                                return usb.snapshot_node(path)
                        raise make_error()
                    if kind in ('inventory-membership-changed','direct-io-failed'):
                        raise make_error()
                    return usb.capture_inventory(root=root/'usb',snapshotter=snapshotter)
                observer=usb.MeasuredUsbfsIdentityObserver(inventory_reader=inventory)
                odin=mock.Mock(side_effect=AssertionError('no Odin call before initial inventory'))
                run=root/'run'
                with module.transaction_session(run) as lease:
                    with self.assertRaises(module.OdinMeasuredEvidenceFailure):
                        module._snapshot_and_record(Path('odin4'),run,10,runner=odin,
                            device_identity=module._default_device_identity,
                            device_inventory=module._default_device_inventory,
                            endpoint_observer_factory=lambda:observer,
                            timestamp=lambda:'2026-09-08T00:00:00Z',
                            enumeration_timeout_sec=1,lease=lease)
                self.assertEqual(calls,['inventory']);odin.assert_not_called()
                files=list((run/'diagnostics').glob('*.json'));self.assertEqual(len(files),1)
                value=json.loads(files[0].read_text())
                self.assertEqual(value['observation_stage'],'initial-inventory-before-enumeration')
                self.assertEqual(value['failure_kind'],kind)
                self.assertEqual(value['attempted_snapshot_sequence'],10)
                self.assertFalse(value['snapshot_persisted'])
                self.assertNotIn('private',files[0].read_text())
                self.assertFalse((run/'receipts').exists())
                self.assertEqual(files[0].stat().st_mode & 0o777,0o400)

    def test_unsupported_diagnostic_stage_is_rejected(self):
        module=previous.load_module()
        for stage in ('after-transfer','',None):
            with self.subTest(stage=stage),self.assertRaises(module.OdinTransitionError):
                module.OdinMeasuredEvidenceFailure('usbfs-identity-failed','UsbfsIdentityError',observation_stage=stage)

if __name__=='__main__':unittest.main()
