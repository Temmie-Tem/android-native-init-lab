#!/usr/bin/env python3
"""Single selector for versioned S22+ FYG8 source contracts."""

from __future__ import annotations

from dataclasses import dataclass
from types import ModuleType
from typing import Any

import s22plus_fyg8_p245_source_contract as p245
import s22plus_fyg8_p248_source_contract as p248


class SourceContractSelectionError(ValueError):
    pass


@dataclass(frozen=True)
class SelectedSourceContract:
    module: ModuleType
    contract: Any
    implementation_verdict: str
    source_check_run_id: bytes
    userspace_verdict: str

    @property
    def contract_id(self) -> str:
        return self.contract.contract_id

    @property
    def profile(self) -> str:
        return self.contract.profile

    @property
    def run_id_domain(self) -> bytes:
        return self.contract.run_id_domain

    @property
    def source_keys(self) -> frozenset[str]:
        return self.contract.source_keys

    @property
    def decoder(self):
        return self.module.decoder

    @property
    def materialized_filenames(self) -> dict[str, str]:
        return self.module.MATERIALIZED_FILENAMES

    @property
    def intent_schema(self) -> str:
        return self.module.INTENT_SCHEMA

    @property
    def preimage_schema(self) -> str:
        return self.module.PREIMAGE_SCHEMA

    @property
    def intent_verdict(self) -> str:
        return self.module.INTENT_VERDICT

    @property
    def contract_schema(self) -> str:
        return self.module.CONTRACT_SCHEMA

    @property
    def contract_verdict(self) -> str:
        return self.module.CONTRACT_VERDICT

    def source_bytes(self, root):
        return self.module.source_bytes(root)

    def source_receipts(self, root):
        return self.module.source_receipts(root)

    def implementation_result(self, root):
        return self.module.implementation_result(root)

    def validate_reachable_records(self, run_id: bytes):
        return self.module.validate_reachable_records(run_id)


def _selection_for(module: ModuleType, contract: Any) -> SelectedSourceContract:
    if module is p245:
        return SelectedSourceContract(
            module=module,
            contract=contract,
            implementation_verdict=p245.p244_checker.VERDICT,
            source_check_run_id=p245.p244_checker.RUN_ID,
            userspace_verdict=(
                "PASS_P245_E2_USERSPACE_TWO_BUILD_REPRO_HOST_ONLY"
            ),
        )
    if module is p248:
        return SelectedSourceContract(
            module=module,
            contract=contract,
            implementation_verdict=p248.IMPLEMENTATION_VERDICT,
            source_check_run_id=p248.SOURCE_CHECK_RUN_ID,
            userspace_verdict=p248.USERSPACE_VERDICT,
        )
    raise SourceContractSelectionError("unregistered source-contract module")


REGISTRY = {
    p245.CONTRACT_ID: p245,
    p248.CONTRACT_ID: p248,
}


def contract_ids() -> tuple[str, ...]:
    return tuple(REGISTRY)


def select(
    source_contract_id: str | None,
    profile: str,
) -> SelectedSourceContract:
    module = REGISTRY.get(source_contract_id)
    if module is None:
        raise SourceContractSelectionError(
            f"unsupported source contract/profile: "
            f"{source_contract_id!r}/{profile}"
        )
    try:
        contract = module.require(source_contract_id, profile)
    except (p245.SourceContractError, p248.SourceContractError) as exc:
        raise SourceContractSelectionError(str(exc)) from exc
    return _selection_for(module, contract)
