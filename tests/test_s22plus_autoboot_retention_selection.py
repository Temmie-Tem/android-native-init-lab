"""Both fixed retention consumers select qualified single-CPU declarations."""
from pathlib import Path
import sys
import unittest
from unittest import mock

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'workspace/public/src/scripts/revalidation'))
import s22plus_debian_autoboot_profile_v1 as profile
import s22plus_debian_usb_retention_v1 as retention
import s22plus_debian_file_retrieval_v1 as retrieval


class ReachedClosedOwner(Exception):pass


class RetentionSelection(unittest.TestCase):
    def route(self,consumer,built,accepted):
        records={Path('task/task.json'):dict(N=dict(profile=profile.PROFILE)),
            Path('task/closed.json'):dict(current_android_terminal=dict(path='terminal')),
            Path('build'):built,Path('terminal'):dict(operation_record=dict(path='operation'))}
        with mock.patch.object(retention,'private_path',side_effect=lambda root,p,**kw:Path(p)), \
             mock.patch.object(retention,'read',side_effect=records.__getitem__), \
             mock.patch.object(retention,'verify',side_effect=lambda r,**kw:Path(r['path'])), \
             mock.patch.object(profile,'image_binding',return_value=dict(build=dict(path='build'))), \
             mock.patch.object(retrieval,'closed_operation',side_effect=ReachedClosedOwner) as closed, \
             mock.patch.object(retention.raw,'acquire_command',side_effect=AssertionError('device acquisition')) as device:
            with self.assertRaises(ReachedClosedOwner if accepted else ValueError):consumer('output','task')
            self.assertEqual(closed.call_count,int(accepted));device.assert_not_called()

    def each(self,built,accepted):
        for consumer in (retention.capture,retention.automatic_projection):
            with self.subTest(consumer=consumer.__name__):self.route(consumer,built,accepted)

    def test_single_cpu_selections_reach_existing_closed_owner_check(self):
        for observer in (profile.SINGLECPU_OBSERVER,profile.SINGLECPU_P447_OBSERVER,profile.SCRIPT_OBSERVER):
            self.each(dict(transition_observer=observer,cpu_policy=profile.SINGLECPU_POLICY,
                idle_policy='cpuidle-off'),True)

    def test_existing_selected_transition_variants_remain_accepted(self):
        for observer in (profile.TRANSITION_OBSERVER,profile.RCS_OBSERVER,profile.WATCHDOG_OBSERVER,profile.PHASE_OBSERVER):
            self.each(dict(transition_observer=observer),True)

    def test_legacy_and_unknown_declarations_reject_before_closed_owner_or_reads(self):
        for built in ({},dict(transition_observer={}),dict(transition_observer=dict(profile.SINGLECPU_P447_OBSERVER,history_selection='unknown'))):
            self.each(built,False)

    def test_cpu_declaration_cannot_omit_or_change_its_cpu_idle_selection(self):
        selected=dict(transition_observer=profile.SINGLECPU_P447_OBSERVER,
            cpu_policy=profile.SINGLECPU_POLICY,idle_policy='cpuidle-off')
        for bad in (dict(cpu_policy=None),dict(cpu_policy='maxcpus-8'),dict(idle_policy='retained-default')):
            self.each(dict(selected,**bad),False)


if __name__=='__main__':unittest.main()
