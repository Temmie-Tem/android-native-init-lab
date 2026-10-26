import copy
import sys
import unittest
from pathlib import Path

from tests.test_s20plus_g986n_twrp_boot_identity_d0 import S20PlusTwrpBootIdentityD0Test as Fixture

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'workspace/public/src/scripts/revalidation'))
import s20plus_g986n_twrp_f1_health as health


class RecoveryReceiptTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        Fixture.setUpClass()
        cls.fixture = Fixture()

    def setUp(self):
        self.calls = []

    def command(self, argv, timeout, maximum):
        self.calls.append(argv)
        f = self.fixture
        if argv[1:] == ['devices', '-l']:
            return 0, f.inventory_output(), b''
        if argv[-1] == 'get-devpath':
            return 0, (f.devpath + '\n').encode(), b''
        if argv[-1] == health.identity.t2.h0.RECOVERY_SHELL_ARGUMENT:
            return 0, f.identity_output(), b''
        if argv[-1] == health.identity.BOOT_METADATA_SCRIPT:
            return 0, f.metadata_output(), b''
        self.fail('unexpected command')

    def receipt(self):
        return health.collect(predecessor=self.fixture.predecessor, command=self.command)

    def test_fixed_producer_replays_without_contact(self):
        receipt = self.receipt()
        result = health.validate(receipt, predecessor=self.fixture.predecessor,
                                 prior_boot_ids=[self.fixture.predecessor['boot_id_sha256']])
        self.assertEqual(len(self.calls), 7)
        self.assertEqual(result['health_kind'], 'retained_t2_recovery')
        self.assertIs(result['android_health_verified'], False)
        self.assertIs(result['boot_content_verified'], False)

    def test_tampering_cannot_be_promoted_to_health(self):
        receipt = self.receipt()
        mutations = [
            lambda r: r['health'].update(android_health_verified=True),
            lambda r: r['health'].update(boot_content_verified=True),
            lambda r: r['health']['observation'].update(device_writes=False),
            lambda r: r['transcript'][0].update(returncode=False),
            lambda r: r['transcript'][0].update(stdout_hex='00' * 200000),
            lambda r: r['transcript'][0].update(stdout_hex='GG'),
            lambda r: r['transcript'][1]['argv'].__setitem__(2, 'FOREIGN'),
            lambda r: r['transcript'].append(copy.deepcopy(r['transcript'][0])),
            lambda r: r['predecessor'].update(serial_sha256='f' * 64),
        ]
        for mutate in mutations:
            with self.subTest(mutation=mutate):
                broken = copy.deepcopy(receipt)
                mutate(broken)
                with self.assertRaises((ValueError, health.identity.AuditError)):
                    health.validate(broken, predecessor=self.fixture.predecessor)

    def test_same_boot_is_rejected_for_terminal(self):
        receipt = self.receipt()
        with self.assertRaisesRegex(ValueError, 'not fresh'):
            health.validate(receipt, predecessor=self.fixture.predecessor,
                            prior_boot_ids=[receipt['health']['boot_id_sha256']])

    def test_negative_transport_and_wrong_identity_fail(self):
        receipt = self.receipt()
        for index in (0, 2, 3, 4):
            broken = copy.deepcopy(receipt)
            broken['transcript'][index]['returncode'] = 1
            with self.assertRaises(health.identity.AuditError):
                health.validate(broken, predecessor=self.fixture.predecessor)


if __name__ == '__main__':
    unittest.main()
