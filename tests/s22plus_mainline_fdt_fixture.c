/* H0 fixture links the actual built uniLoader handler/libfdt objects. */
#include <stdio.h>
#include <stdlib.h>
#include <stdarg.h>
extern int ramdisk_handler_patch_dtb(const void *,void *,int);
void printk(int level,const char *format,...) {(void)level;(void)format;}
int main(int argc,char **argv) {
    if(argc!=4)return 90;
    size_t capacity=(size_t)strtoul(argv[3],NULL,10);
    if(!capacity||capacity>2000000)return 91;
    unsigned char *input=calloc(1,2000000),*output=calloc(1,capacity);
    if(!input||!output)return 92;
    FILE *f=fopen(argv[1],"rb");if(!f)return 93;
    size_t size=fread(input,1,2000000,f);int extra=fgetc(f);
    if(ferror(f)||extra!=EOF||fclose(f)||size<40)return 94;
    int rc=ramdisk_handler_patch_dtb(input,output,(int)capacity);
    if(rc) {printf("HANDLER_REJECTED %d\n",rc);free(input);free(output);return 1;}
    f=fopen(argv[2],"wb");if(!f)return 95;
    if(fwrite(output,1,capacity,f)!=capacity||fclose(f))return 96;
    printf("HANDLER_SUCCESS %zu\n",capacity);free(input);free(output);return 0;
}
