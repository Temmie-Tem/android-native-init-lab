"""The package chain cannot turn intent/partial state into install or reboot proof."""
from pathlib import Path
import struct
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'workspace/public/src/scripts/revalidation'))
import s22plus_debian_evidence_v1 as evidence
import s22plus_debian_package_v1 as package
import s22plus_debian_autoboot_profile_v1 as profile
import s22plus_debian_reboot_access_v1 as access
import test_s22plus_debian_cron_config_v1 as configuration_tests


class PackageChain(unittest.TestCase):
    key=b'K'*32

    def rows(self,phase):
        rows=configuration_tests.DurableConfiguration().rows(phase)
        elapsed=rows[-1][1]
        rows[-1:-1]=[(13,elapsed,phase,phase,52,54,0),(14,elapsed,phase,phase,777,0,54)]
        return rows

    def consume(self,rows,phase,*,selected=True,domain=True):
        chain=evidence.Chain(b'T'*32,autoboot=True,single_cpu=True,
            reboot=dict(phase=phase,initial_mount_count=34),cron_config=True,download=True,package=selected)
        for seq,(kind,ms,p,event,a,b,c) in enumerate(rows):
            row=bytearray(128);row[:8]=b'S22DER1\0'
            struct.pack_into('<IIQIIQQQII',row,8,seq,kind,ms,p,event,a,b,c,0,0)
            row[64:96]=chain.tag
            row[96:]=evidence.tag(self.key,row[:96],autoboot=True,reboot=True,cron_config=True,download=True,package=domain)
            chain.append(bytes(row),self.key)
        return chain

    def test_both_phase_completions_require_the_transaction(self):
        for phase in (1,2):
            rows=self.rows(phase);chain=self.consume(rows,phase)
            self.assertTrue(chain.complete);self.assertEqual(chain.package_complete['phase'],phase)
            for removed in ((13,),(14,),(13,14)):
                with self.subTest(phase=phase,removed=removed),self.assertRaises(ValueError):
                    self.consume([r for r in rows if r[0] not in removed],phase)

    def test_duplicate_reordered_wrong_phase_and_late_events_reject(self):
        rows=self.rows(1);at=next(i for i,r in enumerate(rows) if r[0]==13)
        cases=[rows[:at]+[rows[at]]+rows[at:],rows[:at]+list(reversed(rows[at:at+2]))+rows[at+2:]]
        for index,value in ((2,2),(3,2),(4,51),(5,53),(6,1),(1,300000)):
            changed=list(rows);r=list(changed[at]);r[index]=value;changed[at]=tuple(r);cases.append(changed)
        for changed in cases:
            with self.subTest(changed=changed[at:at+2]),self.assertRaises(ValueError):self.consume(changed,1)
        for index,value in ((4,0),(5,1),(6,53)):
            changed=list(rows);r=list(changed[at+1]);r[index]=value;changed[at+1]=tuple(r)
            with self.assertRaises(ValueError):self.consume(changed,1)

    def test_intent_alone_never_completes_or_allows_control(self):
        rows=self.rows(1);at=next(i for i,r in enumerate(rows) if r[0]==13)
        partial=rows[:at+1];chain=self.consume(partial,1)
        self.assertFalse(chain.complete);self.assertIsNone(chain.package_complete)
        with self.assertRaises(ValueError):self.consume(partial+[(9,125000,1,0,34,36,0)],1)

    def test_old_domain_or_undeclared_package_cannot_admit_events(self):
        with self.assertRaises(ValueError):self.consume(self.rows(1),1,domain=False)
        with self.assertRaises(ValueError):self.consume(self.rows(1),1,selected=False)
        old=configuration_tests.DurableConfiguration().rows(1)
        with self.assertRaises(ValueError):self.consume(old,1)

    def test_package_selection_inherits_the_correct_config_envelope_and_return(self):
        selected=dict(transition_observer=profile.PACKAGE_OBSERVER)
        self.assertEqual(profile.cron_selected(selected),'package')
        self.assertTrue(profile.cron_config_selected(selected));self.assertTrue(profile.download_selected(selected))
        run='01'*16
        _,assets=profile.payloads(run,virt=True,single_cpu=True,minimal=True,reboot=True,cron='package')
        script=assets['qualify']
        self.assertIn(b'S22_CRON_CONFIG_EVIDENCE_V1',script)
        self.assertIn(b'/run/s22-debian/cron-config',script)
        self.assertIn(('/var/lib/lab/s22-cron-config-'+run).encode(),script)
        self.assertNotIn(('/var/lib/lab/s22-cron-'+run).encode(),script)
        self.assertNotIn(b'dpkg',script)
        request=dict(operation='debian-autoboot',N=dict(namespace=package.NAMESPACE))
        self.assertTrue(access.selected(request));self.assertTrue(access.download_selected(request))


if __name__=='__main__':unittest.main()
