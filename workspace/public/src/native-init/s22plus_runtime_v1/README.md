# Direct S22+ FYG8 native sources

These public source fragments replace historical source projection for the
prospective native generation path. The default `console-v1` profile preserves
the production P383 behavior, including its post-authentication HUD. The explicit
`local-display-v1` profile starts local ownership before OPEN/AUTH at the existing
native publication boundary, after unchanged platform bootstrap/USB setup. The consumed candidate
generators, artifacts and execution bindings remain unchanged.

The source API is [s22plus_native_source_v1.py](../../scripts/revalidation/s22plus_native_source_v1.py).
It has no candidate imports, generated Python or predecessor transformations.

| Fragment | Responsibility |
| --- | --- |
| `protocol.inc.c.in` | Existing frame, authentication, bounded I/O and session helpers |
| `return.inc.c.in` | Existing fixed return modules, progress records and preparation |
| `commands.inc.c.in` | Root commands, cancellation, output credits and CONTROL state |
| `hud.inc.c.in` | Renderer/collector children, bounded IPC, updates and cleanup |
| `session.inc.c.in` | Console loop and authentication-to-console entry order |
| `display.c.in` | Current DRM renderer, status/gauge collection and memory snapshot mode |
| `console_terminal.inc.c.in` | Exact historical console terminal behavior for the default profile |
| `local_display.inc.c.in` | PID1-owned local preparation, cooperative updates, deadlines and cleanup |
| `local_entry.inc.c.in` | One authenticated attempt, terminal state and single CONTROL return |
| `local_publish.inc.c.in` | Local start before boot-ID read; replaces the historical publication retry body |

The helper joins its five fragments with explicit original newline separators. Only declared
namespace, run-ID (ASCII and C-escaped), authentication-key and display-version
slots and fixed profile hooks are substituted. Profile selection accepts only the
two named implementations, with unknown profiles rejected. The memory census and display module plan are rendered
from typed metadata. No caller-supplied C body or arbitrary file inclusion is
accepted by the API. Existing protocol names such as P328/P345 remain internal
compatibility names; renaming them is outside this refactor.

`helper_template` contains a key placeholder. `materialize_helper` returns keyed
source to its caller, which must keep it private. The H0 build harness only writes
such source below `workspace/private/`. Never commit materialized keys, firmware,
compiled payloads or device evidence here.

The [H0 comparison harness](../../scripts/analysis/s22plus_native_refactor_h0_v1.py)
uses the historical generator only as an oracle and reuses the existing platform
compiler/packager. It checks actual keyed C, renderer, metadata, ARM64 ELF and A/B
boot/AP equality. The deeper source-matched platform envelope is preserved; this
directory is not a replacement for that entire boot builder or the F1 runner.
That platform envelope/compiler binds `k_run_id`; its identity must match the
explicit helper identity when this API is adopted by a future candidate.

The [local-display H0 harness](../../scripts/analysis/s22plus_local_display_h0_v1.py)
uses `join_platform` on a fully bound platform source. That join replaces one
exact default helper and the publication body, marking three now-unreachable
publication-only witnesses unused without modifying their bodies. It builds
static ARM64 init/child/renderer components twice; it creates no AP or live
manifest. The selected profile has 916 renderer frames, a 1MiB RAM log and
unchanged 601-sample producers. See the [lifecycle specification](../../../../../docs/operations/S22PLUS_FYG8_LOCAL_DISPLAY_LIFECYCLE_V1.md)
for timing, cached progress provenance, observer compatibility and proof limits.

Quoted C includes are included in `source_receipts`; the generated display-plan
header is bound separately with the configuration and emitted source. A future
behavior change must update the reachable source closure and undergo the existing
review and qualification process. This source API does not allocate a candidate,
activate a lane, renew a budget, or authorize a device effect.
