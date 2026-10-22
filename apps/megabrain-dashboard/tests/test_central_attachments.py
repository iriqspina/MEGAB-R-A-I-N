"""Raster upload and bindings against synthetic stores only; no live model calls."""
import asyncio
import base64
import hashlib
import io
import json
import os
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

APP = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(APP))
sys.path.insert(0, str(APP / 'runtime-packages'))
from PIL import Image
import central_attachments as images
import central_server as server
from central_store import Store, ident
import test_central_security as security_fixture
asgi_request = security_fixture.asgi_request


def raster(fmt='PNG', color=(20, 40, 60)):
    output = io.BytesIO()
    Image.new('RGB', (4, 3), color).save(output, format=fmt)
    return output.getvalue()


class AttachmentTests(unittest.TestCase):
    def setUp(self):
        self.env = patch.dict(os.environ, {'MB_ISOLATED': '1', 'MB_PONTE': '0'})
        self.env.start()
        self.fixture = security_fixture.CentralSecurityTests()
        self.fixture.setUp()
        self.app = self.fixture.local
        self.auth = self.fixture.local_login()
        self.pid = self.fixture.pid
        self.url = f'/api/projects/{self.pid}/attachments'
        self.comments = f'/api/projects/{self.pid}/comments'
        self.jobs = f'/api/projects/{self.pid}/jobs'
        asset = self.fixture.sources.index_file(self.fixture.html, self.fixture.project)
        self.feedback = f'/api/reports/{asset["id"]}/feedback'
        self.digest = hashlib.sha256(self.fixture.html.read_bytes()).hexdigest()

    def tearDown(self):
        self.fixture.tearDown()
        self.env.stop()

    def request(self, path, method='GET', body=None, headers=None, chunks=False):
        return asyncio.run(asgi_request(self.app, path, method, body,
                                       self.auth if headers is None else headers, chunks))

    def json(self, path, method='GET', body=None, headers=None, chunks=False):
        status, headers, content = self.request(path, method, body, headers, chunks)
        return status, headers, json.loads(content)

    def body(self, fmt='PNG', data=None, **changes):
        mime, extension = images.FORMATS[fmt]
        return dict(name='print' + extension, mime=mime,
                    data=base64.b64encode(raster(fmt) if data is None else data).decode(), **changes)

    def upload(self, fmt='PNG', data=None, headers=None):
        status, _, result = self.json(self.url, 'POST', self.body(fmt, data), headers)
        self.assertEqual(status, 200, result)
        return result['attachment']

    def test_upload_read_all_formats_are_private_and_survive_reopen(self):
        for fmt in images.FORMATS:
            with self.subTest(fmt=fmt):
                data = raster(fmt)
                saved = self.upload(fmt, data)
                self.assertEqual(saved['size'], len(data))
                self.assertEqual(saved['id'], hashlib.sha256(data).hexdigest())
                self.assertTrue(Path(saved['path']).is_relative_to(self.fixture.project / '.mb-anexos'))
                self.assertEqual(Path(saved['path']).read_bytes(), data)
                status, headers, content = self.request(saved['url'])
                self.assertEqual((status, content), (200, data))
                self.assertEqual(headers['content-type'], saved['mime'])
                self.assertEqual(headers['x-content-type-options'], 'nosniff')
                self.assertEqual(headers['cache-control'], 'no-store')
                self.assertEqual(self.request(saved['url'], headers={})[0], 401)
                self.assertEqual(images.read_attachment(self.fixture.project, self.pid, saved['id'])[0], saved)
        other = server.build_app(Store(self.fixture.store.path), self.fixture.sources)
        self.assertEqual(asyncio.run(asgi_request(other, saved['url'], headers=self.auth))[2], data)

    def test_upload_requires_auth_csrf_origin_and_connected_project(self):
        body = self.body()
        self.assertEqual(self.json(self.url, 'POST', body, {})[0], 401)
        for change in [{'x-mb-csrf': ''}, {'origin': 'https://outside.invalid'}, {'sec-fetch-site': 'cross-site'}]:
            with self.subTest(change=change):
                self.assertEqual(self.json(self.url, 'POST', body, {**self.auth, **change})[0], 403)
        self.assertEqual(self.json('/api/projects/unknown/attachments', 'POST', body)[0], 404)
        self.assertFalse((self.fixture.project / '.mb-anexos').exists())

    def test_upload_is_content_idempotent_and_request_key_rejects_different_body(self):
        auth = {**self.auth, 'idempotency-key': 'attachment_attempt_012345'}
        first = self.upload(headers=auth)
        self.assertEqual(self.upload(headers=auth), first)
        self.assertEqual(self.upload(), first)
        self.assertEqual(len(list((self.fixture.project / '.mb-anexos').iterdir())), 2)
        changed = self.body(data=raster(color=(1, 2, 3)))
        self.assertEqual(self.json(self.url, 'POST', changed, auth)[0], 409)

    def test_invalid_type_base64_mime_and_truncated_bytes_are_visible_errors(self):
        bodies = [dict(name='x.png', mime='image/png', data='!not base64'),
                  dict(name='x.png', mime='image/png', data='data:image/png;base64,AAAA'),
                  self.body(data=b'<svg onload="attack()"></svg>'), self.body(data=b'<html>bad</html>'),
                  self.body(data=raster()[:40]), {**self.body(), 'mime': 'text/html'},
                  {**self.body(), 'name': '\x00bad.png'}, {**self.body(), 'data': 123}]
        for body in bodies:
            with self.subTest(body=str(body)[:60]):
                status, _, result = self.json(self.url, 'POST', body)
                self.assertEqual(status, 400)
                self.assertIn('detail', result)
                self.assertNotIn(str(self.fixture.base), result['detail'])
        # A deceptive name is display-only; bytes choose the extension and MIME.
        status, _, result = self.json(self.url, 'POST', {**self.body(), 'name': '../../looks-like.html'})
        self.assertEqual(status, 200)
        self.assertEqual(Path(result['attachment']['path']).suffix, '.png')
        self.assertEqual(result['attachment']['name'], 'looks-like.html')

    def test_gif_that_expands_after_first_frame_obeys_decoded_pixel_budget(self):
        def single_gif(size, color):
            output = io.BytesIO()
            picture = Image.new('P', size, color)
            picture.putpalette([0, 0, 0, 255, 255, 255] + [0] * 762)
            picture.save(output, format='GIF', optimize=False)
            return output.getvalue()
        small = single_gif((1, 1), 0)
        large = single_gif((20, 20), 1)
        offset = 13 + 3 * (2 ** ((large[10] & 7) + 1))
        data = small[:-1] + large[offset:-1] + b';'
        # The first frame is 1 pixel, the next expands to 400; both are real GIF frames.
        with patch.object(images, 'MAX_IMAGE_PIXELS', 100):
            self.assertEqual(self.json(self.url, 'POST', self.body('GIF', data))[0], 400)

    def test_upload_limit_is_eight_mib_and_only_upload_has_larger_body_budget(self):
        data = raster()
        boundary = data + b'\x00' * (images.MAX_FILE_BYTES - len(data))
        self.upload(data=boundary)
        self.assertEqual(self.json(self.url, 'POST', self.body(data=boundary + b'\x00'))[0], 400)
        streamed = b' ' * (images.MAX_UPLOAD_BODY + 1)
        self.assertEqual(self.request(self.url, 'POST', streamed, chunks=True)[0], 413)
        for path in [self.comments, self.jobs, self.url + '/extra', self.feedback]:
            with self.subTest(path=path):
                self.assertEqual(self.request(path, 'POST', b' ' * 350001, chunks=True)[0], 413)
        for length in ['bad', '-1', str(images.MAX_UPLOAD_BODY + 1)]:
            self.assertEqual(self.request(self.url, 'POST', self.body(), {**self.auth, 'content-length': length})[0], 413)

    def test_cross_project_forged_references_and_paths_never_read_arbitrary_files(self):
        saved = self.upload()
        other = self.fixture.base / 'other'
        other.mkdir()
        other_pid = ident(other)
        self.fixture.sources.projects[other_pid] = other
        self.assertEqual(self.request(f'/api/projects/{other_pid}/attachments/{saved["id"]}')[0], 400)
        unknown = {**saved, 'path': str(other / '.mb-anexos' / Path(saved['path']).name)}
        for reference in [unknown, {**saved, 'id': '../private'}, {**saved, 'mime': 'text/html'},
                          str(self.fixture.html), saved['path'] + '/../private', {**saved, 'url': '/other'}]:
            with self.subTest(reference=reference):
                status, _, result = self.json(self.comments, 'POST', {'anexos': [reference]})
                self.assertEqual(status, 400)
                self.assertNotIn(str(self.fixture.base), result['detail'])
        self.assertEqual(self.fixture.store.listing('comments', self.pid), [])

    def test_hardlink_and_tampered_storage_are_refused(self):
        saved = self.upload()
        path = Path(saved['path'])
        alias = self.fixture.base / 'hardlink.png'
        os.link(path, alias)
        self.assertEqual(self.request(saved['url'])[0], 400)
        alias.unlink()
        path.write_bytes(b'not an image')
        self.assertEqual(self.request(saved['url'])[0], 400)
        path.write_bytes(raster())
        manifest = path.with_suffix('.json')
        value = json.loads(manifest.read_text())
        manifest.write_text(json.dumps({**value, 'format': 'SVG'}))
        self.assertEqual(self.request(saved['url'])[0], 400)

    def test_linked_attachment_directory_is_refused(self):
        outside = self.fixture.base / 'external'
        outside.mkdir()
        link = self.fixture.project / '.mb-anexos'
        try:
            link.symlink_to(outside, target_is_directory=True)
        except OSError as error:
            self.skipTest('Symlink indisponível: ' + type(error).__name__)
        try:
            self.assertEqual(self.json(self.url, 'POST', self.body())[0], 400)
            self.assertEqual(list(outside.iterdir()), [])
        finally:
            link.unlink()

    def test_image_only_comment_has_canonical_strings_metadata_and_idempotency(self):
        saved = self.upload()
        body = {'text': ' ', 'target': 'module:summary', 'anexos': [saved]}
        auth = {**self.auth, 'idempotency-key': 'comment_image_attempt_1234'}
        first = self.json(self.comments, 'POST', body, auth)
        second = self.json(self.comments, 'POST', body, auth)
        self.assertEqual(first[0], 200)
        comment = first[2]['comment']
        self.assertEqual(comment['id'], second[2]['comment']['id'])
        self.assertEqual(comment['text'], '')
        self.assertEqual(comment['anexos'], [saved['path']])
        self.assertEqual(comment['attachment_details'], [saved])
        self.assertNotEqual(comment.get('status'), 'CORRIGIDO_VERIFICADO')
        self.assertEqual(self.json(self.comments, 'POST', {'text': ' '})[0], 400)
        self.assertEqual(len(Store(self.fixture.store.path).listing('comments', self.pid)), 1)

    def test_feedback_associations_unique_aggregation_old_version_and_bridge_paths(self):
        one = self.upload()
        two = self.upload(data=raster(color=(1, 2, 3)))
        fid = self.feedback.split('/')[3]
        view = f'/api/reports/{fid}/view?ticket=' + 'a' * 64
        self.assertEqual(self.request(view)[0], 200)
        self.fixture.html.write_text('<h1>Current version</h1>')
        body = {'hash': self.digest, 'note': '', 'anexos': [one], 'feedback': {
            'kind': 'decisions', 'finalizado': True,
            'notas': [{'id': 'note-1', 'texto': '', 'onde': 'mapa', 'anexos': [two]}],
            'respostas': {'q1': {'valor': '', 'anexos': [one, two]}}}}
        auth = {**self.auth, 'idempotency-key': 'feedback_image_attempt_123'}
        first = self.json(self.feedback, 'POST', body, auth)
        second = self.json(self.feedback, 'POST', body, auth)
        self.assertEqual(first[0], 200, first)
        row = first[2]['comment']
        self.assertEqual(row['id'], second[2]['comment']['id'])
        self.assertEqual(row['text'], '')
        self.assertEqual(row['anexos'], [one['path'], two['path']])
        self.assertEqual(row['feedback']['notas'][0]['anexos'], [two['path']])
        self.assertEqual(row['feedback']['respostas']['q1']['anexos'], [one['path'], two['path']])
        self.assertEqual(row['source_hash'], self.digest)
        self.assertTrue(row['versao_anterior'])
        self.assertEqual(row['status'], 'Recebido, aguardando correção')
        from central_bridge import comentario_para_ordem, _texto_comentarios
        bridge = comentario_para_ordem(row)
        self.assertEqual(bridge['anexos'], row['anexos'])
        self.assertIn(Path(one['path']).as_posix(), _texto_comentarios([bridge], self.fixture.project))

    def test_feedback_image_only_and_forged_nested_references(self):
        saved = self.upload()
        body = {'hash': self.digest, 'anexos': [saved]}
        self.assertEqual(self.json(self.feedback, 'POST', body)[0], 200)
        for feedback in [
            {'kind': 'notes', 'notas': [{'anexos': [{**saved, 'path': 'other'}]}]},
            {'kind': 'decisions', 'finalizado': True, 'respostas': {'q': {'anexos': [{**saved, 'url': '/other'}]}}},
        ]:
            self.assertEqual(self.json(self.feedback, 'POST', {'hash': self.digest, 'feedback': feedback})[0], 400)

    def test_six_image_limit_counts_unique_across_the_whole_feedback(self):
        saved = [self.upload(data=raster(color=(i, 20, 30))) for i in range(7)]
        self.assertEqual(self.json(self.comments, 'POST', {'anexos': saved[:6]})[0], 200)
        self.assertEqual(self.json(self.comments, 'POST', {'anexos': saved})[0], 400)
        body = {'hash': self.digest, 'feedback': {'kind': 'notes', 'notas': [
            {'id': '1', 'anexos': saved[:4]}, {'id': '2', 'anexos': saved[4:]}]}}
        self.assertEqual(self.json(self.feedback, 'POST', body)[0], 400)
        body['feedback']['notas'][1]['anexos'] = saved[:4]
        self.assertEqual(self.json(self.feedback, 'POST', body)[0], 200)

    def test_image_only_job_keeps_empty_human_prompt_and_runs_once(self):
        saved = self.upload()
        body = {'prompt': '', 'category': 'codigo', 'anexos': [saved]}
        auth = {**self.auth, 'idempotency-key': 'job_image_attempt_0123456'}
        # Suppress every executor thread: admission is the behavior under test.
        with patch.object(server.threading.Thread, 'start') as start:
            first = self.json(self.jobs, 'POST', body, auth)
            second = self.json(self.jobs, 'POST', body, auth)
        self.assertEqual(first[0], 200, first)
        self.assertEqual(first[2]['job']['id'], second[2]['job']['id'])
        self.assertEqual(start.call_count, 1)
        job = first[2]['job']
        self.assertEqual(job['prompt'], '')
        self.assertEqual(job['title'], 'Pedido com imagem')
        self.assertEqual(job['selected_paths'], [])
        self.assertEqual(job['anexos'], [saved['path']])
        self.assertEqual(self.json(self.jobs, 'POST', {'prompt': ''})[0], 400)


if __name__ == '__main__':
    unittest.main()
