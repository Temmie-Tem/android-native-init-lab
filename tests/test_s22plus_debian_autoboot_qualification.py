"""Coherently repinned containers cannot replace qualified CPIO members."""
import gzip
import hashlib
from pathlib import Path,PurePosixPath
import stat
import sys
import tempfile
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'workspace/public/src/scripts/revalidation'))
import s22plus_debian_autoboot_profile_v1 as profile
import s22plus_debian_autoboot_qualification_v1 as qualification
from s22plus_native_records_v3 import pin


def newc(rows):
    result=bytearray()
    for inode,(name,body,mode,uid,nlink) in enumerate([('.',b'',stat.S_IFDIR|0o755,0,1),
            *rows,('TRAILER!!!',b'',0,0,1)],1):
        encoded=name.encode()+b'\0'
        fields=(inode,mode,uid,0,nlink,0,len(body),0,0,0,0,len(encoded),0)
        result+=b'070701'+b''.join(f'{v:08x}'.encode() for v in fields)+encoded
        result+=bytes((-len(result))%4);result+=body;result+=bytes((-len(result))%4)
    return bytes(result)


class PayloadBinding(unittest.TestCase):
    def setUp(self):
        temporary=tempfile.TemporaryDirectory();self.addCleanup(temporary.cleanup);self.folder=Path(temporary.name)
        def source(name):
            path=self.folder/name;path.write_bytes(('qualified '+name+'\n').encode());return pin(path)
        self.built={name:source(name) for name in ('helper','writer','entry','witness','busybox','checker','table','startup_script')}
        self.built['assets']={name:source(name) for name in ('hook','inittab','qualify','defer-usb','crontab','usb')}
        self.built['measured']={name+'_sha256':hashlib.sha256(name.encode()).hexdigest() for name in ('init','shell')}
        self.built['modules']=[dict(name='fixture.ko',size=6,sha256=hashlib.sha256(b'module').hexdigest())]
        expected=profile.ramdisk_payloads(self.built);expected['scripts/fyg8-dev']=self.built['startup_script'];self.rows=[]
        for name,receipt in expected.items():
            mode=0o755 if name=='scripts/fyg8-dev' else 0o400 if name in (
                's22-root-inspect.table','s22-debian-inittab','s22-debian-crontab') else 0o500
            self.rows.append((name,Path(receipt['path']).read_bytes(),stat.S_IFREG|mode,0,1))
        self.rows.extend((('init',b'init',stat.S_IFREG|0o755,0,1),
            ('usr/bin/sh',b'shell',stat.S_IFREG|0o755,0,1),('lab/modules/fixture.ko',b'module',stat.S_IFREG|0o400,0,1)))
        parents=sorted({str(parent) for row in self.rows for parent in PurePosixPath(row[0]).parents if str(parent)!='.'})
        self.rows.extend((name,b'',stat.S_IFDIR|0o755,0,1) for name in parents)
        self.rows.extend(((name,target,stat.S_IFLNK|0o777,0,1) for name,target in (('bin',b'usr/bin'),('sbin',b'usr/sbin'))))

    def bind(self,rows):
        archive=self.folder/'initramfs.gz';archive.write_bytes(gzip.compress(newc(rows),mtime=0))
        return qualification.payload_binding(dict(self.built,initramfs=pin(archive)))

    def test_actual_members_match(self):self.assertTrue(self.bind(self.rows))

    def test_container_repins_do_not_cover_changed_runtime_script_module_or_init(self):
        for path in ('usr/sbin/autoboot-init','usr/sbin/file-log','scripts/fyg8-dev',
                's22-debian-hook','lab/modules/fixture.ko','init','usr/bin/sh'):
            with self.subTest(path=path):
                rows=[(name,b'changed' if name==path else data,mode,uid,links) for name,data,mode,uid,links in self.rows]
                with self.assertRaises(ValueError):self.bind(rows)

    def test_equal_payload_with_changed_owner_mode_or_link_count_is_rejected(self):
        for name in ('usr/sbin/autoboot-init','init','usr/bin/sh'):
            for column,value in ((2,stat.S_IFREG),(2,stat.S_IFREG|0o777),(3,1000),(4,2)):
                rows=list(self.rows);index=next(i for i,row in enumerate(rows) if row[0]==name)
                item=list(rows[index]);item[column]=value;rows[index]=tuple(item)
                with self.subTest(path=name,column=column),self.assertRaises(ValueError):self.bind(rows)

    def test_unselected_module_is_rejected(self):
        with self.assertRaises(ValueError):self.bind(self.rows+[('lab/modules/foreign.ko',b'foreign',stat.S_IFREG|0o400,0,1)])

    def test_alias_or_ancestor_cannot_redirect_qualified_bytes(self):
        for path in ('bin','sbin','scripts','usr/bin','lab/modules'):
            rows=[(name,b'elsewhere' if name==path else data,
                stat.S_IFLNK|0o777 if name==path else mode,uid,links) for name,data,mode,uid,links in self.rows]
            with self.subTest(path=path),self.assertRaises(ValueError):self.bind(rows)


if __name__=='__main__':unittest.main()
