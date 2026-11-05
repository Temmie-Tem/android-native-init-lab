// H0 model of short sysfs reads, overflow, close error and ordinary EOF.
#include <assert.h>
#include <errno.h>
#include <fcntl.h>
#include <stdint.h>
#include <string.h>
#include <unistd.h>
#define ML030_REPORT_MAX 256U
#define ML030_RESULT_PATH "/fixed-result"
static size_t offered, offset;
static int read_error, close_error;
static int model_open(const char *path, int flags)
{
	assert(!strcmp(path,ML030_RESULT_PATH) && flags==(O_RDONLY|O_CLOEXEC|O_NOFOLLOW));
	return 1;
}
static ssize_t model_read(int fd, void *out, size_t n)
{
	assert(fd==1);
	size_t count=offered-offset;
	if (count>n) count=n;
	if (count>17) count=17;
	if (!count && read_error) {errno=read_error; return -1;}
	memset(out,'q',count);
	offset+=count;
	return (ssize_t)count;
}
static int model_close(int fd) { assert(fd==1); errno=close_error; return close_error?-1:0; }
#define open model_open
#define read model_read
#define close model_close
#include "reader.inc"
int main(void)
{
	struct sample { size_t bytes; int read_errno,close_errno,expected; };
	struct sample cases[]={ {4,0,0,0},{5,EIO,0,EIO},{7,0,EBADF,EBADF},{256,0,0,0},
	                        {256,EIO,0,EIO},{257,0,0,EOVERFLOW} };
	for (size_t i=0; i<sizeof(cases)/sizeof(cases[0]); i++) {
		uint8_t buf[ML030_REPORT_MAX]={0};
		size_t size=0;
		offered=cases[i].bytes;offset=0;read_error=cases[i].read_errno;close_error=cases[i].close_errno;
		assert(ml030_read_result(buf,&size)==cases[i].expected);
		assert(size==(offered>sizeof(buf)?sizeof(buf):offered));
		for (size_t j=0;j<size;j++) assert(buf[j]=='q');
	}
	return 0;
}
