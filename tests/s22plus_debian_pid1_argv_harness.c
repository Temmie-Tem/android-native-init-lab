/* Exercise the production byte predicate without substituting its logic. */
#define _GNU_SOURCE
#include <errno.h>
#include <fcntl.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <sys/stat.h>
#include <unistd.h>
#include "s22plus_fyg8_max77705_result_parser.inc.c"
static const uint8_t early_shell_hash[32],early_init_hash[32];
static int fs1_error(void) {return errno?errno:EIO;}
#include "pid1-measure.h"

int main(int argc,char **argv) {
    char bytes[256];
    if(argc==2 && !strcmp(argv[1],"read-error")) {
        printf("%d\n",pid1_cmdline_matches(bytes,-1));return 0;
    }
    if(argc!=1)return 2;
    size_t length=fread(bytes,1,sizeof(bytes),stdin);
    if(ferror(stdin) || !feof(stdin))return 3;
    printf("%d\n",pid1_cmdline_matches(bytes,(ssize_t)length));return 0;
}
