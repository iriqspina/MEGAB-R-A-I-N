"""Project-owned raster inputs; client paths and MIME declarations grant no access."""
from __future__ import annotations

import base64
import binascii
import copy
import hashlib
import io
import json
import os
from pathlib import Path
import re
import secrets
import stat
import threading
import warnings

from PIL import Image, UnidentifiedImageError

MAX_FILE_BYTES = 8 * 1024 * 1024
MAX_ATTACHMENTS = 6
MAX_UPLOAD_BODY = 4 * ((MAX_FILE_BYTES + 2) // 3) + 8192
MAX_IMAGE_PIXELS = 40_000_000
FORMATS = {'PNG': ('image/png', '.png'), 'JPEG': ('image/jpeg', '.jpg'),
           'GIF': ('image/gif', '.gif'), 'WEBP': ('image/webp', '.webp')}
ID = re.compile(r'[a-f0-9]{64}')
LOCK = threading.RLock()
INVALID = 'Anexo inválido ou indisponível neste projeto.'


def _guard(path, root):
    """Check lexical descendants before resolve hides symlinks or junctions."""
    root = Path(root).absolute()
    path = Path(path).absolute()
    if not path.is_relative_to(root):
        raise ValueError(INVALID)
    relative = path.relative_to(root)
    for current in [root, *[root.joinpath(*relative.parts[:i]) for i in range(1, len(relative.parts) + 1)]]:
        info = current.lstat()
        if stat.S_ISLNK(info.st_mode) or getattr(info, 'st_file_attributes', 0) & 0x400:
            raise ValueError(INVALID)
    info = path.stat()
    if stat.S_ISREG(info.st_mode) and info.st_nlink != 1:
        raise ValueError(INVALID)
    if not path.resolve().is_relative_to(root.resolve()):
        raise ValueError(INVALID)


def _storage(root, create=False):
    root = Path(root).resolve(strict=True)
    target = root / '.mb-anexos'
    if create:
        target.mkdir(exist_ok=True)
    _guard(target, root)
    if not target.is_dir():
        raise ValueError(INVALID)
    return root, target


def _bounded_read(path, root, limit):
    _guard(path, root)
    info = path.stat()
    if not stat.S_ISREG(info.st_mode) or info.st_size > limit:
        raise ValueError(INVALID)
    with path.open('rb') as source:
        data = source.read(limit + 1)
    if len(data) > limit:
        raise ValueError(INVALID)
    return data


def validate_image(data):
    if not isinstance(data, bytes) or not data or len(data) > MAX_FILE_BYTES:
        raise ValueError('Cada imagem deve ter até 8 MiB.')
    try:
        with warnings.catch_warnings():
            warnings.simplefilter('error', Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(data)) as picture:
                fmt = picture.format
                if fmt not in FORMATS:
                    raise ValueError()
                width, height = picture.size
                if width < 1 or height < 1 or width * height > MAX_IMAGE_PIXELS:
                    raise ValueError()
                # Verify containers and decode every bounded frame; a header alone is insufficient.
                picture.verify()
            with Image.open(io.BytesIO(data)) as picture:
                frames = getattr(picture, 'n_frames', 1)
                if frames > 200:
                    raise ValueError()
                pixels = 0
                for frame in range(frames):
                    picture.seek(frame)
                    pixels += picture.size[0] * picture.size[1]
                    if pixels > MAX_IMAGE_PIXELS:
                        raise ValueError()
                    picture.load()
        return FORMATS[fmt]
    except (ValueError, OSError, SyntaxError, EOFError, UnidentifiedImageError,
            Image.DecompressionBombWarning, Image.DecompressionBombError):
        raise ValueError('Use uma imagem PNG, JPEG, GIF ou WebP válida (até 40 milhões de pixels no conjunto de quadros).') from None


def _atomic(path, data):
    temp = path.parent / ('.upload-' + secrets.token_hex(16))
    try:
        with temp.open('xb') as output:
            output.write(data)
        os.replace(temp, path)
    finally:
        if temp.exists():
            temp.unlink()


def _details(root, pid, aid, metadata):
    mime, extension = FORMATS[metadata['format']]
    return dict(id=aid, path=str(root / '.mb-anexos' / (aid + extension)),
                name=metadata['name'], mime=mime, size=metadata['size'],
                url=f'/api/projects/{pid}/attachments/{aid}')


def read_attachment(root, pid, aid):
    """Resolve only a server-generated ID; never open a caller-supplied path."""
    if not isinstance(aid, str) or not ID.fullmatch(aid):
        raise ValueError(INVALID)
    try:
        root, storage = _storage(root)
        raw = _bounded_read(storage / (aid + '.json'), root, 4096)
        metadata = json.loads(raw)
        if (not isinstance(metadata, dict) or metadata.get('id') != aid
                or metadata.get('format') not in FORMATS or not isinstance(metadata.get('name'), str)
                or len(metadata['name']) > 180 or type(metadata.get('size')) is not int):
            raise ValueError(INVALID)
        result = _details(root, pid, aid, metadata)
        data = _bounded_read(Path(result['path']), root, MAX_FILE_BYTES)
        if len(data) != result['size'] or hashlib.sha256(data).hexdigest() != aid:
            raise ValueError(INVALID)
        if validate_image(data)[0] != result['mime']:
            raise ValueError(INVALID)
        return result, data
    except (OSError, ValueError, KeyError, TypeError):
        raise ValueError(INVALID) from None


def save_attachment(root, pid, body):
    if not isinstance(body, dict):
        raise ValueError('Arquivo de imagem inválido.')
    name = body.get('name')
    declared = body.get('mime')
    encoded = body.get('data')
    if not isinstance(name, str) or not name.strip() or len(name) > 180 or any(ord(c) < 32 for c in name):
        raise ValueError('Nome de imagem inválido (até 180 caracteres).')
    if not isinstance(encoded, str) or len(encoded) > 4 * ((MAX_FILE_BYTES + 2) // 3):
        raise ValueError('Cada imagem deve ter até 8 MiB em base64 sem prefixo.')
    try:
        data = base64.b64decode(encoded, validate=True)
    except (ValueError, binascii.Error):
        raise ValueError('Dados da imagem inválidos; use base64 sem prefixo.') from None
    mime, extension = validate_image(data)
    if declared != mime:
        raise ValueError('O tipo informado não corresponde à imagem.')
    # Name is display-only; canonical storage extension always comes from decoded bytes.
    name = name.replace('\\', '/').rsplit('/', 1)[-1].strip()
    if not name or name in {'.', '..'}:
        raise ValueError('Nome de imagem inválido.')
    aid = hashlib.sha256(data).hexdigest()
    try:
        with LOCK:
            root, storage = _storage(root, create=True)
            manifest = storage / (aid + '.json')
            if manifest.exists() or manifest.is_symlink():
                return read_attachment(root, pid, aid)[0]
            target = storage / (aid + extension)
            if target.exists() or target.is_symlink():
                # An interrupted upload may leave these exact bytes, never follow links.
                if _bounded_read(target, root, MAX_FILE_BYTES) != data:
                    raise ValueError(INVALID)
            else:
                _atomic(target, data)
            fmt = next(k for k, v in FORMATS.items() if v[0] == mime)
            metadata = dict(id=aid, name=name, format=fmt, size=len(data))
            _atomic(manifest, json.dumps(metadata, ensure_ascii=False).encode('utf-8'))
            return _details(root, pid, aid, metadata)
    except OSError:
        raise ValueError('Não foi possível guardar a imagem neste projeto.') from None


def resolve_attachments(root, pid, references):
    if references is None:
        references = []
    if not isinstance(references, list) or len(references) > MAX_ATTACHMENTS:
        raise ValueError('Use até 6 imagens por envio.')
    rows = {}
    for reference in references:
        if isinstance(reference, dict):
            aid = reference.get('id')
        elif isinstance(reference, str):
            aid = Path(reference).stem
        else:
            raise ValueError(INVALID)
        result, _ = read_attachment(root, pid, aid)
        if isinstance(reference, str):
            if reference != result['path']:
                raise ValueError(INVALID)
        else:
            for key in ('path', 'url', 'mime', 'size', 'name'):
                if key in reference and reference[key] != result[key]:
                    raise ValueError(INVALID)
        rows[result['id']] = result
    return list(rows.values())


def attachment_fields(details):
    return dict(anexos=[row['path'] for row in details], attachment_details=details)


def normalize_feedback(root, pid, feedback, references=None):
    """Validate top-level, per-note and per-answer images without dropping associations."""
    rows = {}

    def bind(value):
        value.pop('attachment_details', None)
        details = resolve_attachments(root, pid, value.get('anexos', []))
        for row in details:
            rows[row['id']] = row
        if len(rows) > MAX_ATTACHMENTS:
            raise ValueError('Use até 6 imagens por envio, contando notas e respostas.')
        if details or 'anexos' in value:
            value.update(attachment_fields(details))

    top = {'anexos': references if references is not None else []}
    bind(top)
    output = copy.deepcopy(feedback)
    if output is not None:
        bind(output)
        notes = output.get('notas', [])
        if not isinstance(notes, list) or any(not isinstance(n, dict) for n in notes):
            raise ValueError('Notas do relatório inválidas.')
        for note in notes:
            bind(note)
        choices = output.get('respostas', {})
        if not isinstance(choices, (dict, list)):
            raise ValueError('Respostas do relatório inválidas.')
        for choice in choices.values() if isinstance(choices, dict) else choices:
            if isinstance(choice, dict):
                bind(choice)
    return output, list(rows.values())
