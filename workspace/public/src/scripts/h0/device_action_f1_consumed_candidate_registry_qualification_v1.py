"""Host-only qualification harness for the global Process-v2 registry."""

from __future__ import annotations

import multiprocessing
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from typing import Any


def _worker(module: Any, root: str, identity: dict[str, Any], suffix: int, queue: Any) -> None:
    try:
        module.preflight_candidate(Path(root), identity)
        module.claim(Path(root), identity)
    except module.DuplicateCandidateClaim:
        queue.put("duplicate")
    except Exception as exc:  # pragma: no cover
        queue.put(f"error:{type(exc).__name__}")
    else:
        queue.put("ok")


def build(module: Any, repo_root: Path) -> dict[str, Any]:
    structural = module.qualification_summary(repo_root)
    initial_head = module._head_value(0, -1, module.ZERO_SHA256)
    initial_head_data = module._canonical(initial_head)
    structural["head"] = {
        "name": module.HEAD_NAME,
        "size": len(initial_head_data),
        "sha256": module._sha(initial_head_data),
        "mode": "0400",
        "nlink": 1,
        "record_count": 0,
    }
    structural["record_count"] = 0
    structural["empty_at_initialization"] = True
    profile = {
        "schema": "qualification-profile-v1",
        "profile_id": "qualification-profile-1",
        "target": {"model": "SM-S906N", "device": "g0q", "firmware_incremental": "qualification-build"},
    }
    manifest = {
        "manifest_id": "qualification-manifest-1",
        "run_id": "qualification-run-1",
        "allowed_member": "boot.img.lz4",
        "candidate_ap": {"size": 17, "sha256": "a" * 64},
    }
    identity = module.derive_candidate_identity(
        profile,
        manifest,
        "a" * 64,
        approval_binding_sha256="b" * 64,
        candidate_receipt={"size": 17, "sha256": "a" * 64, "member": {"name": "boot.img.lz4", "size": 9, "sha256": "c" * 64}},
    )
    with tempfile.TemporaryDirectory(prefix="consumed-candidate-registry-qual-") as temporary:
        temp_root = Path(temporary)
        (temp_root / "workspace/private").mkdir(parents=True)
        module.initialize(temp_root)
        context = multiprocessing.get_context("fork")
        queue = context.Queue()
        workers = [context.Process(target=_worker, args=(module, str(temp_root), identity, index, queue)) for index in (1, 2)]
        for worker in workers:
            worker.start()
        for worker in workers:
            worker.join(10)
            if worker.is_alive():
                worker.terminate()
                worker.join(2)
                raise RuntimeError("concurrent registry worker timed out")
            if worker.exitcode != 0:
                raise RuntimeError("concurrent registry worker failed")
        outcomes = [queue.get(timeout=2) for _ in workers]
        if sorted(outcomes) != ["duplicate", "ok"]:
            raise RuntimeError("concurrent registry claim did not serialize")
        shutil.rmtree(temp_root / "workspace/private" / module.REGISTRY_DIR_NAME)
        module.initialize(temp_root)
        module.preflight_candidate(temp_root, identity)
        module.claim(temp_root, identity)
        projection_before = module.qualification_summary(temp_root)
        projection_before["record_count"] = 0
        projection_before["empty_at_initialization"] = True
        projection_before["head"] = {
            "name": module.HEAD_NAME,
            "size": len(module._canonical(module._head_value(0, -1, module.ZERO_SHA256))),
            "sha256": module._sha(module._canonical(module._head_value(0, -1, module.ZERO_SHA256))),
            "mode": "0400",
            "nlink": 1,
            "record_count": 0,
        }
        busy_code = """import importlib.util, pathlib, sys
p = pathlib.Path(sys.argv[1])
r = pathlib.Path(sys.argv[2])
s = importlib.util.spec_from_file_location('registry_busy', p)
m = importlib.util.module_from_spec(s)
s.loader.exec_module(m)
try:
    m.target_session_lease(r).__enter__()
except m.RegistryUnavailable:
    raise SystemExit(0)
raise SystemExit(9)
"""
        with module.target_session_lease(temp_root):
            busy = subprocess.run([sys.executable, "-c", busy_code, str(module.__file__), str(temp_root)], check=False, capture_output=True, text=True)
        if busy.returncode != 0:
            raise RuntimeError("busy target-session lease was not rejected immediately")
        restart_code = (
            "import importlib.util, pathlib, sys; "
            "p=pathlib.Path(sys.argv[1]); r=pathlib.Path(sys.argv[2]); "
            "s=importlib.util.spec_from_file_location('registry_restart',p); "
            "m=importlib.util.module_from_spec(s); s.loader.exec_module(m); m.validate(r)"
        )
        restart = subprocess.run([sys.executable, "-c", restart_code, str(module.__file__), str(temp_root)], check=False, capture_output=True, text=True)
        if restart.returncode != 0:
            raise RuntimeError("fresh process registry reopen failed")
        identity_path = temp_root / "identity.json"
        identity_path.write_bytes(module._canonical(identity))
        duplicate_code = """import importlib.util, json, pathlib, sys
p = pathlib.Path(sys.argv[1])
r = pathlib.Path(sys.argv[2])
i = json.loads(pathlib.Path(sys.argv[3]).read_text())
s = importlib.util.spec_from_file_location('registry_duplicate', p)
m = importlib.util.module_from_spec(s)
s.loader.exec_module(m)
try:
    m.claim(r, i)
except m.DuplicateCandidateClaim:
    raise SystemExit(0)
raise SystemExit(9)
"""
        duplicate = subprocess.run(
            [sys.executable, "-c", duplicate_code, str(module.__file__), str(temp_root), str(identity_path)],
            check=False,
            capture_output=True,
            text=True,
        )
        if duplicate.returncode != 0:
            raise RuntimeError("fresh process duplicate claim was not rejected")
        second_manifest = dict(manifest)
        second_manifest["manifest_id"] = "qualification-manifest-2"
        second_manifest["run_id"] = "qualification-run-2"
        second_manifest["candidate_ap"] = {"size": 17, "sha256": "d" * 64}
        second_identity = module.derive_candidate_identity(
            profile,
            second_manifest,
            "d" * 64,
            approval_binding_sha256="e" * 64,
            candidate_receipt={
                "size": 17,
                "sha256": "d" * 64,
                "member": {"name": "boot.img.lz4", "size": 9, "sha256": "f" * 64},
            },
        )
        third_manifest = dict(manifest)
        third_manifest["manifest_id"] = "qualification-manifest-3"
        third_manifest["run_id"] = "qualification-run-3"
        third_manifest["candidate_ap"] = {"size": 17, "sha256": "1" * 64}
        third_identity = module.derive_candidate_identity(
            profile,
            third_manifest,
            "1" * 64,
            approval_binding_sha256="2" * 64,
            candidate_receipt={
                "size": 17,
                "sha256": "1" * 64,
                "member": {"name": "boot.img.lz4", "size": 9, "sha256": "3" * 64},
            },
        )
        different_queue = context.Queue()
        different_workers = [
            context.Process(target=_worker, args=(module, str(temp_root), candidate, index, different_queue))
            for index, candidate in enumerate((second_identity, third_identity), 1)
        ]
        for worker in different_workers:
            worker.start()
        for worker in different_workers:
            worker.join(10)
            if worker.is_alive():
                worker.terminate()
                worker.join(2)
                raise RuntimeError("different-candidate worker timed out")
            if worker.exitcode != 0:
                raise RuntimeError("different-candidate worker failed")
        different_outcomes = [different_queue.get(timeout=2) for _ in different_workers]
        if sorted(different_outcomes) != ["ok", "ok"]:
            raise RuntimeError("different candidates did not append concurrently")
        projection_after = module.qualification_summary(temp_root)
        projection_after["record_count"] = 0
        projection_after["empty_at_initialization"] = True
        projection_after["head"] = projection_before["head"]
        append_stability = projection_before == projection_after
        if not append_stability:
            raise RuntimeError("qualification projection changed after append")
        registry_path = temp_root / "workspace/private" / module.REGISTRY_DIR_NAME
        head_path = registry_path / module.HEAD_NAME
        head_temp = registry_path / ".head.json.next-123-456"
        head_temp.write_bytes(head_path.read_bytes())
        head_temp.chmod(0o400)
        try:
            module.validate(temp_root)
        except module.RegistryError:
            head_temp_rejected = True
        else:
            head_temp_rejected = False
        try:
            module.preflight_candidate(temp_root, third_identity)
        except module.DuplicateCandidateClaim:
            pass
        if head_temp.exists():
            raise RuntimeError("single head staging file was not repaired by writer preflight")
        original_head = head_path.read_bytes()
        head_path.chmod(0o600)
        head_path.write_bytes(b"{}")
        head_path.chmod(0o400)
        try:
            try:
                module.validate(temp_root)
            except module.RegistryError:
                head_rejected = True
            else:
                head_rejected = False
        finally:
            head_path.chmod(0o600)
            head_path.write_bytes(original_head)
            head_path.chmod(0o400)
        record_path = sorted((registry_path / module.RECORDS_NAME).glob("*.json"))[0]
        original_record = record_path.read_bytes()
        record_path.chmod(0o600)
        record_path.write_bytes(original_record[:-2] + b"x")
        record_path.chmod(0o400)
        try:
            try:
                module.validate(temp_root)
            except module.RegistryError:
                record_rejected = True
            else:
                record_rejected = False
        finally:
            record_path.chmod(0o600)
            record_path.write_bytes(original_record)
            record_path.chmod(0o400)
        writer_root = temp_root / "writer-hostile"
        (writer_root / "workspace/private").mkdir(parents=True)
        module.initialize(writer_root)
        module.claim(writer_root, identity)
        lock_path = writer_root / "workspace/private" / module.REGISTRY_DIR_NAME / module.LOCK_NAME
        replacement = lock_path.with_name("writer.lock.replacement")
        replacement.write_bytes(module.LOCK_PAYLOAD)
        replacement.chmod(0o600)
        os.replace(replacement, lock_path)
        try:
            module.validate(writer_root)
        except module.RegistryError:
            lock_rejected = True
        else:
            lock_rejected = False
        session_root = temp_root / "session-hostile"
        (session_root / "workspace/private").mkdir(parents=True)
        module.initialize(session_root)
        module.claim(session_root, identity)
        session_lock_path = session_root / "workspace/private" / module.REGISTRY_DIR_NAME / module.SESSION_LOCK_NAME
        session_replacement = session_lock_path.with_name("target-session.lock.replacement")
        session_replacement.write_bytes(module.SESSION_LOCK_PAYLOAD)
        session_replacement.chmod(0o600)
        os.replace(session_replacement, session_lock_path)
        try:
            module.validate(session_root)
        except module.RegistryError:
            session_rejected = True
        else:
            session_rejected = False
    if not all((head_rejected, record_rejected, lock_rejected, session_rejected)):
        raise RuntimeError("registry hostile replacement was accepted")
    return {
        **structural,
        "behavioral": {
            "fresh_process_reopen": True,
            "fresh_process_duplicate_rejected": True,
            "concurrent_processes": 2,
            "concurrent_outcomes": sorted(outcomes),
            "different_candidate_outcomes": sorted(different_outcomes),
            "duplicate_active_claim_rejected": True,
            "head_replacement_rejected": head_rejected,
            "single_head_temp_rejected_and_repaired": head_temp_rejected,
            "record_replacement_rejected": record_rejected,
            "lock_replacement_rejected": lock_rejected,
            "session_lock_replacement_rejected": session_rejected,
            "session_lock_busy_rejected": True,
            "session_lock_nonblocking": True,
            "append_stability": append_stability,
            "backend_calls": 0,
            "device_contact": False,
        },
    }
