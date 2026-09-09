from pathlib import Path
import base64
import json
import os
import struct
import tempfile
import time
import unittest

import s22plus_fyg8_p375_console_owner as owner


class ConsoleOwnerTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)

    def plan(self, command=b"printf ok", cwd="/s22-root-work", timeout=1234):
        return {"schema": owner.SCHEMA, "commands": [{
            "command_base64": base64.b64encode(command).decode(),
            "cwd": cwd, "timeout_ms": timeout}]}

    def publish(self, value):
        path = self.root / "plan.json"
        path.write_bytes(owner._canonical(value))
        path.chmod(0o600)
        return path

    def test_canonical_plan_is_sealed_without_command_relabelling(self):
        value = self.plan(b"printf binary")
        path = self.publish(value)
        run = self.root / "run"
        run.mkdir()
        loaded, receipt = owner.seal(path, run)
        self.assertEqual(loaded, value)
        self.assertEqual(owner.load(run / owner.SEALED_NAME), value)
        self.assertEqual(receipt["size"], len(owner._canonical(value)))

    def test_changed_or_noncanonical_plan_is_rejected(self):
        run = self.root / "run"
        run.mkdir()
        owner.seal(self.publish(self.plan()), run)
        changed = self.root / "changed.json"
        changed.write_bytes(owner._canonical(self.plan(b"printf changed")))
        with self.assertRaisesRegex(owner.ConsolePlanError, "sealed"):
            owner.seal(changed, run)
        duplicate = self.root / "duplicate.json"
        duplicate.write_text('{"schema":"x","schema":"y","commands":[]}\n')
        with self.assertRaises(owner.ConsolePlanError):
            owner.load(duplicate)

    def test_bounds_and_absolute_cwd_are_enforced(self):
        for value in (
            self.plan(b"", timeout=1), self.plan(cwd="relative"),
            self.plan(timeout=300001),
            {"schema": owner.SCHEMA, "commands": self.plan()["commands"] * 65},
        ):
            with self.subTest(value=value):
                with self.assertRaises((owner.ConsolePlanError, ValueError)):
                    owner.validate(value)

    def test_pre_spawn_terminal_stops_plan_and_preserves_unexecuted_suffix(self):
        value={"schema":owner.SCHEMA,"commands":self.plan(b"first",timeout=1000)["commands"]
            +self.plan(b"second",timeout=1000)["commands"]}
        terminal=[3,16,0,(-24)&0xffffffff,0,0,0]
        class Session:
            raw_count=0
            def __init__(self):self.sent=[]
            def send(self,kind,body):
                sequence=3+len(self.sent);self.sent.append((kind,body))
                self.events=[(owner.wire.EXIT,sequence,struct.pack("<7I",*terminal))]
                return sequence
            def poll(self):
                events=self.events;self.events=[];return events
        session=Session();events=[]
        owner.run(session,events,time.monotonic()+20,value)
        self.assertEqual(len(session.sent),1)
        row={"sequence":3,"timeout_ms":1000,"command":owner._identity(b"first"),
            "cwd":owner._identity(b"/s22-root-work"),"accepted":False,
            "rejected":False,"terminal":terminal}
        execution=owner.execution_projection(value,[row])
        self.assertEqual(execution["results"][0]["outcome"],"setup-failure")
        self.assertEqual(execution["results"][1]["outcome"],"not-executed")
        self.assertFalse(execution["all_planned_terminal"])

    def test_deadline_and_raw_reserves_stop_before_exec(self):
        value=self.plan(timeout=300000)
        class Session:
            def __init__(self,raw_count):self.raw_count=raw_count;self.sent=[]
            def send(self,kind,body):self.sent.append((kind,body));return 3
            def poll(self):return []
        deadline=Session(0)
        owner.run(deadline,[],time.monotonic()+owner.RETURN_RESERVE_SEC+1,value)
        self.assertEqual(deadline.sent,[])
        saturated=Session(owner.wire.SESSION_RX_LIMIT-owner.wire.MAX_COMMAND_RX_BYTES)
        owner.run(saturated,[],time.monotonic()+400,value)
        self.assertEqual(saturated.sent,[])
        execution=owner.execution_projection(value,[])
        self.assertEqual(execution["unexecuted_command_count"],1)
        self.assertFalse(execution["all_planned_terminal"])


if __name__ == "__main__":
    unittest.main()
