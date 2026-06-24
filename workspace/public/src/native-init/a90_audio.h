#ifndef A90_AUDIO_H
#define A90_AUDIO_H

int a90_audio_cmd(char **argv, int argc);
int a90_audio_boot_chime_start_once(void);
int a90_audio_start_pcm_stream_worker_quiet(const char *profile_id,
                                            const char *pcm_stream_path,
                                            int amplitude_milli,
                                            int duration_ms);

#endif
