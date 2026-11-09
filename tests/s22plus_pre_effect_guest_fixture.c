/* Actual ml030_module_result gate, with bounded supplied report and stubbed I/O. */
#include <assert.h>
#include <errno.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include "link-report.h"
#define ML030_BODY 136U
#define ML030_FRAME 168U
#define ML030_REPORT_MAX 256U
static uint8_t canary_key[32],canary_id[32],ml030_result_digest[32];
static unsigned int sent,hashed;
static unsigned char input[257];
static size_t input_size;
static int ml030_load_once(void) { return 0; }
static int ml030_read_result(uint8_t *out,size_t *size) { memcpy(out,input,input_size);*size=input_size;return 0; }
static void g_put32(uint8_t *out,uint32_t value) { memcpy(out,&value,4); }
static void g_tag(uint8_t *out,const uint8_t *key,const uint8_t *id,unsigned int kind,const uint8_t *data,size_t size)
{ (void)key;(void)id;(void)data;assert(kind==20 && size==404);memset(out,0,32); }
static int transfer(int fd,uint8_t *data,size_t size,int write)
{ (void)data;assert(fd==1 && size==436 && write==1);sent++;return 0; }
static void g_hash(const uint8_t *data,size_t size,uint8_t *out)
{ (void)data;assert(size==436);memset(out,1,32);hashed++; }
#include "guest.inc"
int main(void)
{
	input_size=fread(input,1,sizeof(input),stdin);assert(input_size<=256);
	uint8_t witness[ML030_FRAME]={0};int rc=ml030_module_result(1,witness);
	assert(sent==1 && hashed==(rc==0));printf("%d\n",rc);return 0;
}
