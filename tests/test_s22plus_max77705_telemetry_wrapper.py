"""Execute the actual wrapper with only kernel/hardware primitives substituted."""
from pathlib import Path
import subprocess
import tempfile
import unittest
ROOT=Path(__file__).resolve().parents[1]
MODULE=ROOT/'workspace/public/src/kernel-modules/s22plus_max77705_telemetry'
STUB=r'''
#include <assert.h>
#include <errno.h>
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "telemetry_core.h"
typedef uint64_t u64;typedef uint32_t u32;
#define PAGE_SIZE 4096
#define static_assert _Static_assert
#define DEFINE_MUTEX(name) struct mutex name={0}
#define ATOMIC_INIT(v) {v}
#define MODULE_PARM_DESC(a,b)
#define MODULE_DESCRIPTION(a)
#define MODULE_LICENSE(a)
#define module_param_cb(a,b,c,d) _Static_assert((d)==0444,"read only")
#define module_platform_driver(a)
#define I2C_FUNC_SMBUS_READ_BYTE_DATA 1
#define I2C_FUNC_SMBUS_READ_WORD_DATA 2
#define scnprintf snprintf
struct mutex {int held;};
static int mutex_trylock(struct mutex *m){if(m->held)return 0;m->held=1;return 1;}
static void mutex_lock(struct mutex *m){assert(!m->held);m->held=1;}
static void mutex_unlock(struct mutex *m){assert(m->held);m->held=0;}
typedef struct {int value;} atomic_t;
static int atomic_cmpxchg(atomic_t *a,int old,int next){int value=a->value;if(value==old)a->value=next;return value;}
struct device_node {const char *full_name;};
struct device_driver {const char *name;};
struct device {struct device *parent;struct device_node *of_node;struct device_driver *driver;void *data;};
struct i2c_adapter {struct device dev;};
struct i2c_client {struct device dev;unsigned addr;struct i2c_adapter *adapter;};
struct platform_device {const char *name;struct device dev;};
struct max77705_dev {struct device *dev;struct i2c_client *i2c,*charger,*fuelgauge,*muic,*debug;struct mutex i2c_lock;};
struct kernel_param {};
struct kernel_param_ops {int (*get)(char *,const struct kernel_param *);void *set;};
struct platform_device_id {const char *name;unsigned long data;};
struct platform_driver {int (*probe)(struct platform_device *);int (*remove)(struct platform_device *);struct device_driver driver;const struct platform_device_id *id_table;};
static struct device_node root_node={"/"},fg_node={"/samsung_mobile_device/max77705-fuelgauge"};
static const char *model="Qualcomm Technologies, Inc. Waipio v2 SoC";
static unsigned resistor=5,calls,fault;
static u64 clock_ms=1000;
static struct i2c_client *expected_parent,*expected_fg;
static struct device_node *verified_parent_node,*verified_bus_node;
static u64 ktime_get(void){return clock_ms;}
static u64 ktime_to_ms(u64 v){return v;}
static struct i2c_client *i2c_verify_client(struct device *d){return d==&expected_parent->dev?expected_parent:NULL;}
static void *dev_get_drvdata(struct device *d){return d->data;}
static void *i2c_get_clientdata(struct i2c_client *c){return c->dev.data;}
static bool of_device_is_compatible(struct device_node *n,const char *s){return n==expected_parent->dev.of_node&&!strcmp(s,"maxim,max77705");}
static struct device_node *of_find_node_by_path(const char *p){return !strcmp(p,"/")?&root_node:!strcmp(p,fg_node.full_name)?&fg_node:!strcmp(p,"/soc/i2c@994000/max77705@66")?verified_parent_node:!strcmp(p,"/soc/i2c@994000")?verified_bus_node:NULL;}
static void of_node_put(struct device_node *n){(void)n;}
static int of_property_read_string(struct device_node *n,const char *p,const char **out){assert(n==&root_node&&!strcmp(p,"model"));*out=model;return 0;}
static int of_property_read_u32(struct device_node *n,const char *p,u32 *out){assert(n==&fg_node&&!strcmp(p,"fuelgauge,fg_resistor"));*out=resistor;return 0;}
static int i2c_check_functionality(struct i2c_adapter *a,unsigned flags){assert(a==expected_parent->adapter&&flags==3);return 1;}
static int i2c_smbus_read_byte_data(struct i2c_client *c,unsigned reg){assert(c==expected_parent);assert(((struct max77705_dev*)c->dev.data)->i2c_lock.held);calls++;if(calls==fault)return -EIO;assert(reg<=1);return reg?2:0x15;}
static int i2c_smbus_read_word_data(struct i2c_client *c,unsigned reg){assert(c==expected_fg);assert(((struct max77705_dev*)c->dev.data)->i2c_lock.held);calls++;if(calls==fault)return -EIO;assert(reg==6||reg==9||reg==10);return reg==6?12800:reg==9?51200:65408;}
'''
MAIN=r'''
int main(int argc,char **argv){
 assert(argc==2);const char *test=argv[1];
 struct device_node bus_node={"i2c@994000"},parent_node={"max77705@66"},other_bus={"i2c@other"};
 verified_parent_node=&parent_node;verified_bus_node=&bus_node;
 struct device_driver driver={"max77705"};struct i2c_adapter adapter={.dev={.of_node=&bus_node}};
 struct i2c_client parent={.dev={.of_node=&parent_node,.driver=&driver},.addr=0x66,.adapter=&adapter};
 struct i2c_client gauge={.addr=0x36,.adapter=&adapter};
 struct max77705_dev mfd={.dev=&parent.dev,.i2c=&parent,.fuelgauge=&gauge};
 parent.dev.data=gauge.dev.data=&mfd;expected_parent=&parent;expected_fg=&gauge;
 struct platform_device child={.name="max77705-fuelgauge",.dev={.parent=&parent.dev}};
 if(!strcmp(test,"wrong-bus"))adapter.dev.of_node=&other_bus;
 if(!strcmp(test,"wrong-same-name-bus")){other_bus.full_name="i2c@994000";adapter.dev.of_node=&other_bus;}
 if(!strcmp(test,"wrong-parent"))parent.addr=0x65;
 if(!strcmp(test,"wrong-fg"))gauge.addr=0x35;
 if(!strcmp(test,"wrong-abi"))mfd.i2c=&gauge;
 if(!strcmp(test,"wrong-model"))model="Samsung B0Q PROJECT (board-id,12)";
 if(!strcmp(test,"wrong-resistor"))resistor=2;
 if(!strncmp(test,"wrong-",6)){assert(telemetry_probe(&child)==-ENODEV&&!calls&&!bound_parent);return 0;}
 assert(!telemetry_probe(&child)&&!calls&&bound_parent==&mfd);
 assert(telemetry_probe(&child)==-EBUSY&&!calls);
 assert(!sample_ops.set&&sample_ops.get==sample_get);
 char text[PAGE_SIZE];
 mfd.i2c_lock.held=1;assert(sample_get(text,NULL)==-EAGAIN&&!calls);mfd.i2c_lock.held=0;
 sample_lock.held=1;assert(sample_get(text,NULL)==-EAGAIN&&!calls);sample_lock.held=0;
 if(!strcmp(test,"fault"))fault=4;
 assert(sample_get(text,NULL)>0);assert(!sample_lock.held&&!mfd.i2c_lock.held);
 if(!strcmp(test,"emit")){fputs(text,stdout);return 0;}
 if(fault){assert(calls==4&&strstr(text,"error=-5"));clock_ms+=10000;assert(sample_get(text,NULL)>0&&calls==4&&strstr(text,"start_ms=1000"));return 0;}
 assert(calls==5&&strstr(text,"seq=1 start_ms=1000 valid=7 error=0")&&strstr(text,"voltage_uv=4000000 current_ua=-100000"));
 clock_ms+=999;assert(sample_get(text,NULL)>0&&calls==5&&strstr(text,"start_ms=1000"));
 clock_ms++;assert(sample_get(text,NULL)>0&&calls==8&&strstr(text,"seq=2 start_ms=2000"));
 assert(!telemetry_remove(&child));assert(sample_get(text,NULL)==-ENODEV&&calls==8);
 puts("PASS actual wrapper binding locking cache and removal");return 0;
}
'''

class Wrapper(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory();cls.addClassCleanup(cls.temp.cleanup)
        cls.binary=Path(cls.temp.name)/'wrapper'
        body='\n'.join(x for x in (MODULE/'s22plus_max77705_telemetry.c').read_text().splitlines() if not x.startswith('#include'))
        p=subprocess.run(['cc','-x','c','-','-std=c11','-O1','-Wall','-Wextra','-Werror','-Wno-unused-variable','-fsanitize=undefined','-fno-sanitize-recover=all','-I',str(MODULE),'-o',str(cls.binary)],input=STUB+body+MAIN,text=True,capture_output=True,timeout=30)
        if p.returncode:raise AssertionError(p.stderr)

    def test_producer_consumer_and_faults(self):
        for case in ('good','fault','wrong-bus','wrong-same-name-bus','wrong-parent','wrong-fg','wrong-abi','wrong-model','wrong-resistor'):
            with self.subTest(case=case):
                p=subprocess.run([self.binary,case],capture_output=True,text=True,timeout=5)
                self.assertEqual(p.returncode,0,p.stderr)

if __name__=='__main__':unittest.main()
