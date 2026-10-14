"""Check or run the dedicated named tunnel without exposing its token in argv.

Run only after review/activation. No installation, login, tunnel creation, API
mutation, service registration or firewall change occurs in this script.
The parent application owns the process lifecycle.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parent
PRIVATE = ROOT.parent / 'data' / '.private'
BINARY = ROOT / 'runtime' / 'cloudflared.exe'
TOKEN_FILE = PRIVATE / 'tunnel.token'


def own_windows_child(process):
    """OS-owned lifecycle: terminating this wrapper also closes its dedicated child."""
    if os.name != 'nt': return None
    import ctypes
    from ctypes import wintypes
    class Basic(ctypes.Structure):
        _fields_=[('process_time',ctypes.c_longlong),('job_time',ctypes.c_longlong),
                  ('flags',wintypes.DWORD),('min_working',ctypes.c_size_t),('max_working',ctypes.c_size_t),
                  ('active',wintypes.DWORD),('affinity',ctypes.c_size_t),('priority',wintypes.DWORD),('scheduling',wintypes.DWORD)]
    class Counters(ctypes.Structure):
        _fields_=[(name,ctypes.c_ulonglong) for name in ('reads','writes','others','read_bytes','write_bytes','other_bytes')]
    class Extended(ctypes.Structure):
        _fields_=[('basic',Basic),('io',Counters),('process_memory',ctypes.c_size_t),('job_memory',ctypes.c_size_t),
                  ('peak_process',ctypes.c_size_t),('peak_job',ctypes.c_size_t)]
    api=ctypes.WinDLL('kernel32',use_last_error=True)
    api.CreateJobObjectW.restype=wintypes.HANDLE
    api.CreateJobObjectW.argtypes=[ctypes.c_void_p,wintypes.LPCWSTR]
    api.SetInformationJobObject.argtypes=[wintypes.HANDLE,ctypes.c_int,ctypes.c_void_p,wintypes.DWORD]
    api.AssignProcessToJobObject.argtypes=[wintypes.HANDLE,wintypes.HANDLE]
    api.CloseHandle.argtypes=[wintypes.HANDLE]
    handle=api.CreateJobObjectW(None,None)
    limits=Extended();limits.basic.flags=0x2000  # JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
    if not handle or not api.SetInformationJobObject(handle,9,ctypes.byref(limits),ctypes.sizeof(limits)) or not api.AssignProcessToJobObject(handle,wintypes.HANDLE(int(process._handle))):
        error=ctypes.get_last_error()
        if handle:api.CloseHandle(handle)
        process.terminate();process.wait(timeout=10)
        raise OSError(error,'Unable to own dedicated tunnel lifecycle')
    return lambda:api.CloseHandle(handle)


def check() -> dict:
    token = TOKEN_FILE.read_text(encoding='utf-8').strip() if TOKEN_FILE.is_file() else ''
    gateway = PRIVATE / 'gateway.key'
    key = gateway.read_text(encoding='utf-8').strip() if gateway.is_file() else ''
    manifest_file=ROOT/'runtime'/'cloudflared-manifest.json'
    manifest=json.loads(manifest_file.read_text(encoding='utf-8')) if manifest_file.is_file() else {}
    digest='sha256:'+hashlib.sha256(BINARY.read_bytes()).hexdigest() if BINARY.is_file() else None
    return {
        'binary_present': BINARY.is_file(),
        'binary_digest_verified': bool(digest and digest==manifest.get('digest')),
        'token_valid_format': bool(re.fullmatch(r'[A-Za-z0-9_+/=-]{50,2048}', token)),
        'gateway_key_valid_format': bool(re.fullmatch(r'[a-f0-9]{64}', key)),
        'transport': 'quic', 'origin': '127.0.0.1:8767',
        'starts_network_connection': False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', action='store_true', help='Inicia o túnel já provisionado; padrão apenas verifica.')
    args = parser.parse_args()
    state = check()
    ready = all(state[key] for key in ('binary_present', 'binary_digest_verified', 'token_valid_format', 'gateway_key_valid_format'))
    if not args.run:
        print(json.dumps(state))
        return 0
    if not ready:
        print(json.dumps({'started': False, 'error': 'configuration_incomplete'}))
        return 2
    env = dict(os.environ)
    env['TUNNEL_TOKEN'] = TOKEN_FILE.read_text(encoding='utf-8').strip()
    env['TUNNEL_TRANSPORT_PROTOCOL'] = 'quic'
    command = [str(BINARY), 'tunnel', '--no-autoupdate', '--protocol', 'quic', '--loglevel', 'error', 'run']
    process = subprocess.Popen(command, env=env, stdin=subprocess.DEVNULL,
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                               creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    close_job=own_windows_child(process)
    print(json.dumps({'started': True, 'pid': process.pid, 'transport': 'quic'}), flush=True)
    try:return process.wait()
    finally:
        if close_job:close_job()


if __name__ == '__main__':
    raise SystemExit(main())
