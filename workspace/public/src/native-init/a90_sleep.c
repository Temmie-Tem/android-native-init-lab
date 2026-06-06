#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>

int main(int argc, char **argv) {
    int seconds = 30;
    int index;

    if (argc >= 2) {
        seconds = atoi(argv[1]);
        if (seconds <= 0) {
            seconds = 30;
        }
    }

    printf("a90sleep: sleeping %d seconds\n", seconds);
    fflush(stdout);

    for (index = 0; index < seconds; ++index) {
        if (sleep(1) != 0 && errno != EINTR) {
            return 1;
        }
    }

    printf("a90sleep: done\n");
    return 0;
}
