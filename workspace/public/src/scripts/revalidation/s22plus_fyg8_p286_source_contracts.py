#!/usr/bin/env python3
"""P2.86 selector layered over the historical FYG8 contract registry."""

from __future__ import annotations

import s22plus_fyg8_p286_source_contract as p286
import s22plus_fyg8_p288_source_contract as p288
import s22plus_fyg8_source_contracts as historical


SourceContractSelectionError = historical.SourceContractSelectionError
SelectedSourceContract = historical.SelectedSourceContract

REGISTRY = {
    **historical.REGISTRY,
    p286.CONTRACT_ID: p286,
    p288.CONTRACT_ID: p288,
}


def contract_ids() -> tuple[str, ...]:
    return tuple(REGISTRY)


def __getattr__(name: str):
    return getattr(historical, name)


def _p286_selection(contract) -> SelectedSourceContract:  # noqa: ANN001
    return SelectedSourceContract(
        module=p286,
        contract=contract,
        implementation_verdict=p286.IMPLEMENTATION_VERDICT,
        source_check_run_id=p286.SOURCE_CHECK_RUN_ID,
        userspace_verdict=p286.USERSPACE_VERDICT,
    )


def _p288_selection(contract) -> SelectedSourceContract:  # noqa: ANN001
    return SelectedSourceContract(
        module=p288,
        contract=contract,
        implementation_verdict=p288.IMPLEMENTATION_VERDICT,
        source_check_run_id=p288.SOURCE_CHECK_RUN_ID,
        userspace_verdict=p288.USERSPACE_VERDICT,
    )


def select(
    source_contract_id: str | None,
    profile: str,
) -> SelectedSourceContract:
    if source_contract_id == p288.CONTRACT_ID:
        try:
            contract = p288.require(source_contract_id, profile)
        except p288.SourceContractError as exc:
            raise SourceContractSelectionError(str(exc)) from exc
        return _p288_selection(contract)
    if source_contract_id != p286.CONTRACT_ID:
        return historical.select(source_contract_id, profile)
    try:
        contract = p286.require(source_contract_id, profile)
    except p286.SourceContractError as exc:
        raise SourceContractSelectionError(str(exc)) from exc
    return _p286_selection(contract)
