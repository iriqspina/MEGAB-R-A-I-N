"""Small standard-library transaction shared by quota writers (no models/Qt)."""
from contextlib import contextmanager
import json
import os
from pathlib import Path
import time
import uuid


@contextmanager
def file_lock(path, timeout=3):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    # Keep this inode after release: unlinking a lock while another process
    # waits on it can allow two independent locks on the same destination.
    with path.with_name(path.name+'.lock').open('a+b') as handle:
        handle.seek(0,2)
        if handle.tell()==0:handle.write(b'\0');handle.flush()
        until=time.monotonic()+timeout
        while True:
            try:
                handle.seek(0)
                if os.name=='nt':
                    import msvcrt
                    msvcrt.locking(handle.fileno(),msvcrt.LK_NBLCK,1)
                else:
                    import fcntl
                    fcntl.flock(handle,fcntl.LOCK_EX|fcntl.LOCK_NB)
                break
            except OSError:
                if time.monotonic()>=until:raise TimeoutError('Quota data is busy')
                time.sleep(.02)
        try:yield
        finally:
            handle.seek(0)
            if os.name=='nt':
                import msvcrt
                msvcrt.locking(handle.fileno(),msvcrt.LK_UNLCK,1)
            else:
                import fcntl
                fcntl.flock(handle,fcntl.LOCK_UN)


def update_json(path, transform, *, recover_invalid=False):
    path=Path(path)
    with file_lock(path):
        try:current=json.loads(path.read_text(encoding='utf-8-sig'))
        except FileNotFoundError:current={}
        except (ValueError,UnicodeError):
            if not recover_invalid:raise
            current={}
        if not isinstance(current,dict):
            if not recover_invalid:raise ValueError('Expected an object')
            current={}
        result=transform(current)
        temp=path.with_name(path.name+'.'+uuid.uuid4().hex+'.tmp')
        try:
            temp.write_text(json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False),encoding='utf-8')
            os.replace(temp,path)
        finally:
            if temp.exists():temp.unlink()
    return result
