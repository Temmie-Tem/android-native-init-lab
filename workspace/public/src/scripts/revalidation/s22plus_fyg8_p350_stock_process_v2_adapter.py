#!/usr/bin/env python3
"""P350 raw Carrier decoder binding and three-session display metadata."""
from pathlib import Path
import hashlib

TEMPLATE_SOURCE = Path(__file__).with_name('s22plus_fyg8_p345_stock_process_v2_adapter.py')
TEMPLATE_IDENTITY = {'size':7753,'sha256':'f9934c7d274a93ee079ee15e5f7daca089326d8da075086f03eaf77acf7bae40'}
_template=TEMPLATE_SOURCE.read_bytes()
if {'size':len(_template),'sha256':hashlib.sha256(_template).hexdigest()}!=TEMPLATE_IDENTITY:
    raise ValueError('P350 adapter template identity differs')
_template=_template.replace(b'P345',b'P350').replace(b'p345',b'p350')
_template=_template.replace(b'readonly-research-shell-v1',b'display-once-v1')
_template=_template.replace(b'readonly_research_shell_v1',b'display_once_v1')
_template=_template.replace(b'five-same-fd|no-idle|no-reopen|no-lease|rollback-required|readonly-child|authenticated-cancel',
    b'three-same-fd|usb-before|display-once|usb-after|no-lease|rollback-required')
_template=_template.replace(b'INITIAL_SESSION_COUNT = SAME_FD_SESSION_COUNT = 5',b'INITIAL_SESSION_COUNT = SAME_FD_SESSION_COUNT = 3')
_template=_template.replace(b'TOTAL_COMMANDS = 15',b'TOTAL_COMMANDS = 9')
_template=_template.replace(b'"initial_session_count": 5',b'"initial_session_count": 3')
_template=_template.replace(b'"same_fd_session_count": 5',b'"same_fd_session_count": 3')
_template=_template.replace(b'"total_commands": 15',b'"total_commands": 9')
_template=_template.replace(b'"read_only_child_required": True',b'"read_only_child_required": False')
exec(compile(_template,str(TEMPLATE_SOURCE)+'#p350','exec'),globals())
