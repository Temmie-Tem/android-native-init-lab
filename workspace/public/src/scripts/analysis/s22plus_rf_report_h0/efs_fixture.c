/* Hexagon userspace fixture. The stock reader is linked from private firmware.
 * Port 0 is a host pipe. The fixture has no device, pathname syscall or modem.
 */
typedef unsigned char byte;
typedef unsigned int word;
static const char name[] = "rfc/rfdevice_report.dat";
static byte reply[320];
static word reply_size, file_size, position, opens, reads, closes, checked;
static byte scenario;
static int held, mock_errno;
extern byte *stock_reader(const byte *, word);
extern int stock_fd;

static int host_io(int nr, int fd, void *data, word size)
{
    register int r0 __asm__("r0") = fd;
    register void *r1 __asm__("r1") = data;
    register word r2 __asm__("r2") = size;
    register int r6 __asm__("r6") = nr;
    __asm__ volatile("trap0(#1)" : "+r"(r0) : "r"(r1), "r"(r2), "r"(r6) : "memory");
    return r0;
}

static __attribute__((noreturn)) void finish(int status)
{
    host_io(93, status, (void *)0, 0);
    __builtin_unreachable();
}

static void transfer(int nr, int fd, void *data, word size)
{
    byte *p = data;
    while (size) {
        int n = host_io(nr, fd, p, size);
        if (n <= 0 || (word)n > size)
            finish(71);
        size -= n;
        p += n;
    }
}

static void verify(int ok, int line)
{
    if (!ok)
        finish(line);
}

#define require(condition) verify((condition), __LINE__)

static int same(const void *first, const void *second, word size)
{
    const byte *a = first, *b = second;
    for (word i = 0; i < size; i++)
        if (a[i] != b[i])
            return 0;
    return 1;
}

int fixture_compare(const byte *a, const byte *b, word size)
{
    return !same(a, b, size);
}

word fixture_length(const char *p)
{
    require(same(p, name, sizeof(name)));
    return sizeof(name) - 1;
}

int fixture_access(const char *p, word mode)
{
    require(mode == 7 && same(p, name, sizeof(name)));
    checked++;
    return scenario != 'D';
}

byte *fixture_denied(word error, const byte *req, word size)
{
    require(scenario == 'D' && error == 19 && req && size && !opens);
    reply[0] = 'D';  /* Fixture access denial; no stock error encoding assumed. */
    reply_size = 1;
    return reply;
}

byte *fixture_allocate(word kind, word size)
{
    require(kind == 89 && size <= sizeof(reply));
    for (word i = 0; i < sizeof(reply); i++)
        reply[i] = 0;
    return reply;
}

int fixture_stat(const char *p, word *st)
{
    require(checked == 1 && same(p, name, sizeof(name)));
    if (scenario == 'A') {
        mock_errno = 2;
        return -1;
    }
    st[3] = file_size;
    return 0;
}

int *fixture_error(void)
{
    return &mock_errno;
}

int fixture_error_code(int e, int group)
{
    require(scenario == 'A' && e == 2 && group == 102);
    return 2;  /* Fixture ENOENT mapping. */
}

int fixture_open(const char *p, int flags)
{
    require(same(p, name, sizeof(name)) && !flags && !held && checked == 1);
    require(scenario == 'R' && opens == 0);
    held = 1;
    opens++;
    return 17;
}

int fixture_read(int fd, byte *dst, word count)
{
    require(held && fd == 17 && count == 256 && position <= file_size);
    word n = file_size - position;
    if (n > count)
        n = count;
    for (word i = 0; i < n; i++)
        dst[i] = (byte)((position + i) % 251);
    position += n;
    reads++;
    return (int)n;
}

int fixture_close(int fd)
{
    require(held && fd == 17);
    held = 0;
    closes++;
    return 0;
}

word fixture_copy(byte *dst, word capacity, const byte *src, word n)
{
    require(n <= capacity);
    for (word i = 0; i < n; i++)
        dst[i] = src[i];
    return n;
}

void fixture_shorten(byte *p, word length)
{
    require(p == reply && length && length <= sizeof(reply));
    reply_size = length;
}

void _start(void)
{
    byte request[4 + sizeof(name)];
    word n;
    transfer(63, 0, &scenario, 1);
    transfer(63, 0, &file_size, 4);
    require(file_size <= 262145 && (scenario == 'R' || scenario == 'A' || scenario == 'D'));
    stock_fd = -1;  /* A fresh fixture boot with no pre-existing transaction. */
    for (;;) {
        transfer(63, 0, &n, 4);
        if (!n)
            break;
        require(n >= 3 && n <= sizeof(request));
        transfer(63, 0, request, n);
        /* H0-only tags, deliberately outside the exercised dispatcher's table. */
        require(request[0] == 0xff && request[1] == 0xff);
        if (!opens)
            require(n == sizeof(request) && !request[2] && request[3] == sizeof(name)
                    && same(request + 4, name, sizeof(name)));
        else
            require(held && n == 3);
        reply_size = 0;
        byte *p = stock_reader(request, n);
        require(p == reply && reply_size);
        word summary[] = {reply_size, opens, reads, closes, held, checked};
        transfer(64, 1, summary, sizeof(summary));
        transfer(64, 1, p, reply_size);
    }
    require(!held);
    finish(0);
}
