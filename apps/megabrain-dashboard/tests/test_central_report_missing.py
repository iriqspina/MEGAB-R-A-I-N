"""Invalid report links fail as client errors without leaking filesystem paths."""
import hashlib
import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parent))
import test_central_security as harness
from central_reports import confined_file


class MissingReportLinkTests(unittest.TestCase):
    def setUp(self):
        self.fixture=harness.CentralSecurityTests()
        self.fixture.setUp()
        self.auth=self.fixture.local_login()
        asset=self.fixture.sources.index_file(self.fixture.html,self.fixture.project)
        self.endpoint='/api/reports/'+asset['id']+'/resolve'
        self.digest=hashlib.sha256(self.fixture.html.read_bytes()).hexdigest()
        (self.fixture.project/'regular-file.txt').write_text('synthetic file',encoding='utf-8')
        self.paths=['missing-inside.txt','../missing-outside.txt','regular-file.txt/child.txt','.private/missing.txt']

    def tearDown(self):
        self.fixture.tearDown()

    def test_missing_and_invalid_components_are_value_errors(self):
        for value in self.paths:
            with self.subTest(path=value), self.assertRaises(ValueError):
                confined_file(value,self.fixture.project)

    def test_local_and_remote_link_resolution_returns_safe_client_error(self):
        remote_headers={**self.fixture.remote_headers,'cookie':self.auth['cookie'],'x-mb-csrf':self.auth['x-mb-csrf']}
        for app,headers in [(self.fixture.local,self.auth),(self.fixture.remote,remote_headers)]:
            for value in self.paths:
                with self.subTest(remote=app is self.fixture.remote,path=value):
                    status,_,body=self.fixture.request(app,self.endpoint,method='POST',body={'hash':self.digest,'path':value},headers=headers)
                    self.assertIn(status,(400,404))
                    decoded=json.loads(body)
                    self.assertIsInstance(decoded.get('detail'),str)
                    self.assertNotIn(str(self.fixture.project),body.decode())
                    self.assertNotIn(value,body.decode())
                    self.assertNotIn('Traceback',body.decode())


if __name__=='__main__':unittest.main()
