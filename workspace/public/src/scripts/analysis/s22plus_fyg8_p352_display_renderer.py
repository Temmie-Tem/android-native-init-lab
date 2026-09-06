"""Fresh renderer over immutable P351; exact vendor name and cached failure values."""
import hashlib
from pathlib import Path

import s22plus_fyg8_p351_display_renderer as predecessor
import s22plus_fyg8_display_kms_contract_h0 as kms

PREDECESSOR_SHA = "f68dc412f21d2a14532ea458eafe43d8c3e4601efc941cb504fc676e4c2e9ae8"


def render():
    if hashlib.sha256(Path(predecessor.__file__).read_bytes()).hexdigest() != PREDECESSOR_SHA:
        raise ValueError("P352 predecessor renderer generator drift")
    source = predecessor.render().decode()

    def once(old, new):
        nonlocal source
        if source.count(old) != 1:
            raise ValueError("P352 renderer transform seam differs: " + old)
        source = source.replace(old, new, 1)

    once("static int fd = -1;", '#include "s22plus_native_display_diagnostic_v3.inc.c"\nstatic int fd = -1;')
    once('    fprintf(stderr, "DISPLAY_FAIL stage=%s errno=%d\\n", stage, errno);',
         '    int saved_errno=errno;\n    fprintf(stderr, "DISPLAY_FAIL stage=%s errno=%d\\n", stage, saved_errno);\n    errno=saved_errno; display_failure_context();')
    once('    if (ioctl(fd, op, arg) < 0)',
         '    display_diag.ioctl_op=op; display_diag.ioctl_stage=stage;\n    if (ioctl(fd, op, arg) < 0)')
    once('    struct props p = {0};', '    display_diag.property_object=obj;\n    struct props p = {0};')
    once('    uint32_t found=0;', '    display_diag.property_name=name;\n    uint32_t found=0;')
    once('    require(r.count_crtcs &&',
         '    display_diag.resources_crtcs=r.count_crtcs; display_diag.resources_connectors=r.count_connectors;\n    require(r.count_crtcs &&')
    once('        require(!s.connector,"multiple-dsi");',
         '        display_diag.connector=c.connector_id;\n        require(!s.connector,"multiple-dsi");')
    once('        /* A unique lowest-refresh',
         '        display_diag.mode_count=nm;\n        memcpy(display_diag.modes,modes,(nm<16?nm:16)*sizeof(modes[0]));\n        /* A unique lowest-refresh')
    once('        require(matches==1,"mode-selection");',
         '        display_diag.lowest_hz=hz; display_diag.matches=matches;\n        require(matches==1,"mode-selection");')
    once('    require(s.plane && s.crtc,"no-primary");',
         '    display_diag.plane=s.plane; display_diag.crtc=s.crtc;\n    require(s.plane && s.crtc,"no-primary");')
    comparisons = [f'm->{key}=={value}U' for key, value in kms.SELECTED.items() if key != 'name']
    comparisons += ['memchr(m->name,0,sizeof(m->name))!=NULL',
                    f'!strcmp(m->name,"{kms.SELECTED["name"]}")']
    once('static struct selection select_display(void) {',
         '/* Source-derived exact cmdHS tuple; returned type/preference is retained. */\n'
         'static int exact_mode(const struct drm_mode_modeinfo *m) {\n'
         '    return ' + ' && '.join(comparisons) + ';\n}\n'
         'static struct selection select_display(void) {')
    start = source.index('        /* A unique lowest-refresh')
    end = source.index('        display_diag.lowest_hz=hz;', start)
    source = source[:start] + '''        /* Select only the source-bound 30HS mode. No alternate mode attempt. */
        uint32_t hz=30, matches=0;
        for(uint32_t j=0;j<nm;j++) if(exact_mode(&modes[j])) {
            s.mode=modes[j]; matches++;
        }
''' + source[end:]
    once('    call(DRM_IOCTL_VERSION,&v,"driver-version");require(v.name_len<sizeof(name)&&!strcmp(name,"msm"),"driver-name");',
         '    call(DRM_IOCTL_VERSION,&v,"driver-version");\n'
         '    display_diag.driver_length=v.name_len; memcpy(display_diag.driver_name,name,sizeof(display_diag.driver_name));\n'
         '    require(v.name_len==7&&!memcmp(name,"msm_drm",7),"driver-name");')
    return source.encode()
