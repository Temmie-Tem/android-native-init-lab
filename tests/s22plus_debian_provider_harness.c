#define _GNU_SOURCE
#include <dirent.h>
#include <errno.h>
#include <limits.h>
#include <stdio.h>
#include <string.h>
#include <sys/stat.h>
#include <unistd.h>
static int fs1_error(void){return errno>0 ? errno : EIO;}
#include "integrated-providers.h"
int main(int argc,char **argv) {
    if(argc!=2)return 2;
    struct di_provider spec={argv[1],"/soc/qcom,spmi@c42d000","spmi_pmic_arb"};
    printf("%d\n",di_provider_scan(&spec));
    return 0;
}
