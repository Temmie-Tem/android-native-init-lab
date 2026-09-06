"""H0: longevity requires witnesses issued after real elapsed-time thresholds."""
from pathlib import Path
import sys
import types
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'workspace/public/src/scripts/revalidation'))
import s22plus_fyg8_p349_shell_session as session
import s22plus_fyg8_p349_research_shell_observer as observer


class LifetimeTests(unittest.TestCase):
    def summary(self, *, offset=0, reverse=False):
        opened=9_000_000_000
        roles=list(observer.LATER_ACCEPTANCE_COMMANDS)
        if reverse:
            roles[-1],roles[-2]=roles[-2],roles[-1]
        rows=[{'ordinal':i,'acceptance_role':role} for i,role in enumerate(roles,1)]
        actions=[]
        for role in roles:
            seconds=observer.LONGEVITY_SECONDS.get(role,1)
            issued=opened+seconds*1_000_000_000+(offset if role in observer.LONGEVITY_SECONDS else 0)
            actions.append(({'issued_elapsed_ns':issued}, {'issued_elapsed_ns':opened+3800*1_000_000_000}))
        lease=types.SimpleNamespace(lease={'opened_elapsed_ns':opened},actions=actions)
        with mock.patch.object(session.ShellLease,'open',return_value=lease):
            return session._acceptance_summary(None,types.SimpleNamespace(run_dir=Path('/unused')),rows)

    def test_exact_thresholds_are_required(self):
        result=self.summary()
        self.assertTrue(result['proved'])
        self.assertEqual(result['witness_intent_elapsed_ns']['witness-60min'],3600*1_000_000_000)

    def test_late_result_does_not_rescue_early_intent(self):
        result=self.summary(offset=-1)
        self.assertFalse(result['proved'])
        self.assertIn('witness-60min-too-early',result['missing'])

    def test_required_witness_order(self):
        self.assertFalse(self.summary(reverse=True)['proved'])

    def test_finite_budget_and_commands(self):
        self.assertEqual(session.MAX_LEASE_SECONDS,3900)
        self.assertLessEqual(len(observer.LATER_ACCEPTANCE_COMMANDS),session.MAX_ACTIONS)
        for spec in observer.LATER_ACCEPTANCE_COMMANDS.values():
            self.assertLessEqual(len(spec['command']),session.MAX_COMMAND_BYTES)

if __name__=='__main__': unittest.main()
