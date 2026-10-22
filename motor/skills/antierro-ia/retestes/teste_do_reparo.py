import importlib.util, pathlib, unittest

spec = importlib.util.spec_from_file_location("r", pathlib.Path(__file__).parent / "reparo_buggy.py")
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class T(unittest.TestCase):
    def test_sem_diferenca_devolve_vazio(self):
        est = {"a": 1}
        self.assertEqual(m.resumo(est, dict(est)), [],
                         "reparo de verdade devolve [] (rotulo de regeracao fica em quem chama)")


if __name__ == "__main__":
    unittest.main()
