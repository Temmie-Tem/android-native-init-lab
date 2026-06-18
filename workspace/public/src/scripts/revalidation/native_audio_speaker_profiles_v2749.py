#!/usr/bin/env python3
"""V2749 reusable audio speaker profile API.

This module turns the V2748-proven internal-speaker path from scattered runner
constants into a small host-side API.  It is intentionally data-only: importing
it performs no device action, no file I/O, no mixer write, no ACDB SET, and no
playback.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Literal


AudioMode = Literal["probe", "listen"]
StageOwner = Literal["host", "native-init", "private-helper"]
DEFAULT_SETCAL_MANIFEST_PATH = "/cache/a90-runtime/pkg/manifests/audio-setcal-internal-speaker-safe.manifest"


def _jsonable(value: object) -> object:
    if isinstance(value, tuple):
        return [_jsonable(item) for item in value]
    if isinstance(value, list):
        return [_jsonable(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    return value


@dataclass(frozen=True)
class AppTypeEntry:
    """Kernel app-type table tuple for one playback endpoint."""

    app_type: int
    acdb_id: int
    sample_rate: int
    bit_width: int
    stream_channels: int

    def global_config_values(self) -> tuple[str, ...]:
        """Values for the write-only global `App Type Config` control."""

        return ("1", str(self.app_type), str(self.sample_rate), str(self.bit_width))

    def global_config_entry(self) -> str:
        """Entry string consumed by the atomic V2733 writer."""

        return f"{self.app_type}:{self.sample_rate}:{self.bit_width}"

    def stream_config_values(self) -> tuple[str, ...]:
        """Values for `Audio Stream 0 App Type Cfg`."""

        return (str(self.app_type), str(self.acdb_id), str(self.sample_rate), str(self.stream_channels))


@dataclass(frozen=True)
class PlaybackLimits:
    """Bounded PCM generation limits for one mode."""

    default_amplitude: float
    max_amplitude: float
    default_duration_ms: int
    max_duration_ms: int

    def validate(self, *, amplitude: float, duration_ms: int, mode: AudioMode) -> None:
        if amplitude <= 0.0 or amplitude > self.max_amplitude:
            raise ValueError(f"amplitude out of bound for {mode} mode: {amplitude}")
        if duration_ms <= 0 or duration_ms > self.max_duration_ms:
            raise ValueError(f"duration_ms out of bound for {mode} mode: {duration_ms}")


@dataclass(frozen=True)
class AudioFeatureStage:
    """One callable stage in the speaker feature contract."""

    stage_id: str
    order: int
    owner: StageOwner
    phase: str
    command_template: tuple[str, ...]
    native_implemented: bool
    writes_runtime_state: bool
    rollback_boundary: bool
    speaker_scope: str
    note: str

    def command_for_profile(self, profile_id: str) -> tuple[str, ...]:
        return tuple(part.format(profile=profile_id) for part in self.command_template)

    def manifest(self, profile_id: str) -> dict[str, object]:
        return {
            "stage_id": self.stage_id,
            "order": self.order,
            "owner": self.owner,
            "phase": self.phase,
            "command": list(self.command_for_profile(profile_id)),
            "native_implemented": self.native_implemented,
            "writes_runtime_state": self.writes_runtime_state,
            "rollback_boundary": self.rollback_boundary,
            "speaker_scope": self.speaker_scope,
            "note": self.note,
        }


@dataclass(frozen=True)
class AudioSpeakerProfile:
    """Replay/playback contract for a native-init audio endpoint."""

    profile_id: str
    display_name: str
    endpoint: str
    card: int
    pcm_device: int
    app_type: AppTypeEntry
    acdb_set_order: tuple[int, ...]
    forbidden_stale_cal_types: tuple[int, ...]
    route_source: str
    acdb_source: str
    sample_rate: int
    channels: int
    sample_width_bytes: int
    probe_limits: PlaybackLimits
    listen_limits: PlaybackLimits
    dmesg_focus_terms: tuple[str, ...]
    mixer_focus_terms: tuple[str, ...]
    output_observer_controls: tuple[str, ...]
    safety_notes: tuple[str, ...]

    def limits_for_mode(self, mode: AudioMode) -> PlaybackLimits:
        return self.listen_limits if mode == "listen" else self.probe_limits

    def validate_playback(self, *, mode: AudioMode, amplitude: float, duration_ms: int) -> None:
        self.limits_for_mode(mode).validate(amplitude=amplitude, duration_ms=duration_ms, mode=mode)

    def global_app_type_values(self) -> tuple[str, ...]:
        return self.app_type.global_config_values()

    def global_app_type_entry(self) -> str:
        return self.app_type.global_config_entry()

    def stream_app_type_values(self) -> tuple[str, ...]:
        return self.app_type.stream_config_values()

    def dmesg_focus_pattern(self) -> str:
        return "|".join(self.dmesg_focus_terms)

    def mixer_focus_pattern(self) -> str:
        return "|".join(self.mixer_focus_terms)

    def manifest(self) -> dict[str, object]:
        payload = _jsonable(asdict(self))
        assert isinstance(payload, dict)
        payload["global_app_type_values"] = list(self.global_app_type_values())
        payload["global_app_type_entry"] = self.global_app_type_entry()
        payload["stream_app_type_values"] = list(self.stream_app_type_values())
        payload["dmesg_focus_pattern"] = self.dmesg_focus_pattern()
        payload["mixer_focus_pattern"] = self.mixer_focus_pattern()
        payload["staged_contract"] = list(staged_contract())
        payload["stage_api"] = stage_manifests(self.profile_id)
        return payload


INTERNAL_SPEAKER_SAFE = AudioSpeakerProfile(
    profile_id="internal-speaker-safe",
    display_name="Internal speaker, V2748-proven safe bounded playback",
    endpoint="internal-speaker",
    card=0,
    pcm_device=0,
    app_type=AppTypeEntry(
        app_type=69941,
        acdb_id=15,
        sample_rate=48000,
        bit_width=16,
        stream_channels=2,
    ),
    acdb_set_order=(39, 20, 20, 13, 9, 11, 12, 15, 23, 16, 21),
    forbidden_stale_cal_types=(10, 14, 24),
    route_source="V2377 Android speaker route delta + V2730/V2735 app-type fix",
    acdb_source="V2632/V2725 corrected SET replay manifest, V2748 audible confirmation",
    sample_rate=48000,
    channels=2,
    sample_width_bytes=2,
    probe_limits=PlaybackLimits(
        default_amplitude=0.02,
        max_amplitude=0.20,
        default_duration_ms=1000,
        max_duration_ms=10000,
    ),
    listen_limits=PlaybackLimits(
        default_amplitude=0.15,
        max_amplitude=0.20,
        default_duration_ms=8000,
        max_duration_ms=10000,
    ),
    dmesg_focus_terms=(
        "q6core",
        "register_topolog",
        "map_memory",
        "avcs",
        "adsp.*ready",
        "adm_open",
        "app type",
        "bit_width",
        "msm_pcm_routing",
        "get_app_type",
        "send_afe_cal",
        "q6asm",
        "AFE_PORT",
        "ASM",
    ),
    mixer_focus_terms=(
        "SPKR",
        "Spkr",
        "WSA",
        "VISENSE",
        "COMP",
        "BOOST",
        "RMS",
        "VI",
        "feedback",
        "RX INT7",
        "SLIMBUS_0_RX",
        "SWR DAC",
        "App Type",
    ),
    output_observer_controls=(
        "COMP7 Switch",
        "SLIMBUS_0_RX Audio Mixer MultiMedia1",
        "RX INT7_1 MIX1 INP0",
        "Audio Stream 0 App Type Cfg",
        "App Type Config",
        "Get RMS",
        "Backend Device Channel Map",
        "SpkrLeft WSA PA Gain",
        "SpkrLeft WSA PA Mute",
        "SpkrLeft WSA T0 Init",
        "SpkrLeft COMP Switch",
        "SpkrLeft BOOST Switch",
        "SpkrLeft VISENSE Switch",
        "SpkrLeft Boost Level",
        "SpkrLeft SWR DAC_Port Switch",
        "AIF4_VI Mixer SPKR_VI_1",
        "AIF4_VI Mixer SPKR_VI_2",
        "WSA_CDC_DMA_RX_0 Audio Mixer MultiMedia1",
        "WSA_CDC_DMA_RX_1 Audio Mixer MultiMedia1",
        "VI_FEED_TX Channels",
    ),
    safety_notes=(
        "V2748 proved audible playback at amplitude 0.15 for 8 seconds.",
        "Do not exceed amplitude 0.20 without a separate WSA/VI-sense safety unit.",
        "Do not replay stale per-subsystem custom-topology cal types 10/14/24.",
        "No smart-amp gain or boost writes beyond the V2377-observed route controls.",
    ),
)


_PROFILES = {INTERNAL_SPEAKER_SAFE.profile_id: INTERNAL_SPEAKER_SAFE}


AUDIO_FEATURE_STAGES = (
    AudioFeatureStage(
        stage_id="preflight-v2321-health",
        order=10,
        owner="host",
        phase="boot",
        command_template=("a90ctl", "version/status/selftest"),
        native_implemented=False,
        writes_runtime_state=False,
        rollback_boundary=True,
        speaker_scope="host",
        note="confirm rollback baseline health before flashing or playback work",
    ),
    AudioFeatureStage(
        stage_id="adsp-boot-once",
        order=20,
        owner="native-init",
        phase="adsp",
        command_template=("audio", "adsp-boot-once", "AUD2_ONE_SHOT_ADSP_BOOT"),
        native_implemented=True,
        writes_runtime_state=True,
        rollback_boundary=False,
        speaker_scope="shared",
        note="bounded ADSP boot write; retry is forbidden in one boot",
    ),
    AudioFeatureStage(
        stage_id="snd-materialize-once",
        order=30,
        owner="native-init",
        phase="snd",
        command_template=("audio", "snd-materialize-once", "AUD3_DEV_SND_MATERIALIZE_ONLY"),
        native_implemented=True,
        writes_runtime_state=True,
        rollback_boundary=False,
        speaker_scope="shared",
        note="materialize ALSA /dev/snd nodes from sysfs only",
    ),
    AudioFeatureStage(
        stage_id="write-global-app-type-config",
        order=40,
        owner="native-init",
        phase="app_type",
        command_template=("audio", "app-type", "{profile}", "--write"),
        native_implemented=True,
        writes_runtime_state=True,
        rollback_boundary=False,
        speaker_scope="shared",
        note="writes App Type Config with the V2735 proven tuple",
    ),
    AudioFeatureStage(
        stage_id="verify-private-acdb-manifest",
        order=45,
        owner="native-init",
        phase="acdb",
        command_template=(
            "audio",
            "setcal",
            "{profile}",
            "--manifest",
            DEFAULT_SETCAL_MANIFEST_PATH,
            "--verify",
            "--dry-run",
        ),
        native_implemented=True,
        writes_runtime_state=False,
        rollback_boundary=False,
        speaker_scope="shared",
        note="verifies private SET arg/payload files by path, size, and sha256 without issuing audio calibration ioctls",
    ),
    AudioFeatureStage(
        stage_id="prepare-acdb-payload-bundle",
        order=47,
        owner="native-init",
        phase="acdb",
        command_template=(
            "audio",
            "setcal",
            "{profile}",
            "--manifest",
            DEFAULT_SETCAL_MANIFEST_PATH,
            "--prepare",
            "--dry-run",
        ),
        native_implemented=True,
        writes_runtime_state=False,
        rollback_boundary=False,
        speaker_scope="shared",
        note="summarizes verified private SET arg/payload byte plan without opening audio devices",
    ),
    AudioFeatureStage(
        stage_id="load-acdb-payload-files",
        order=48,
        owner="native-init",
        phase="acdb",
        command_template=(
            "audio",
            "setcal",
            "{profile}",
            "--manifest",
            DEFAULT_SETCAL_MANIFEST_PATH,
            "--load",
            "--dry-run",
        ),
        native_implemented=True,
        writes_runtime_state=False,
        rollback_boundary=False,
        speaker_scope="shared",
        note="opens and drains verified private SET arg/payload files without opening audio devices or issuing ioctls",
    ),
    AudioFeatureStage(
        stage_id="replay-acdb-setcal-sequence",
        order=50,
        owner="native-init",
        phase="acdb",
        command_template=(
            "audio",
            "setcal",
            "{profile}",
            "--manifest",
            DEFAULT_SETCAL_MANIFEST_PATH,
            "--execute",
        ),
        native_implemented=False,
        writes_runtime_state=True,
        rollback_boundary=False,
        speaker_scope="shared",
        note="SET replay remains blocked until the private manifest verifier is followed by a native ioctl implementation",
    ),
    AudioFeatureStage(
        stage_id="apply-core-speaker-route",
        order=60,
        owner="native-init",
        phase="route",
        command_template=("audio", "route", "{profile}", "--apply", "--layer", "core"),
        native_implemented=True,
        writes_runtime_state=True,
        rollback_boundary=False,
        speaker_scope="shared",
        note="applies only core route controls; endpoint/boost layers remain blocked",
    ),
    AudioFeatureStage(
        stage_id="plan-bounded-pcm-playback",
        order=68,
        owner="native-init",
        phase="pcm",
        command_template=("audio", "play", "{profile}", "--mode", "probe", "--dry-run"),
        native_implemented=True,
        writes_runtime_state=False,
        rollback_boundary=False,
        speaker_scope="internal-speaker",
        note="plans bounded PCM playback from profile defaults and enforces amplitude/duration caps without opening ALSA",
    ),
    AudioFeatureStage(
        stage_id="bounded-pcm-playback",
        order=70,
        owner="native-init",
        phase="pcm",
        command_template=("audio", "play", "{profile}", "--mode", "probe", "--execute"),
        native_implemented=False,
        writes_runtime_state=True,
        rollback_boundary=False,
        speaker_scope="internal-speaker",
        note="planned bounded tone API; amplitude stays capped by the profile",
    ),
    AudioFeatureStage(
        stage_id="reset-core-speaker-route",
        order=80,
        owner="native-init",
        phase="cleanup",
        command_template=("audio", "route", "{profile}", "--reset", "--layer", "core"),
        native_implemented=True,
        writes_runtime_state=True,
        rollback_boundary=False,
        speaker_scope="shared",
        note="resets the same core controls in reverse order",
    ),
    AudioFeatureStage(
        stage_id="rollback-v2321",
        order=90,
        owner="host",
        phase="rollback",
        command_template=("native_init_flash.py", "boot_linux_v2321_usb_clean_identity_rodata.img"),
        native_implemented=False,
        writes_runtime_state=True,
        rollback_boundary=True,
        speaker_scope="host",
        note="checked boot-partition rollback target for live audio tests",
    ),
)


def list_profiles() -> tuple[str, ...]:
    return tuple(sorted(_PROFILES))


def staged_contract() -> tuple[str, ...]:
    return tuple(stage.stage_id for stage in AUDIO_FEATURE_STAGES)


def stage_manifests(profile_id: str = INTERNAL_SPEAKER_SAFE.profile_id) -> list[dict[str, object]]:
    profile = get_profile(profile_id)
    return [stage.manifest(profile.profile_id) for stage in AUDIO_FEATURE_STAGES]


def get_profile(profile_id: str = INTERNAL_SPEAKER_SAFE.profile_id) -> AudioSpeakerProfile:
    try:
        return _PROFILES[profile_id]
    except KeyError as exc:
        raise ValueError(f"unknown audio speaker profile: {profile_id}") from exc


def profile_manifest(profile_id: str = INTERNAL_SPEAKER_SAFE.profile_id) -> dict[str, object]:
    return get_profile(profile_id).manifest()
