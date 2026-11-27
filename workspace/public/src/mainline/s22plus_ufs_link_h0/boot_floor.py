"""Witness-floor boot-time floors: the fixed V13 module and RPMh transport with 60 s instead of 300 s.

Two fixed artifacts refuse to run below 300 s of boot time: the V13 module's
start() and the transport kernel's g0q_rpmh_begin(). The route-scope witness
floor admits the module permit from 60 s of guest BOOTTIME, so its kernel and
module are rebuilds whose only source differences are those two comparisons.
The 540-second ceilings and 15-second budgets are unchanged, and the adopted
g0q_stage.c and transport/authority.inc.c stay byte for byte.
"""
import hashlib
from pathlib import Path

HERE = Path(__file__).resolve().parent
FLOOR_MS = 60000
FIELD = "boot_floor_ms"
STAGE_FIELD = "stage_source_sha256"
AUTHORITY_FIELD = "authority_source_sha256"

STAGE = HERE/"g0q_stage.c"
STAGE_SHA256 = "c03d59d02ccf2270662b82148ca39bb2521b9a627b6abdc042ea93dcd470f7d5"
# The v71 (report V13) floor module was rendered from the earlier adopted g0q_stage.c;
# its retained component and run keep that exact rendering.
V13_STAGE_RENDERING = "397c9fe33cf7a419de64a2dc0f7c672478eca51d357e45d084d28e9d32994e64"
# The v72 (report V14) storage module of ML057 likewise keeps its own rendering.
V14_STAGE_RENDERING = "d3cf1f0001fec19d07d67b86ac88edad6e02a5d40ffdac8e813a175cda30adc2"
STAGE_LINE = ("\tif (now < 300ULL * NSEC_PER_SEC || now + 15ULL * NSEC_PER_SEC >= 540ULL * NSEC_PER_SEC)\n",
              "\tif (now < 60ULL * NSEC_PER_SEC || now + 15ULL * NSEC_PER_SEC >= 540ULL * NSEC_PER_SEC)\n")

AUTHORITY = HERE/"transport"/"authority.inc.c"
AUTHORITY_SHA256 = "3cb4893a79d7aed7efbba251109b5c1254ca26482dab65f840addce938715e3a"
AUTHORITY_LINE = ("\t    now < 300ULL * NSEC_PER_SEC || now >= deadline ||\n",
                  "\t    now < 60ULL * NSEC_PER_SEC || now >= deadline ||\n")


def _require(value, message):
    if not value:
        raise ValueError(message)


def _render(path, pin, line):
    data = path.read_bytes()
    _require(hashlib.sha256(data).hexdigest() == pin, "adopted source changed: " + path.name)
    text = data.decode()
    _require(text.count(line[0]) == 1, "boot-time floor line differs: " + path.name)
    return text.replace(*line)


def stage_source():
    """The rendered g0q_stage.c for the witness-floor module."""
    return _render(STAGE, STAGE_SHA256, STAGE_LINE)


def authority_source():
    """The rendered transport authority for the witness-floor kernel."""
    return _render(AUTHORITY, AUTHORITY_SHA256, AUTHORITY_LINE)


def kernel_rpmh_source(built):
    """A prepared transport rpmh.c with the adopted authority replaced by its rendering."""
    adopted = AUTHORITY.read_text()
    _require(hashlib.sha256(adopted.encode()).hexdigest() == AUTHORITY_SHA256 and built.count(adopted) == 1,
             "prepared rpmh.c lacks the adopted transport authority")
    return built.replace(adopted, authority_source())


def digest(text):
    return hashlib.sha256(text.encode()).hexdigest()


RPMH = "drivers/soc/qcom/rpmh.c"


def _file_digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def component_floor(record, kernel):
    """True for an exact witness-floor module and kernel, False for unfloored ones; otherwise refuse.

    The record's fields must match the renderings, and the recorded build directories must hold
    them: the module directory's g0q_stage.c is the rendered source, and the kernel's transport
    record pins a prepared rpmh.c that carries the rendered authority instead of the adopted one.
    """
    fields = {FIELD, STAGE_FIELD, AUTHORITY_FIELD}
    keys = fields & set(record)
    transport_path = Path(kernel["image"]).parents[4]/"transport.json"
    _require(_file_digest(transport_path) == kernel["transport_sha256"], "kernel transport record differs")
    import json
    transport = json.loads(transport_path.read_bytes())
    if not keys:
        _require("boot_floor" not in transport, "unfloored module paired with a floor kernel")
        return False
    stage, authority = stage_source(), authority_source()
    version = record.get("report_version")
    expected = {13: V13_STAGE_RENDERING, 14: V14_STAGE_RENDERING, 15: digest(stage)}.get(version) if type(version) is int else None
    _require(keys == fields and type(record[FIELD]) is int and record[FIELD] == FLOOR_MS and
             expected is not None and record[STAGE_FIELD] == expected and
             record[AUTHORITY_FIELD] == digest(authority),
             "boot floor record differs")
    _require(_file_digest(Path(record["module_path"]).parent/STAGE.name) == expected,
             "floor module was not built from the rendered source")
    rpmh = Path(transport["kernel"])/RPMH
    built = rpmh.read_text()
    _require(transport.get("boot_floor", {}).get("authority_source_sha256") == digest(authority) and
             transport["files"][RPMH] == _file_digest(rpmh) and built.count(authority) == 1 and
             AUTHORITY.read_text() not in built, "floor module paired with a kernel without the floor")
    return True
