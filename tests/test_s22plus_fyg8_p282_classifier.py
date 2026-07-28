from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "workspace/public/src/scripts/revalidation"
CLASSIFIER = (
    ROOT
    / "workspace/public/src/native-init/"
    "s22plus_fyg8_p282_classifier.inc.c"
)
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import s22plus_fyg8_p282_contract_spec as spec  # noqa: E402


DEFAULTS = {
    "p282_classify_stop": {
        "none_readback": 1,
        "trace_authoritative": 1,
        "worker_entered": 1,
        "worker_returned": 1,
        "worker_rc": 0,
    },
    "p282_classify_suspend": {
        "trace_authoritative": 1,
        "suspend_entered": 1,
        "suspend_returned": 1,
        "suspend_rc": 0,
        "status_suspended": 1,
        "power_off_entered": 1,
        "power_off_returned": 1,
        "power_off_rc": 0,
    },
    "p282_classify_restart": {
        "peripheral_readback": 1,
        "trace_authoritative": 1,
        "worker_entered": 1,
        "worker_returned": 1,
        "worker_rc": 0,
        "resume_entered": 1,
        "resume_returned": 1,
        "resume_rc": 0,
        "init_entered": 1,
        "init_returned": 1,
        "init_rc": 0,
        "power_on_entered": 1,
        "power_on_returned": 1,
        "power_on_rc": 0,
        "notify_connect": 1,
        "status_active": 1,
        "mode_peripheral": 1,
        "exact_udc": 1,
        "off_on_zero_pair": 1,
    },
    "p282_classify_bind": {
        "cleanup_verified": 1,
        "source_consistent": 1,
        "trace_authoritative": 1,
        "pullup_returned_zero": 1,
        "run_stop_seen": 1,
        "run_stop_rc": 0,
        "repair_class": 0,
        "bind_branch": 0,
    },
    "p282_classify_final_pair": {
        "first_state": 0,
        "first_speed": 0,
        "second_state": 0,
        "second_speed": 0,
        "repair_class": 0,
        "bind_branch": 0,
    },
}

STRUCTS = {
    "p282_classify_stop": "p282_stop_observation",
    "p282_classify_suspend": "p282_suspend_observation",
    "p282_classify_restart": "p282_restart_observation",
    "p282_classify_bind": "p282_bind_observation",
    "p282_classify_final_pair": "p282_final_pair_observation",
}


def _initializer(values: dict[str, int]) -> str:
    return ", ".join(f".{name} = {value}" for name, value in values.items())


def _fixture_block(index: int, fixture: spec.ClassifierFixture) -> str:
    if fixture.function == "p282_classify_cycle_control":
        condition = dict(fixture.fields)["condition"]
        invocation = (
            f"{fixture.function}(0x{fixture.stage:02x}U, "
            f"{condition}U, &result)"
        )
        declaration = ""
    else:
        values = dict(DEFAULTS[fixture.function])
        values.update(dict(fixture.fields))
        struct_name = STRUCTS[fixture.function]
        declaration = (
            f"struct {struct_name} observation = "
            f"{{ {_initializer(values)} }};"
        )
        invocation = f"{fixture.function}(&observation, &result)"
    return f"""
    {{
        struct p282_classification result = {{0}};
        {declaration}
        int rc = {invocation};
        if (rc != 1 || result.detail != 0x{fixture.detail:03x}U ||
            result.stage != 0x{fixture.stage:02x}U ||
            result.outcome != {fixture.outcome}U)
            return {index + 1};
    }}
"""


def harness_source() -> str:
    blocks = "".join(
        _fixture_block(index, fixture)
        for index, fixture in enumerate(spec.CLASSIFIER_FIXTURES)
    )
    return (
        spec.render_classifier_contract_c()
        + f'\n#include "{CLASSIFIER}"\n'
        + """
int main(void)
{
"""
        + blocks
        + """
    {
        struct p282_classification result = {0};
        int rc = p282_classify_cycle_control(
            P282_STAGE_SUSPENDED,
            P282_CONTROL_HELPER_SOURCE_CONTRADICTION,
            &result);
        if (rc != -1)
            return 100;
    }
    {
        struct p282_stop_observation observation = {
            .none_readback = 1,
            .trace_authoritative = 0,
            .worker_entered = 0,
        };
        struct p282_classification result = {0};
        if (p282_classify_stop(&observation, &result) != 0)
            return 101;
    }
    {
        struct p282_final_pair_observation observation = {
            .first_state = P282_STATE_COUNT,
        };
        struct p282_classification result = {0};
        if (p282_classify_final_pair(&observation, &result) != -1)
            return 102;
    }
    {
        unsigned int repair;
        unsigned int bind;
        unsigned int state;
        unsigned int speed;
        unsigned int detail;
        unsigned int count = 0;
        for (repair = 0; repair < P282_REPAIR_COUNT; ++repair)
            for (bind = 0; bind < P282_BIND_COUNT; ++bind)
                for (state = 0; state < P282_STATE_COUNT; ++state)
                    for (speed = 0; speed < P282_SPEED_COUNT; ++speed) {
                        if (p282_encode_tuple(
                                repair, bind, state, speed, &detail) != 0)
                            return 103;
                        if (detail != P282_TUPLE_BASE + count)
                            return 104;
                        ++count;
                    }
        if (count != 567U || detail != P282_TUPLE_MAX)
            return 105;
    }
    return 0;
}
"""
    )


class S22PlusFyg8P282ClassifierTest(unittest.TestCase):
    def test_shared_production_classifier_emits_46_of_46(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "fixture.c"
            binary = root / "fixture"
            source.write_text(harness_source(), encoding="ascii")
            compile_result = subprocess.run(
                [
                    "cc",
                    "-std=c11",
                    "-Wall",
                    "-Wextra",
                    "-Werror",
                    "-O2",
                    str(source),
                    "-o",
                    str(binary),
                ],
                check=False,
                capture_output=True,
                text=True,
                timeout=30,
            )
            self.assertEqual(compile_result.returncode, 0, compile_result.stderr)
            run = subprocess.run(
                [str(binary)],
                check=False,
                capture_output=True,
                text=True,
                timeout=10,
            )
            self.assertEqual(run.returncode, 0, run.stderr)

    def test_classifier_has_no_fixture_or_test_mode(self) -> None:
        source = CLASSIFIER.read_text(encoding="ascii")
        for forbidden in (
            "test_mode",
            "fixture_mode",
            "inject",
            "#ifdef TEST",
            "CLASSIFIER_FIXTURES",
        ):
            self.assertNotIn(forbidden, source)
        self.assertIn("const struct p282_stop_observation *", source)
        self.assertIn("const struct p282_restart_observation *", source)


if __name__ == "__main__":
    unittest.main()
