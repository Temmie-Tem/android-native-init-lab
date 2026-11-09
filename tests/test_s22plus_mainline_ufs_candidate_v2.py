"""Capability/data separation, recovery closure and dormant adoption behavior."""
import builtins
from contextlib import ExitStack
import copy
import hashlib
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'workspace/public/src/scripts/revalidation'))
import s22plus_mainline_task_v1 as task
import s22plus_mainline_ufs_candidate_v2 as candidate
from s22plus_native_records_v3 import pin,publish,read


class CapabilityTests(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup);self.root=Path(tmp.name)
        self.private=self.root/'workspace/private';self.private.mkdir(parents=True)
        self.image=dict(schema=task.IMAGE_V2)
        for source in task.source_paths(ROOT,image=self.image):
            path=self.root/source.relative_to(ROOT);path.parent.mkdir(parents=True,exist_ok=True)
            path.write_bytes(source.read_bytes())
        self.cap=dict(schema=task.CAPABILITY_SCHEMA,scope=task.CAPABILITY_SCOPE,policy=task.CAPABILITY_POLICY,
            sources=task.source_pins(self.root,image=self.image),fixed={},evidence=[],device_actions=0)
        self.bind(self.cap)

    def bind(self,cap):
        # Synthetic fixtures only; these do not qualify an artifact or a device.
        ordinal=len(list(self.private.glob('cap-*.json')))
        receipt=publish(self.private/f'cap-{ordinal}.json',cap)
        review=publish(self.private/f'review-{ordinal}.json',dict(schema='s22plus-mainline-ufs-capability-review-v2',
            scope=task.CAPABILITY_SCOPE,verdict='PASS_GO',capability=receipt,reviewer='UNIT TEST FIXTURE',findings=[]))
        self.image.update(capability=receipt,capability_review=review)
        return review

    def test_two_candidate_declarations_preserve_review_and_source_identity(self):
        before=task.source_pins(self.root,image=self.image)
        first=task.capability(self.root,image=self.image)
        for name in ('candidate-a','candidate-b'):
            publish(self.private/(name+'.json'),dict(schema=candidate.CANDIDATE_SCHEMA,name=name,
                key_commitment=hashlib.sha256(name.encode()).hexdigest()))
            self.assertEqual(task.capability(self.root,image=self.image),first)
        self.assertEqual(task.source_pins(self.root,image=self.image),before)
        self.assertFalse(set(r['path'] for r in before)&task.V2_RETIRED)
        self.assertIn('AGENTS.md',{r['path'] for r in before})
        self.assertIn(task.tasks.TARGET_CONTRACT,{r['path'] for r in before})

    def test_wrong_scope_mixed_review_or_missing_required_source_rejected(self):
        saved=copy.deepcopy(self.image);old_review=self.image['capability_review']
        cap=copy.deepcopy(self.cap);cap['scope']='OTHER_TARGET';self.bind(cap)
        with self.assertRaisesRegex(ValueError,'scope'):task.capability(self.root,image=self.image)
        self.bind(self.cap);self.image['capability_review']=old_review
        with self.assertRaisesRegex(ValueError,'review'):task.capability(self.root,image=self.image)
        self.image=saved
        cap=copy.deepcopy(self.cap);cap['sources']=cap['sources'][1:];self.bind(cap)
        with self.assertRaisesRegex(ValueError,'closure'):task.capability(self.root,image=self.image)

    def test_changed_execution_authority_or_health_invalidates_review(self):
        for relative in ('AGENTS.md',task.tasks.TARGET_CONTRACT,
            'workspace/public/src/scripts/revalidation/s22plus_mainline_session_v1.py',
            'workspace/public/src/scripts/revalidation/s22plus_native_target_io_v3.py'):
            with self.subTest(relative=relative):
                path=self.root/relative;data=path.read_bytes();path.write_bytes(data+b'\n# changed\n')
                with self.assertRaises(ValueError):task.capability(self.root,image=self.image)
                with self.assertRaises(ValueError):task.capability(self.root,image=self.image,recovery=True)
                path.write_bytes(data)

    def test_original_recovery_does_not_import_or_open_candidate_build_inputs(self):
        for relative in task.V2_BUILD:
            (self.root/relative).unlink()
        blocked={'s22plus_mainline_ufs_candidate_v2','link_initramfs','build_evidence'}
        real_import=builtins.__import__
        def importing(name,*args,**kwargs):
            if name in blocked:raise AssertionError('recovery imported candidate builder')
            return real_import(name,*args,**kwargs)
        with mock.patch('builtins.__import__',side_effect=importing):
            self.assertEqual(task.capability(self.root,image=self.image,recovery=True),self.image['capability_review'])
        with self.assertRaises(OSError):task.capability(self.root,image=self.image)
        # Eagerly imported profile -> verify -> prepare stays a real recovery dependency.
        (self.root/'workspace/public/src/mainline/s22plus_canary_h0/prepare.py').unlink()
        with self.assertRaises(OSError):task.capability(self.root,image=self.image,recovery=True)

    def test_data_cannot_select_report_or_policy(self):
        image=dict(self.image,profile=task.profile.PROFILE,namespace=task.profile.NAMESPACE,version=task.profile.VERSION,
            ufs_link=True,run_id_hex='01'*16,ap={},member={},key={},qualification={},runtime_sources={},
            debian_ram={},download_return={},candidate={})
        image['report_version']=4
        with self.assertRaisesRegex(ValueError,'shape'):candidate.selection(image)
        cap=copy.deepcopy(self.cap);cap['policy']='docs/operations/S22PLUS_MAINLINE_RAM_V1.md';self.bind(cap)
        with self.assertRaisesRegex(ValueError,'scope'):task.capability(self.root,image=self.image)


class RecipeTests(unittest.TestCase):
    def test_generated_slots_keep_content_and_other_paths_exact(self):
        manifest=dict(initramfs=dict(path='/fixture/init/initramfs.cpio.gz'),
            debian_ram=dict(package_lock=dict(path='/fixture/init/packages/package-lock.json')),
            inputs=[dict(path='/fixture/init/observer.c',sha256='a',size=1),
                    dict(path='/fixture/init/packages/package-lock.json',sha256='b',size=2),
                    dict(path='/fixed/module.ko',sha256='c',size=3)])
        template=candidate.input_template(manifest)
        moved=copy.deepcopy(manifest)
        moved['initramfs']['path']='/other/init/initramfs.cpio.gz'
        moved['debian_ram']['package_lock']['path']='/other/init/packages/package-lock.json'
        for row in moved['inputs'][:2]:row['path']=row['path'].replace('/fixture/','/other/')
        self.assertEqual(candidate.input_template(moved),template)
        moved['inputs'][0]['sha256']='changed'
        self.assertNotEqual(candidate.input_template(moved),template)
        malformed=copy.deepcopy(manifest);malformed['inputs'].pop(0)
        with self.assertRaises(ValueError):candidate.input_template(malformed)

    def test_binding_never_reproduces_or_builds(self):
        # The first shape failure is real; a timed guard cannot invoke a producer
        # as a fallback for missing qualification or unknown data.
        with mock.patch.object(candidate,'reproduce',side_effect=AssertionError('compile during guard')):
            with self.assertRaises(ValueError):candidate.binding(dict(schema=task.IMAGE_V2))




class TaskRouteTests(unittest.TestCase):
    """Real task preparation/adoption; only retained target facts are fixtures."""
    bind=CapabilityTests.bind

    def setUp(self):
        CapabilityTests.setUp(self)
        import os
        self.install=publish(self.private/'installation.json',dict(uid=os.getuid(),
            topology=task.target.lane.CANDIDATE_TOPOLOGY.removeprefix('usb:')))
        fixed=read(self.root/task.tasks.PROFILE)
        self.android=dict(ap=dict(fixed['rollback']['ap'],path=str(self.root/fixed['rollback']['ap']['path'])),
            member={'fixture':True},partition_sha256=dict(boot=fixed['start_health']['boot_sha256'],
                **fixed['start_health']['supporting_partition_sha256']))
        previous=publish(self.private/'previous.json',dict(target=dict(serial='FIXTURE123',topology=task.target.lane.SOURCE_TOPOLOGY),
            lane={'fixture':True},host_installation=self.install,recovery_evidence={'fixture':True}))
        self.previous=Path(previous['path'])
        self.image.update(profile=task.profile.PROFILE,runtime_sources={},ufs_link=True)
        self.manifest=dict(debian_ram=dict(schema=task.profile.codec.LINK_SCHEMA))
        self.stack=ExitStack();self.addCleanup(self.stack.close)
        for target,name,value in ((task.profile,'image_binding',self.manifest),
            (task.tasks,'android_artifact',self.android),(task.tasks,'validate_recovery',None),
            (task.target.lane,'validate_binding',None)):
            self.stack.enter_context(mock.patch.object(target,name,return_value=value))
        # Fixed A payload is an isolated fixture; no old recovery record is rewritten.
        real_unchanged=task.tasks.unchanged
        def unchanged(row,**kwargs):
            if row==self.android['ap']:return
            return real_unchanged(row,**kwargs)
        self.stack.enter_context(mock.patch.object(task.tasks,'unchanged',side_effect=unchanged))
        import s22plus_mainline_ufs_image_v1 as ufs
        self.stack.enter_context(mock.patch.object(ufs,'policy_for',return_value=task.CAPABILITY_POLICY))

    def prepare(self,name):
        image=publish(self.private/(name+'-image.json'),self.image)
        return task.prepare(self.root,self.private/name,Path(image['path']),self.previous)

    def test_prepare_uses_selected_review_and_snapshots_without_global_selector(self):
        first=self.prepare('one');second=self.prepare('two')
        a=read(Path(first['path']));b=read(Path(second['path']))
        self.assertEqual(a['review'],b['review']);self.assertEqual(a['review'],self.image['capability_review'])
        self.assertFalse((self.root/task.profile.REVIEW).exists())
        for record in (first,second):
            snapshot=read(Path(record['path']).parent/'source-snapshot.json')
            originals=[r['original'] for r in snapshot['sources']]
            self.assertIn(self.image['capability_review'],originals)
            self.assertIn(self.image['capability'],originals)
            self.assertFalse((Path(record['path']).parent/'grant.json').exists())

    def test_all_new_connected_entry_points_reject_unadopted_scope(self):
        from contextlib import nullcontext
        from s22plus_native_adapter_v3 import Adapter
        record=self.prepare('not-adopted');path=Path(record['path']);value=read(path)
        with mock.patch.object(task.registry,'target_session_lease',return_value=nullcontext()),\
             mock.patch.object(task.registry,'require_no_f1_owner'),\
             mock.patch.object(task.target.Android,'health',side_effect=AssertionError('device read')),\
             mock.patch.object(task,'host_ready',side_effect=AssertionError('host live setup')):
            calls=(lambda:task.validate_task(self.root,value,live=True),
                   lambda:task.readiness(self.root,path),
                   lambda:task.open_grant(self.root,path,returned_approval='fixture',operator_statement='fixture'),
                   lambda:Adapter(self.root,path.parent).prepare(task.profile.OPERATION,dict(task=record)))
            for call in calls:
                with self.assertRaisesRegex(ValueError,'common/target adoption'):call()
        self.assertFalse((path.parent/'grant.json').exists())
        self.assertFalse(list(path.parent.glob('ready-*')))

    def test_recovery_and_completed_a_skip_candidate_validation(self):
        record=self.prepare('stopped');value=read(Path(record['path']))
        with mock.patch.object(task.profile,'image_binding',side_effect=AssertionError('requalified N')):
            self.assertEqual(task.validate_task(self.root,value,live=True,recovery=True),value)
            self.assertEqual(task.validate_task(self.root,value,live=True,recovery=True,require_android=False),value)




@unittest.skipUnless(os.environ.get('S22PLUS_UFS_V2_ARTIFACT_ROOT'), 'private real artifact fixture not selected')
class RealArtifactTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.folder=Path(os.environ['S22PLUS_UFS_V2_ARTIFACT_ROOT'])
        cls.fixed=read(cls.folder/'fixed-with-auxiliary.json')
        cls.declarations=[read(cls.folder/('draft-'+n+'.json')) for n in ('a','b')]
        cls.component=candidate.checked(cls.fixed['component'])
        cls.kernel=candidate.checked(cls.fixed['kernel'])

    def runtime(self,declaration):
        return candidate.runtime_binding(declaration,self.fixed,self.component)

    def test_both_actual_runtime_and_package_joins(self):
        for declaration in self.declarations:
            manifest,_,_=self.runtime(declaration)
            loader,package,_=candidate.artifact_binding(declaration,self.fixed,self.kernel,manifest)
            candidate.byte_joins(declaration,self.fixed,loader,package,manifest)

    def test_changed_kernel_release_and_network_are_not_key_data(self):
        declaration=self.declarations[0];original=candidate.checked
        for field in ('kernel_release','network'):
            manifest=copy.deepcopy(original(declaration['manifest']))
            if field=='kernel_release':manifest[field]+='-wrong'
            else:manifest[field]['device_ip']='192.0.2.99'
            def changed(receipt):
                return manifest if receipt==declaration['manifest'] else original(receipt)
            with self.subTest(field=field),mock.patch.object(candidate,'checked',side_effect=changed):
                with self.assertRaisesRegex(ValueError,'runtime mode|network'):self.runtime(declaration)

    def test_wrong_or_empty_kernel_path_cannot_make_byte_join_vacuous(self):
        declaration=self.declarations[0];manifest,_,_=self.runtime(declaration)
        original=candidate.checked
        with tempfile.TemporaryDirectory() as name:
            empty=Path(name)/'empty';empty.touch()
            loader=copy.deepcopy(original(declaration['loader']));loader['kernel']['image']=str(empty)
            def changed(receipt):
                return loader if receipt==declaration['loader'] else original(receipt)
            with mock.patch.object(candidate,'checked',side_effect=changed):
                with self.assertRaisesRegex(ValueError,'loader capability'):
                    candidate.artifact_binding(declaration,self.fixed,self.kernel,manifest)

    def test_changed_toolchain_and_missing_raw_evidence_invalidate_reuse(self):
        fixed=copy.deepcopy(self.fixed);fixed['observer_build'][0]['sha256']='0'*64
        cap=dict(fixed=fixed,evidence=[pin(self.folder/'artifact-check-3.log')])
        with self.assertRaises(ValueError):candidate.fixed_binding(cap)
        cap=dict(fixed=self.fixed,evidence=[dict(path=str(self.folder/'missing-raw'),size=1,sha256='0'*64)])
        with self.assertRaises(OSError):candidate.fixed_binding(cap)

    def test_auxiliary_tool_and_specs_drift_reject_before_recompile(self):
        fixed=copy.deepcopy(self.fixed)
        fixed['observer_auxiliary']['inputs'][0]['sha256']='0'*64
        with self.assertRaises(ValueError):candidate.fixed_binding(dict(fixed=fixed,evidence=[]))
        declaration=self.declarations[0];manifest,producer,_=self.runtime(declaration)
        fixed=copy.deepcopy(self.fixed);fixed['observer_auxiliary']['specs_sha256']='0'*64
        with tempfile.TemporaryDirectory() as name:
            output=Path(name)/'reproduction'
            with self.assertRaisesRegex(ValueError,'auxiliary/specs'):
                candidate.reproduce(self.folder/'draft-a.json',manifest,producer,fixed,output)
            self.assertFalse((output/'observer').exists())

    def test_mixed_candidate_loader_is_rejected(self):
        first,second=self.declarations
        manifest,_,_=self.runtime(first)
        mixed=dict(first,loader=second['loader'])
        with self.assertRaisesRegex(ValueError,'loader capability'):
            candidate.artifact_binding(mixed,self.fixed,self.kernel,manifest)


if __name__=='__main__':unittest.main()
