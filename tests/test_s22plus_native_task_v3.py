"""Task/artifact provenance and the fixed root installation input boundary."""
import copy
import os
from pathlib import Path
import pwd
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'workspace/public/src/scripts/revalidation'))
import s22plus_native_adapter_v3 as adapter
import s22plus_native_host_v3 as host
import s22plus_native_host_install_v3 as installer
import s22plus_native_records_v3 as records
import s22plus_native_task_v3 as task
from test_s22plus_boot_only_f1_transport import make_ap


class TaskTests(unittest.TestCase):
    def setUp(self):
        temporary=tempfile.TemporaryDirectory(); self.addCleanup(temporary.cleanup)
        self.root=Path(temporary.name)

    def image(self,profile='thermal-v3-reconnect-v1'):
        ap=self.root/'AP.tar.md5';make_ap(ap)
        key=self.root/'key';key.write_bytes(b'k'*32)
        source=self.root/'fixture.c';source.write_text('/* fixture producer identity */\n')
        sources={'fixture.c':{k:v for k,v in records.pin(source).items() if k!='path'}}
        with adapter.transport.pin_boot_only_ap(ap,label='fixture',expected_size=ap.stat().st_size,
                expected_sha256=records.digest(ap.read_bytes())) as opened:
            member=adapter.transport.boot_only_member_receipt(opened,label='fixture')
        image=dict(schema='s22plus-native-image-v3',namespace='p998',run_id_hex='1'*32,
            profile=profile,version='v0.2.1',ap=records.pin(ap),member=member,
            key=records.pin(key),runtime_sources=sources)
        package=dict(ap_tar_md5={k:image['ap'][k] for k in ('size','sha256')},
            boot_img_lz4={k:member[k] for k in ('size','sha256')})
        built=dict(schema='s22plus-native-thermal-build-v1',verdict='PASS_NATIVE_THERMAL_BUILD_H0',
            byte_identical=True,candidate=dict(a=package,b=package),source_inputs=sources,
            run_id_hex=image['run_id_hex'],native_selection=dict(namespace=image['namespace'],
                display_version=image['version'],auth_key={k:image['key'][k] for k in ('size','sha256')}))
        if profile=='thermal-v3-reconnect-ufs-v1':
            built['native_selection']['runtime_profile']=dict(storage_profile='fyg8-stock-ufs-v1')
        builder=self.root/'builder.json';records.publish(builder,built)
        exporter=Path(adapter.__file__).resolve().parents[1]/'analysis'/(
            's22plus_native_ufs_artifact_v1_h0.py' if profile=='thermal-v3-reconnect-ufs-v1'
            else 's22plus_native_artifact_v3_h0.py')
        qualification=self.root/'qualification.json'
        records.publish(qualification,dict(schema='s22plus-native-artifact-qualification-v3',
            image=image,builder_result=records.pin(builder),ab_identical=True,actual_ap_join=True,
            exporter=records.pin(exporter)))
        return dict(image,qualification=records.pin(qualification))

    def test_ufs_profile_requires_its_own_exporter_and_producer_profile(self):
        image=self.image('thermal-v3-reconnect-ufs-v1');adapter.image_valid(image,artifact_bytes=True)
        qualification=records.read(Path(image['qualification']['path']))
        original=copy.deepcopy(qualification)
        qualification['exporter']=records.pin(Path(adapter.__file__).resolve().parents[1]/
            'analysis/s22plus_native_artifact_v3_h0.py')
        bad=copy.deepcopy(image);bad['qualification']=records.publish(self.root/'wrong-exporter.json',qualification)
        with self.assertRaisesRegex(ValueError,'actual A/B producer'):adapter.image_valid(bad)
        built=records.read(Path(original['builder_result']['path']))
        built['native_selection']['runtime_profile']['storage_profile']='different-initialization'
        original['builder_result']=records.publish(self.root/'wrong-producer.json',built)
        bad['qualification']=records.publish(self.root/'wrong-producer-qualification.json',original)
        with self.assertRaisesRegex(ValueError,'selected initialization profile'):adapter.image_valid(bad)

    def test_actual_ap_receipt_is_joined_to_frozen_builder_key_member_and_source(self):
        image=self.image();adapter.image_valid(image,artifact_bytes=True)
        for key,value in (('runtime_sources',{}),('run_id_hex','2'*32),('version','v0.2.2')):
            bad=copy.deepcopy(image);bad[key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):adapter.image_valid(bad)
        # Rewriting both descriptive records still cannot change the builder's
        # actual key/AP/source joins.
        bad=copy.deepcopy(image);bad['key']['sha256']='f'*64
        with self.assertRaises(ValueError):adapter.image_valid(bad)
        Path(image['ap']['path']).write_bytes(b'damaged')
        with self.assertRaises(adapter.transport.F1TransportError):adapter.image_valid(image,artifact_bytes=True)

    def test_runtime_scope_requires_the_reviewed_source_set(self):
        image=self.image()
        profile=dict(rollback=dict(ap=dict(path='AP.tar.md5',size=image['ap']['size'],sha256=image['ap']['sha256'])),
            transport=dict(odin=dict(path='/fixture/odin',size=1,sha256='a'*64)),
            start_health=dict(boot_sha256='1'*64,supporting_partition_sha256={k:'2'*64 for k in ('vendor_boot','dtbo','recovery')}))
        profile_path=self.root/task.PROFILE;profile_path.parent.mkdir(parents=True);records.publish(profile_path,profile)
        review=self.root/'review.json';records.publish(review,dict(runtime_sources=image['runtime_sources']))
        installation=self.root/'host.json';records.publish(installation,dict(uid=os.getuid(),topology='3-1.3'))
        value=dict(schema='s22plus-native-task-v3',target=dict(serial='FIXTURE123',topology='usb:2-1.3'),lane={},
            N=image,E=None,A=dict(ap=image['ap'],member=image['member'],partition_sha256=dict(boot='1'*64,
                **{k:'2'*64 for k in ('vendor_boot','dtbo','recovery')})),adb={},odin=profile['transport']['odin'],
            host_installation=records.pin(installation),review=records.pin(review),recovery_evidence={},
            operations=['bootstrap'],seconds=600,operation_budget=1,recovery_mode='attended',reentry=False,
            hud=False,usb_reconnect=False,admission=None,prior_terminal=None,runtime_scope=image['runtime_sources'])
        with mock.patch.object(task,'capability',return_value=value['review']), \
                mock.patch.object(adapter.target.lane,'validate_binding'),mock.patch.object(task,'validate_recovery'):
            task.validate_task(self.root,value)
            wrong=copy.deepcopy(value);wrong['runtime_scope']={}
            with self.assertRaisesRegex(ValueError,'independently reviewed'):
                task.validate_task(self.root,wrong)

    def test_fixed_installer_rejects_source_drift_extra_destination_and_hardlink(self):
        receipt=host.prepare_installation(self.root/'prepared',uid=os.getuid(),account=pwd.getpwuid(os.getuid()).pw_name,
            topology='3-1.3')
        rows=installer.prepared(Path(receipt['path']),receipt['sha256'],os.getuid())
        self.assertEqual({str(path) for path,data,mode in rows},set(installer.DESTINATIONS))
        manifest=records.read(Path(receipt['path']));source=Path(manifest['files'][0]['source']['path'])
        linked=self.root/'linked';os.link(source,linked)
        with self.assertRaises(ValueError):installer.prepared(Path(receipt['path']),receipt['sha256'],os.getuid())
        linked.unlink()
        source.write_bytes(source.read_bytes()+b'# changed\n')
        with self.assertRaises(ValueError):installer.prepared(Path(receipt['path']),receipt['sha256'],os.getuid())
        with self.assertRaises(ValueError):installer.prepared(Path(receipt['path']),'0'*64,os.getuid())
        wrong=copy.deepcopy(manifest);wrong['files'][0]['destination']='/etc/arbitrary-root-target'
        invalid=records.publish(Path(receipt['path']).parent/'invalid-installation.json',wrong)
        with self.assertRaisesRegex(ValueError,'destination set'):
            installer.prepared(Path(invalid['path']),invalid['sha256'],os.getuid())

    def test_prior_installation_is_only_an_exact_fixed_four_or_five_file_manifest(self):
        receipt=host.prepare_installation(self.root/'prepared',uid=os.getuid(),account=pwd.getpwuid(os.getuid()).pw_name,
            topology='3-1.3')
        previous=records.read(Path(receipt['path']))
        previous['files']=[row for row in previous['files'] if row['destination']!=installer.ACTION]
        old=records.publish(Path(receipt['path']).parent/'previous.json',previous)
        self.assertEqual(len(installer.prepared(Path(old['path']),old['sha256'],os.getuid(),previous=True)),4)
        with self.assertRaises(ValueError):installer.prepared(Path(old['path']),old['sha256'],os.getuid())
        with self.assertRaises(ValueError):installer.prepared(Path(old['path']),'0'*64,os.getuid(),previous=True)
        previous['files'][0]['destination']='/usr/bin/unrelated-program'
        bad=records.publish(Path(receipt['path']).parent/'unrelated.json',previous)
        with self.assertRaises(ValueError):installer.prepared(Path(bad['path']),bad['sha256'],os.getuid(),previous=True)


if __name__=='__main__':unittest.main()
