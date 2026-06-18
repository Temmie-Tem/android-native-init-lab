#ifndef A90_AUDIO_QUERY_H
#define A90_AUDIO_QUERY_H

int a90_audio_query_profiles_cmd(void);
int a90_audio_query_profile_cmd(char **argv, int argc);
int a90_audio_query_stages_cmd(char **argv, int argc);
int a90_audio_query_speaker_map_cmd(char **argv, int argc);

#endif
