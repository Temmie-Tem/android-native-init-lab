/* Calls only the pure parameter parser; no driver or device entry is invoked. */
#define P350_DISPLAY_VARIANT 1
#define main unused_renderer_main
#include "../workspace/public/src/native-init/s22plus_native_display_h0.c"
#undef main
int main(int argc, char **argv) {
    require(argc==2 && strlen(argv[1])<8192,"test-arguments");
    char input[8192],output[192];strcpy(input,argv[1]);
    p350_parameters(output,input);puts(output);return 0;
}
