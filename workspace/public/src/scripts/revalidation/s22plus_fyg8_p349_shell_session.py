#!/usr/bin/env python3
"""P349 bounded RAM-workspace successor; retained P348 template is immutable."""
from pathlib import Path
import hashlib
TEMPLATE_SOURCE = Path(__file__).with_name('s22plus_fyg8_p348_shell_session.py')
TEMPLATE_IDENTITY = {"size": 68273, "sha256": '8a5ae2f72a7b88a66a94f8acfd529ba0fcede006d16772dbc10135c5161b99c8'}
_template = TEMPLATE_SOURCE.read_bytes()
if {"size": len(_template), "sha256": hashlib.sha256(_template).hexdigest()} != TEMPLATE_IDENTITY:
    raise ValueError("P349 template identity differs")
_template = _template.replace(b"P348", b"P349").replace(b"p348", b"p349")
_template = _template.replace(b"readonly_research_shell", b"ram_workspace_research_shell")
_template = _template.replace(b"MAX_LEASE_SECONDS = 3_600", b"MAX_LEASE_SECONDS = 3_900")
exec(compile(_template, str(TEMPLATE_SOURCE) + "#p349", "exec"), globals())

def _acceptance_summary(live, prepared, rows):
    """Require authenticated witnesses started after each actual time bound.

    The inherited summary has already reopened raw frames, checked each nonce,
    command identity and same candidate boot. Here the durable action intents,
    rather than result or terminal timestamps, establish elapsed duration.
    """
    import s22plus_fyg8_p349_research_shell_observer as observer
    required = tuple(observer.LATER_ACCEPTANCE_COMMANDS)
    lease = ShellLease.open(prepared.run_dir / DIRECTORY, validate_clock=False)
    roles = []
    missing = []
    cursor = 0
    timed = {}
    for row in rows:
        role = row.get("acceptance_role")
        if not isinstance(role, str):
            continue
        roles.append(role)
        if cursor < len(required) and role == required[cursor]:
            cursor += 1
        elif role in required[cursor:]:
            missing.append("ordered-acceptance-sequence")
        if role in observer.LONGEVITY_SECONDS:
            ordinal = row["ordinal"]
            intent, result = lease.actions[ordinal - 1]
            elapsed = intent["issued_elapsed_ns"] - lease.lease["opened_elapsed_ns"]
            threshold = observer.LONGEVITY_SECONDS[role] * 1_000_000_000
            if result is None or elapsed < threshold:
                missing.append(role + "-too-early")
            else:
                timed[role] = elapsed
    missing.extend(required[cursor:])
    return {"proved": not missing and cursor == len(required), "roles": roles,
            "missing": missing, "required": list(required),
            "witness_intent_elapsed_ns": timed, "required_duration_seconds": 3600}
