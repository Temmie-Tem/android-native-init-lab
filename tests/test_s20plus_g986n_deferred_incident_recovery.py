"""Exercise the recovery entrypoint in an isolated source view without USB."""
import hashlib
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[1] / "workspace/public/src/scripts/revalidation"
sys.path.insert(0, str(SCRIPTS))
import s20plus_g986n_deferred_incident_recovery as r


class Incident(unittest.TestCase):
    def test_exact_port(self):
        with patch.object(r.owner, "engine", create=True), patch.object(r, "read", return_value={
            "binding": {"endpoint": {"usb": {"product": "stock"}, "topology_sha256": "same"}}
        }):
            r.check_endpoint({"usb": {"product": "stock"}, "topology_sha256": "same"})
            with self.assertRaises(r.owner.Stop):
                r.check_endpoint({"usb": {"product": "stock"}, "topology_sha256": "foreign"})

    def test_changed_authority_denied(self):
        with self.assertRaises(r.owner.Stop):
            r.historical_common(b"other policy")

    def test_archive_checks_endpoint_before_reporting(self):
        with patch.object(r, "incident_arrival", side_effect=ValueError("wrong endpoint")):
            with patch.object(r.owner, "engine", create=True), self.assertRaisesRegex(ValueError, "wrong endpoint"):
                r.archived(r.RUN)

    def isolated(self, fixture, *, archived=False, bad_original=False):
        snapshot = r.trial.EXP / "incident-qualification/before"
        if not snapshot.exists():
            self.skipTest("requires private historical snapshot")
        digest = hashlib.sha256()
        for f in sorted(snapshot.rglob("*")):
            if f.is_file():
                digest.update(str(f.relative_to(snapshot)).encode() + b"\0" + hashlib.sha256(f.read_bytes()).digest())
        self.assertEqual(digest.hexdigest(), "01c706b6ba89d41f6425678b1585dff5128507b54171e3ccd836c99e7e5fdb39")
        source = r.trial.LAST if archived else r.RUN
        admission = source.with_name(source.name.replace("run-", "ticket-"))
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            run, ticket = tmp / "run", tmp / "ticket"
            shutil.copytree(source if archived else snapshot / "run", run)
            shutil.copytree(admission if archived else snapshot / "ticket", ticket)
            shutil.copytree(snapshot / "routine", tmp / "routine")
            command = r.base.view.command(observe=False)
            command = command[:command.index("--chdir")]
            registry = r.owner.REGISTRY_ROOT
            shutil.copytree(snapshot / "registry", tmp / "registry")
            if bad_original:
                (tmp / "bad-ap").write_bytes(b"changed rollback")
                command += ["--ro-bind", str(tmp / "bad-ap"), str(r.trial.parent.ORIGINAL_AP)]
            command += ["--bind", str(tmp / "routine"), str(r.owner.GUARD.parent),
                        "--bind", str(tmp / "registry"), str(registry), "--bind", str(run), str(source),
                        "--bind", str(ticket), str(admission), "--chdir", str(SCRIPTS), "--",
                        str(r.base.view.PYTHON), "-B", "-c", fixture]
            subprocess.run(command, check=True, timeout=120)

    def test_actual_entrypoint_before_identification_and_on_cut(self):
        self.isolated(FIXTURE)

    def test_dispatch_and_interrupted_receipt(self):
        self.isolated(DISPATCH)

    def test_issue_requires_owner_and_bound_original(self):
        self.isolated(ISSUE)
        self.isolated(BAD_ORIGINAL, bad_original=True)

    def test_archived_consumer(self):
        self.isolated(ARCHIVED, archived=True)


FIXTURE = """
import json,os
from unittest.mock import patch
import s20plus_g986n_deferred_incident_recovery as m
assert not os.path.exists('/dev/bus/usb')
m.bind()
m.base.cal.runtime()
m.stage.enter_runtime()
m.history()
m.owner.require_active()
e=m.owner.engine
m.owner.retained_physical_recovery()
e.validate_rollback_closure()
class Cut(Exception): pass
# Only the external endpoint acquisition is replaced in the normal leased
# entrypoint. All history, registry, guard, prepared and AP checks run.
issued=int(m.time.time())
with patch.object(m,'reviewed'), patch.object(m,'grant',side_effect=lambda t:dict(issued=t,expires=t+900)):
    grant=m.grant(issued)
    m.base.put(m.TICKET, f'incident-grant-{issued}',grant)
    token=f'{m.PREFIX}{issued}-{e.digest(grant)}'
    try:
        m.valid_token(token+'0',fresh=True)
    except m.owner.Stop: pass
    else: raise AssertionError('wrong token')
    with patch.object(m.time,'time',return_value=issued+901):
        try: m.valid_token(token,fresh=True)
        except m.owner.Stop: pass
        else: raise AssertionError('expired token')
    # Retain installed capability identity; substitute the endpoint source
    # inside the inherited identification function.
    with patch.object(m,'check_endpoint',side_effect=AssertionError('unexpected live endpoint')):
        try: e.confirm_physical_rollback(m.RUN,token)
        except Exception as first:
            assert (m.RUN/m.INTENT).exists(), (type(first).__name__,str(first))
        else: raise AssertionError('missing USB passed')
    assert not (m.RUN/m.ARRIVAL).exists() and not (m.RUN/'rollback-intent.json').exists()
    try: e.confirm_physical_rollback(m.RUN,token)
    except Exception as second: assert 'consumed' in str(second),str(second)
    else: raise AssertionError('repeated inventory')
"""

ISSUE = """
from unittest.mock import patch
import s20plus_g986n_deferred_incident_recovery as m
assert not m.os.path.exists('/dev/bus/usb')
with patch.object(m,'reviewed'),patch.object(m,'grant',side_effect=lambda t:dict(issued=t,expires=t+900)):
    assert m.main(['--inside','--issue'])==0
assert len(list(m.TICKET.glob('incident-grant-*.json')))==1
(m.RUN/'rollback.stdout').touch()
try: m.issue()
except m.owner.Stop: pass
else: raise AssertionError('possible prior dispatch ignored')
m.owner.GUARD.unlink()
try: m.issue()
except FileNotFoundError: pass
else: raise AssertionError('missing guard accepted')
"""

BAD_ORIGINAL = """
import s20plus_g986n_deferred_incident_recovery as m
try: m.main(['--inside','--check'])
except Exception as ex: assert 'rollback' in str(ex).lower() or 'size' in str(ex).lower(), str(ex)
else: raise AssertionError('changed original AP accepted')
"""

DISPATCH = """
from unittest.mock import patch
import s20plus_g986n_deferred_incident_recovery as m
assert not m.os.path.exists('/dev/bus/usb')
m.bind()
m.base.cal.runtime()
inherited=m.trial.parent._configure_runtime
endpoint=m.read(m.RUN/'prepared.json')['binding']['endpoint']
calls=[]
stat=list(endpoint['endpoint_identity'])
stat[3]+=1
class Cut(Exception): pass
def at_hardware(run, prepared, current):
    e=m.owner.engine
    assert m.stage.fresh_return_run==run and current==endpoint
    e.durable_json(run/'rollback-intent.json', {'endpoint':dict(current,endpoint_identity=stat.copy())})
    m.dispatch_check(run)
    stat[3]+=1
    try: m.dispatch_check(run)
    except m.owner.Stop: pass
    else: raise AssertionError('endpoint replaced after transfer preflight')
    stat[3]-=1
    calls.append('dispatch')
    raise Cut
def configure(rt):
    inherited(rt)
    rt.engine.identify_download=lambda: endpoint
    rt.engine.endpoint_stat=lambda path: tuple(stat)
    rt.engine.rollback_from_arrival=at_hardware
m.trial.parent._configure_runtime=configure
m.stage.enter_runtime()
e=m.owner.engine
with patch.object(m,'reviewed'),patch.object(m,'grant',side_effect=lambda t:dict(issued=t,expires=t+900)):
    issued=int(m.time.time())
    grant=m.grant(issued)
    m.base.put(m.TICKET,f'incident-grant-{issued}',grant)
    token=f'{m.PREFIX}{issued}-{e.digest(grant)}'
    try: e.confirm_physical_rollback(m.RUN,token)
    except Cut: pass
    else: raise AssertionError('dispatch did not reach simulated cut')
    assert calls==['dispatch'] and m.stage.fresh_return_run is None
    try: e.confirm_physical_rollback(m.RUN,token)
    except Exception: pass
    else: raise AssertionError('incomplete receipt passed')
    assert calls==['dispatch'] and not (m.RUN/'final-health.json').exists()
"""

# Exercise the incident terminal consumer on a full historical rooted return.
# Only its run identity and incident metadata use the historical fixture.
ARCHIVED = """
from unittest.mock import patch
import s20plus_g986n_deferred_incident_recovery as m
p=m.trial.parent
m.RUN=m.trial.LAST
m.TICKET=m.RUN.with_name(m.RUN.name.replace('run-','ticket-'))
m.BINDING=m.read(m.RUN/'prepared.json')['binding_sha256']
p.bind()
m.base.cal.runtime()
m.stage.enter_runtime()
e=m.owner.engine
old=m.read(m.RUN/'physical-rollback-arrival.json')
arm=m.read(m.RUN/'physical-rollback-intent.json')
(m.RUN/'physical-rollback-arrival.json').unlink()
def put(name,value):
    m.base.cal.engine.durable_json(m.RUN/name,value)
put('physical-observation-miss.json',dict(schema='s20plus_g986n_b0_physical_observation_miss_v1',
    version=p.PROFILE,binding_sha256=m.BINDING,baseline_sha256=arm['baseline_sha256'],
    expires_unix=arm['expires_unix'],reason='bounded-wait-expired',endpoint_count=0,
    listing_sha256=None,no_replay=True,at=arm['at']))
issued=old['observed_unix']
grant=dict(issued=issued,expires=issued+900)
token=f'{m.PREFIX}{issued}-{e.digest(grant)}'
m.base.put(m.TICKET,f'incident-grant-{issued}',grant)
intent=dict(binding=m.BINDING,approval=token,original=m.ORIGINAL)
put(m.INTENT,intent)
put(m.ARRIVAL,dict(intent=e.digest(intent),observed=issued,endpoint=old['endpoint']))
original=m.read(m.RUN/'terminal.json')
historical=m.owner.strict_private(p.RUN_ROOT/'activation.json')['identity']
with patch.object(m,'history'),patch.object(m.base,'review',return_value=historical),patch.object(m,'grant',return_value=grant):
    assert m.archived(m.RUN)==original
    assert m.archived(m.RUN)==original
    # Losing the capture preserves its intent. The reader must report the cut;
    # the stored positive terminal can no longer be rederived from the raw data.
    raw=m.stage.paths('return')[1]
    receipt=m.RUN/(raw+'.capture.json')
    backup=receipt.read_bytes()
    receipt.unlink()
    prep=m.read(m.RUN/'prepared.json')
    final=m.read(m.RUN/'final-health.json')
    assert m.stage.first_return(m.RUN,prep,final)['state']=='capture_cut'
    try: m.archived(m.RUN)
    except Exception: pass
    else: raise AssertionError('archived positive without raw receipt')
    receipt.write_bytes(backup)
    put('rollback-download-intent.json',{})
    try: m.archived(m.RUN)
    except m.owner.Stop: pass
    else: raise AssertionError('mixed recovery branches passed')
"""

if __name__ == "__main__":
    unittest.main()
