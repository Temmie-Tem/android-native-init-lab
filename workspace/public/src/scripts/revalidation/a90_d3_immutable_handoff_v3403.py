#!/usr/bin/env python3
"""Host-only model and source-order gate for the V3403 D3 handoff."""

from __future__ import annotations

from dataclasses import dataclass, field


PRE_SWITCH_STEPS = (
    "validate_source",
    "stop_autohud",
    "stop_dpublic",
    "stop_drm_owners",
    "verify_zero_owners",
    "rehash_source",
    "copy_work",
    "verify_work",
    "attach_loop",
    "mount_rw",
    "validate_init",
    "move_mounts",
    "exec_switch_root",
)


@dataclass
class HandoffState:
    source_hash: str
    expected_hash: str
    owners: list[int]
    history: list[str] = field(default_factory=list)
    work_exists: bool = False
    loop_attached: bool = False
    root_mounted: bool = False
    mounts_moved: bool = False
    exec_reached: bool = False
    rc: int = 0

    @property
    def source_unchanged(self) -> bool:
        return self.source_hash == self.expected_hash


def _cleanup_failure(state: HandoffState, rc: int) -> HandoffState:
    state.history.append("cleanup_restore_mounts")
    state.mounts_moved = False
    state.history.append("cleanup_unmount_root")
    state.root_mounted = False
    state.history.append("cleanup_detach_loop")
    state.loop_attached = False
    state.history.append("cleanup_remove_work")
    state.work_exists = False
    state.history.append("verify_source_after_failure")
    state.rc = rc
    return state


def simulate_handoff(
    *,
    source_hash: str = "a" * 64,
    expected_hash: str = "a" * 64,
    owners: tuple[int, ...] = (),
    busy_owner: int | None = None,
    fail_step: str | None = None,
) -> HandoffState:
    """Execute the policy model, injecting at most one pre-switch failure."""

    if fail_step is not None and fail_step not in PRE_SWITCH_STEPS:
        raise ValueError(f"unknown fail step: {fail_step}")

    state = HandoffState(
        source_hash=source_hash,
        expected_hash=expected_hash,
        owners=list(owners),
    )

    def enter(step: str, rc: int = -5) -> bool:
        state.history.append(step)
        if fail_step == step:
            _cleanup_failure(state, rc)
            return False
        return True

    if not enter("validate_source"):
        return state
    if not state.source_unchanged:
        return _cleanup_failure(state, -116)
    if not enter("stop_autohud", -16):
        return state
    if not enter("stop_dpublic", -16):
        return state

    state.history.append("stop_drm_owners")
    if fail_step == "stop_drm_owners":
        return _cleanup_failure(state, -16)
    for owner in tuple(state.owners):
        state.history.append(f"stop_drm_owner:{owner}")
        if owner == busy_owner:
            return _cleanup_failure(state, -16)
        state.owners.remove(owner)

    if not enter("verify_zero_owners", -16):
        return state
    if state.owners:
        return _cleanup_failure(state, -16)
    if not enter("rehash_source", -116):
        return state
    if not state.source_unchanged:
        return _cleanup_failure(state, -116)

    state.history.append("copy_work")
    state.work_exists = True
    if fail_step == "copy_work":
        return _cleanup_failure(state, -5)
    if not enter("verify_work", -116):
        return state

    state.history.append("attach_loop")
    state.loop_attached = True
    if fail_step == "attach_loop":
        return _cleanup_failure(state, -5)

    state.history.append("mount_rw")
    state.root_mounted = True
    if fail_step == "mount_rw":
        return _cleanup_failure(state, -5)
    if not enter("validate_init", -22):
        return state

    state.history.append("move_mounts")
    state.mounts_moved = True
    if fail_step == "move_mounts":
        return _cleanup_failure(state, -5)

    state.history.append("exec_switch_root")
    if fail_step == "exec_switch_root":
        return _cleanup_failure(state, -5)
    state.exec_reached = True
    return state


def validate_source_contract(source: str) -> tuple[str, ...]:
    """Bind the model to the active C implementation's D3 command ordering."""

    issues: list[str] = []
    start_marker = "int a90_server_distro_switch_root_cmd(char **argv, int argc) {"
    end_marker = "#define A90_D4_TAG"
    try:
        start = source.index(start_marker)
        end = source.index(end_marker, start)
    except ValueError:
        return ("missing D3 command boundary",)
    body = source[start:end]

    ordered_tokens = (
        'd3_verify_source_sha(image, expected_sha, "initial")',
        "d3_handoff_stop_display_owners_strict()",
        'd3_verify_source_sha(image, expected_sha, "post-display-cleanup")',
        "d3_copy_work_image(image, expected_sha, &work_owned)",
        "d3_ensure_loop_node(&loop_created)",
        "d3_attach_loop(A90_D3_WORK_IMAGE, &loop_attached)",
        "d3_mount_root()",
        "d3_check_distro_init()",
        "d3_move_core_mounts(",
        "execve(A90_D3_BUSYBOX, switch_argv, newenv);",
        "fail_immutable_source:",
        'd3_verify_source_sha(image, expected_sha, "after-failure")',
    )
    cursor = -1
    for token in ordered_tokens:
        pos = body.find(token, cursor + 1)
        if pos < 0:
            issues.append(f"missing or out-of-order token: {token}")
            continue
        cursor = pos

    if "d_handoff_stop_display_owners(A90_D3_TAG)" in body:
        issues.append("D3 still uses the preserving display-owner cleanup")
    for token in (
        "source_unchanged_after_failure=1",
        "d3_remove_work_image(work_owned)",
        "rootfs=unmounted-after-fail",
        "d3_detach_loop()",
    ):
        if token not in body:
            issues.append(f"missing failure cleanup token: {token}")

    helper_start = source.find("static int d3_copy_work_image(")
    if helper_start < 0 or helper_start > start:
        issues.append("missing D3 work-copy helper")
    else:
        helper = source[helper_start:start]
        for token in (
            'd3_verify_source_sha(A90_D3_WORK_IMAGE, expected_sha, "work-copy")',
            'd3_verify_source_sha(image, expected_sha, "post-copy-source")',
            "reason=preexisting",
        ):
            if token not in helper:
                issues.append(f"missing work-copy contract token: {token}")

    strict_start = source.find("static int d3_handoff_stop_display_owners_strict(void)")
    if strict_start < 0 or strict_start > start:
        issues.append("missing strict D3 display cleanup")
    else:
        strict = source[strict_start:start]
        for token in (
            "preserve_dpublic=0",
            "d_handoff_stop_display_owners_mode(A90_D3_TAG, false)",
        ):
            if token not in strict:
                issues.append(f"missing strict display contract token: {token}")
        if "required_nonpreserved_owner_count=0" not in source[:strict_start]:
            issues.append(
                "missing strict display contract token: "
                "required_nonpreserved_owner_count=0"
            )

    return tuple(issues)
