# NATIVE_INIT V2732 — App Type Config write-semantics recon

## Scope

Host-only analysis after V2731.  V2731 wrote:

```text
tinymix -D 0 "App Type Config" 1 69941 48000 16
```

The command returned `rc=0`, but the following PCM probe still printed:

```text
msm_pcm_routing_get_app_type_idx: App type not available, fallback to default
adm_open:bit_width:0 app_type:0x11135 acdb_id:15
```

This report checks whether the failure is likely a wrong field layout, a wrong
kernel lead, or a userspace mixer-write semantics issue.

## Findings

### 1. Public Qualcomm routing source confirms the intended kernel layout

The public Qualcomm `msm-pcm-routing-v2.c` put callback for `App Type Config`
uses this sequence:

```text
value[0] = num_app_types
repeat num_app_types times:
  app_type
  sample_rate
  bit_width
```

The same source defines the control as `SOC_SINGLE_MULTI_EXT("App Type Config",
..., 128, ...)`.  It also confirms that `msm_pcm_routing_get_app_type_idx()`
searches `app_type_cfg[]`, logs "App type not available" on miss, and returns
index 0.  The prepare path then consumes `app_type_cfg[idx].bit_width`, matching
the V2731 `bit_width:0` failure signature.

Source used:
- Qualcomm/Google kernel msm `msm-pcm-routing-v2.c`, put callback and control:
  https://android.googlesource.com/kernel/msm/+/android-7.1.0_r0.2/sound/soc/msm/qdsp6v2/msm-pcm-routing-v2.c
- Qualcomm/Google kernel msm `msm_pcm_routing_get_app_type_idx()` and prepare
  path: same file.

### 2. V2731 did not falsify the field order

V2731 falsified only this specific userspace invocation:

```text
tinymix -D 0 "App Type Config" 1 69941 48000 16
```

It does **not** yet falsify the kernel layout.  The public source says the tuple
layout V2731 attempted is correct for the Qualcomm implementation:

```text
[num_app_types, app_type, sample_rate, bit_width]
```

Therefore trying `1 69941 16 48000` is lower-priority unless Samsung's compiled
kernel differs from this public Qualcomm source.

### 3. TinyALSA `tinymix` is a bad writer for this write-only multi-value control

Both upstream tinyalsa and AOSP `tinymix` set integer controls by repeatedly
calling `mixer_ctl_set_value(ctl, index, value)` for each supplied value.  They
do not use `mixer_ctl_set_array()` for integer controls; `mixer_ctl_set_array()`
is used for byte controls.

That is a strong explanation for V2731:

1. `App Type Config` is write-only/transient; its get callback returns zeros.
2. A per-index `mixer_ctl_set_value()` submits one full ALSA elem write with only
   one index populated.
3. The kernel put callback clears `app_type_cfg[]` at the start of each write.
4. V2731's four values likely became four independent writes:
   - index 0 = `1` → `num_app_types=1`, but app/rate/width still zero;
   - index 1 = `69941` → `num_app_types=0`, table cleared;
   - index 2 = `48000` → `num_app_types=0`, table cleared;
   - index 3 = `16` → `num_app_types=0`, table cleared.
5. The final table remains empty, exactly matching the later fallback.

This makes V2731's `rc=0` unsurprising: every individual ioctl can succeed while
the multi-value control's semantic state is still wrong.

Sources used:
- tinyalsa upstream `utils/tinymix.c` set path:
  https://github.com/tinyalsa/tinyalsa/blob/master/utils/tinymix.c
- tinyalsa upstream `src/mixer.c` `mixer_ctl_set_value()` /
  `mixer_ctl_set_array()` behavior:
  https://github.com/tinyalsa/tinyalsa/blob/master/src/mixer.c
- AOSP `platform/external/tinyalsa/tinymix.c` shows the same per-index integer
  write pattern:
  https://android.googlesource.com/platform/external/tinyalsa/

### 4. Android-good log evidence remains semantic-only

Existing Android captures show the HAL semantic tuple order as:

```text
set_app_type_cfg app_type_cfg->app_type <id>,
set_app_type_cfg app_type_cfg->sample_rate <rate>,
set_app_type_cfg app_type_cfg->bit_width 16
```

They confirm the field names and values but do not prove the ALSA write
mechanism, because the HAL is expected to submit the complete array in one
control write rather than using `tinymix`'s per-index path.

Relevant observed values:

```text
app_type 69938, sample_rate 48000, bit_width 16
app_type 69937, sample_rate 48000, bit_width 16
app_type 69936, sample_rate 11025, bit_width 16
```

For speaker playback, project route evidence continues to use:

```text
app_type 69941, acdb_id 15, sample_rate 48000
```

## Conclusion

The current best root cause for V2731 is not a wrong numeric tuple.  It is that
`tinymix` is the wrong tool for this specific write-only 128-value integer
control.

The kernel likely requires one atomic ALSA `SNDRV_CTL_IOCTL_ELEM_WRITE` carrying
the full integer value array with:

```text
value[0] = 1
value[1] = 69941
value[2] = 48000
value[3] = 16
value[4..127] = 0
```

## Next unit

Build a tiny native control writer that performs one atomic ALSA elem write for
`App Type Config`, instead of calling `tinymix`:

1. Open `/dev/snd/controlC0`.
2. Resolve the `App Type Config` control by name or use the known numid only
   after confirming it at runtime.
3. Submit a single `SNDRV_CTL_IOCTL_ELEM_WRITE` with all 128 integer slots.
4. In the replay runner, replace the V2731 global `tinymix` write with this
   atomic writer, then re-run one bounded native replay.

Expected discriminator:

- If `msm_pcm_routing_get_app_type_idx` no longer falls back and
  `adm_open:bit_width` flips from `0` to `16`, V2731 was a userspace writer
  artifact.
- If fallback remains after one atomic write, then the next hypothesis is
  Samsung source divergence or the wrong control instance/numid, not field order
  first.

Do not repeat V2731 unchanged.
