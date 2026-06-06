#ifndef A90_CONTROLLER_H
#define A90_CONTROLLER_H

#include <stdbool.h>
#include <stddef.h>

#include "a90_shell.h"

enum a90_controller_busy_reason {
    A90_CONTROLLER_BUSY_NONE = 0,
    A90_CONTROLLER_BUSY_AUTO_MENU,
    A90_CONTROLLER_BUSY_DANGEROUS,
    A90_CONTROLLER_BUSY_POWER,
};

enum a90_controller_menu_request {
    A90_CONTROLLER_MENU_REQUEST_NONE = 0,
    A90_CONTROLLER_MENU_REQUEST_HIDE,
    A90_CONTROLLER_MENU_REQUEST_SHOW,
};

struct a90_controller_policy_result {
    const char *label;
    const char *command;
    bool power_page;
    bool expected_allowed;
    bool actual_allowed;
    enum a90_controller_busy_reason reason;
    unsigned int flags;
};

bool a90_controller_is_hide_word(const char *name);
enum a90_controller_busy_reason a90_controller_command_busy_reason(const char *name,
                                                                   unsigned int flags,
                                                                   bool menu_active,
                                                                   bool power_page_active);
enum a90_controller_busy_reason a90_controller_command_busy_reason_ex(const char *name,
                                                                      unsigned int flags,
                                                                      int argc,
                                                                      char **argv,
                                                                      bool menu_active,
                                                                      bool power_page_active);
const char *a90_controller_busy_message(enum a90_controller_busy_reason reason);
int a90_controller_policy_matrix_run(const struct shell_command *commands, size_t count);
void a90_controller_policy_matrix_summary(char *out, size_t out_size);
size_t a90_controller_policy_matrix_count(void);
const struct a90_controller_policy_result *a90_controller_policy_matrix_entry_at(size_t index);
void a90_controller_clear_menu_ipc(void);
void a90_controller_clear_menu_request(void);
void a90_controller_set_menu_active(bool active);
void a90_controller_set_menu_state(bool active, bool power_page);
bool a90_controller_menu_is_active(void);
bool a90_controller_menu_power_is_active(void);
void a90_controller_request_menu_show(void);
void a90_controller_request_menu_hide(void);
enum a90_controller_menu_request a90_controller_consume_menu_request(void);

#endif
