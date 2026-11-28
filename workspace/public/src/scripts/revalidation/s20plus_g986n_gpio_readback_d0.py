#!/usr/bin/env python3
"""Read only the qualified GP2 milestones on the GPIO trial's restored Android boot."""
import json
import os
from pathlib import Path
import types

import s20plus_g986n_presence_readback_d0 as session

SCRIPT = Path(__file__).resolve()
prior, stock = session.prior, session.stock
ROOT, SOURCE = prior.ROOT, prior.SOURCE
PARENT = prior.RUNS / "s20plus-g986n-gpio-readback-d0"
PROFILE = "s20plus-g986n-tlmm-gpio-f1"
RUN = prior.RUNS / PROFILE / "run-1795876893319878903"
EXP = prior.PRIVATE / "analysis/s20plus-y2q-tlmm-gpio-h0-20261128"
PAIR = EXP / "packaged/pair.json"
READER = SOURCE / "gpio_return_reader.py"
FILTER = SOURCE / "gpio-return-filter.awk"
TEST = ROOT / "tests/test_s20plus_gpio_readback_d0.py"
SECTION = "## S20+ same restored boot GPIO marker readback D0\n"
F1_SECTION = "## S20+ post-wake GPIO registration attended trial\n"
RECORDS = {
    RUN / "terminal.json": "a5756875b5e74006493aa1337169257c4021255e7f3614d98163d6838045aec1",
    RUN / "final-health.json": "f48ca96698b5cb7089746aa7bc58b776ac384408fd2b0e680c4a63cb6f107aad",
    RUN / "mainline-baseline-intent.json": "9e988cbac59b1e04a9cb911420077bdd8cf4e4f984553d097e56aa244a3562be",
    RUN / "mainline-baseline-evidence.json": "1e2659758863bd42183eaf4a6357de4107c1dfee60f7e4d8ed24256e83f79749",
    RUN / "mainline-return-evidence.json": "6dac372d2c3bd1a234bf81bb2173546bc880a6da706b0283d68efafc926e72b1",
    RUN / "candidate-result.json": "1f5cf49aedfce41fa8ad0603b5183fbef9c1a1ea0ad3dedf087e2da3d28a93c2",
    RUN / "rollback-result.json": "39fa54012051eb821f7561111b4127f8eb41945eedc57c3d8498a7cd8a9d8760",
    PAIR: "54d3a345aeb7dd51b6f41493b340bb01e9c9bb4ca6ce47ad0a4d56a4b2aed165",
}
HELPERS = {
    session.SCRIPT: "67985ed22446be1ed97effeef6e29659c4e16af7e8ab8fb397dff5ead7743a4d",
    prior.SCRIPT: "99479aaf55d9c841d226eeaaecb5d08febadb88cafdaea048d35818612396fc3",
    prior.STOCK: "cf0c1b7e38c01fae1c1ae57cc4389c0ea3709ad5193135a0046cda8f14a79cd0",
    READER: "52b3807da86a64b578a545e3b993396318d281ec56e99a918e40354ff12b93ad",
    FILTER: "ccab3129c9e90f407205e140f7c11e05abca13f696727975d5e05e81229923c0",
    SOURCE / "tlmm_return_reader.py": "62c24c00c5e09bb2baecfb3ad58267b9c5f1feba0a9e09dc970c751229c5296d",
    SOURCE / "tlmm_gpio_h0.py": "9a4a8a2759f17c1150b66cd13ef95156cfc54f0b8e23522eb5261be195ef18a9",
    SOURCE / "tlmm_flush_h0.py": "a8a9332b64b7857288a5eb6aa0f869b5de2e0c5f9f0809306ff0ac2fe43e5236",
    SOURCE / "tlmm-return-filter.awk": "9c7c65e8aef2604e802f82927535e96a5291df7b5e0991761251869515628410",
    SOURCE / "mainline-handoff/return_stage.py": "1fc37c9a3bcf1b1cc6410628a766ad8b5b0f15db9104bc4f3327a6a07ef2f8e5",
    SOURCE / "mainline-handoff/return-stage.awk": "58c44217e5d523d74c2aa2ec15b1ff3673ec7892daf2c4e14d19e4f7affcdfc8",
}


def inputs():
    for path, digest in HELPERS.items():
        prior.checked(path, digest)
    records = {p.stem: json.loads(prior.checked(p, pin)) for p, pin in RECORDS.items()}
    final, term, baseline, gap = (records[k] for k in ("final-health", "terminal", "mainline-baseline-evidence",
                                                       "mainline-return-evidence"))
    health = final["health"]
    key = term["binding_sha256"]
    require = prior.require
    require(final["version"] == term["version"] == PROFILE
            and final["binding_sha256"] == key and final["resident_boot_healthy"] is True
            and final["rollback_outcome_proved"] is final["rollback_transfer_completed"] is True
            and term["verdict"] == "NO_PROOF_GPIO_ORIGINAL_RETURNED" and term["experiment_pass"] is False
            and term["candidate_attempts"] == term["rollback_attempts"] == 1
            and term["candidate_replay_permitted"] is term["rollback_replay_permitted"] is False
            and gap == dict(phase="return", state="observation_gap", binding_sha256=key,
                            final_health_sha256=RECORDS[RUN / "final-health.json"])
            and not os.path.lexists(RUN / "mainline-return-intent.json"), "original closure or capture differs")
    pair = records["pair"]
    for role in ("candidate", "rollback"):
        transfer = records[role + "-result"]
        require(transfer["classification"] == "odin_transfer_completed" and transfer["version"] == PROFILE
                and transfer["binding_sha256"] == key and transfer["kind"] == role
                and transfer["host_process_quiescence_proved"] is True and transfer["replay_permitted"] is False
                and transfer["receipt"]["ap"] == pair["archives"][role]["ap"], "closed transfer differs")
    intent = records["mainline-baseline-intent"]
    before = intent["health"]
    require(before["target"] == health["target"] and all(before[k] == health[k] for k in prior.IDENTITY[:2])
            and before["boot_id_sha256"] == baseline["boot_id_sha256"] != health["boot_id_sha256"]
            and intent["pair_sha256"] == RECORDS[PAIR] and baseline["phase"] == intent["phase"] == "baseline"
            and baseline["intent_sha256"] == RECORDS[RUN / "mainline-baseline-intent.json"]
            and baseline["state"] == "no_record" and baseline["windows"] == baseline["slots"] == 0
            and baseline["size"] == 2097136, "source boot or baseline differs")
    nonce = pair["nonce"]
    require(intent["script_sha256"] == prior.sha(reader.shell(nonce, before["boot_id_sha256"]).encode()),
            "qualified GP2 baseline shell differs")
    shell = reader.shell(nonce, health["boot_id_sha256"])
    identity = stock.subject(shell)
    target = prior.files.read_file(stock.io.TARGET_CONTRACT).decode()
    sections = {}
    for heading in (SECTION, F1_SECTION):
        require(target.count(heading) == 1, "readback authority missing")
        sections[heading.strip()] = prior.sha((heading + target.split(heading)[1].split("\n## ", 1)[0]).encode())
    identity.update(schema="s20plus_gpio_current_restored_boot_d0_v1", owner=prior.sha(prior.files.read_file(SCRIPT)),
                    selected=sections, closure={str(p.relative_to(ROOT)): v for p,v in RECORDS.items()},
                    readback_helpers={str(p.relative_to(ROOT)): v for p,v in HELPERS.items()},
                    test=prior.sha(prior.files.read_file(TEST)))
    return health, shell, identity


reader = types.ModuleType("_s20_gpio_current_reader")
reader.__file__ = str(READER)
exec(compile(prior.checked(READER, HELPERS[READER]), str(READER), "exec"), reader.__dict__)


def main():
    # Reuse the already reviewed reservation, two health brackets, fixed digest-only
    # capture and owner exclusions. Only the bound inputs and result schema differ.
    session.inputs, session.classify = inputs, reader.parse
    session.PARENT, session.LIMIT = PARENT, reader.MAX_STDOUT
    session.main()


if __name__ == "__main__":
    main()
