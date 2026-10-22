"""Catálogo do despacho coerente com a linguagem real de cada vendor (261020).

Comentário do <USUARIO> no painel "Enviar pro terminal": faltavam efforts do
Codex e as listas não seguiam a nomenclatura dos vendors. Este teste prende o
CATALOG do servidor ao espelho do seletor (motor/modelos/interacoes) e às
fontes locais batidas em 20/10/2026, para a deriva não voltar calada.
"""
import re
import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from central_dispatch import CATALOG, validar, _linha_cli  # noqa: E402

RAIZ = Path(__file__).resolve().parents[3]
JS = RAIZ / 'motor' / 'modelos' / 'interacoes' / '261010_decisoes-respondiveis' / 'decisoes-respondiveis.js'
RELATORIO = RAIZ / '00_PARA-VOCE' / '261020_cotas-mapa-bapp' / '261020_RELATORIO.html'


def _ias_do_js():
    texto = JS.read_text(encoding='utf-8')
    bloco = re.search(r'var IAS = \{\n(.*?)\n  \};', texto, re.S)
    if not bloco:
        raise AssertionError('var IAS não encontrado no JS do motor')
    ias = {}
    for linha in re.finditer(r"(\w+): \{ nome: '([^']+)', modelos: \[([^\]]*)\], efforts: \[([^\]]*)\](.*?)\}(?:,|$)", bloco.group(1)):
        chave, nome, modelos, efforts, resto = linha.groups()
        nota = re.search(r"nota: '([^']*)'", resto)
        ias[chave] = {
            'nome': nome,
            'modelos': [v.strip().strip("'") for v in modelos.split(',') if v.strip()],
            'efforts': [v.strip().strip("'") for v in efforts.split(',') if v.strip()],
            'nota': nota.group(1) if nota else None,
        }
    if not ias:
        raise AssertionError('nenhuma IA lida do var IAS do JS do motor')
    return ias


def _ias_do_html():
    """Cópia inline entregue ao <USUARIO> precisa seguir o mesmo catálogo."""
    if not RELATORIO.is_file():
        raise unittest.SkipTest('relatório 261020 fora do lugar; proteger quando existir')
    texto = RELATORIO.read_text(encoding='utf-8')
    bloco = re.search(r'var IAS = \{\r?\n(.*?)\r?\n  \};', texto, re.S)
    if not bloco:
        raise AssertionError('var IAS inline não encontrado no relatório entregue')
    ias = {}
    for linha in re.finditer(r"(\w+): \{ nome: '([^']+)', modelos: \[([^\]]*)\], efforts: \[([^\]]*)\](.*?)\}(?:,|$)", bloco.group(1)):
        chave, _nome, modelos, efforts, _resto = linha.groups()
        ias[chave] = {
            'modelos': [v.strip().strip("'") for v in modelos.split(',') if v.strip()],
            'efforts': [v.strip().strip("'") for v in efforts.split(',') if v.strip()],
        }
    if not ias:
        raise AssertionError('nenhuma IA lida do var IAS inline do relatório')
    return ias


class CatalogoConsistente(unittest.TestCase):
    def setUp(self):
        self.js = _ias_do_js()

    def test_mesmas_ias_no_catalogo_e_no_seletor(self):
        self.assertEqual(set(CATALOG), set(self.js), 'CATALOG e var IAS divergem em quais IAs existem')

    def test_modelos_e_efforts_iguais_por_ia(self):
        for ia, entrada in CATALOG.items():
            espelho = self.js[ia]
            self.assertEqual(entrada['modelos'], espelho['modelos'], f'modelos de {ia} divergem do seletor')
            self.assertEqual(entrada['efforts'], espelho['efforts'], f'efforts de {ia} divergem do seletor')

    def test_copia_inline_do_relatorio_entregue_igual_ao_catalogo(self):
        html = _ias_do_html()
        self.assertEqual(set(CATALOG), set(html), 'var IAS inline do relatório diverge em quais IAs existem')
        for ia, entrada in CATALOG.items():
            self.assertEqual(entrada['modelos'], html[ia]['modelos'], f'modelos de {ia} divergem no relatório entregue')
            self.assertEqual(entrada['efforts'], html[ia]['efforts'], f'efforts de {ia} divergem no relatório entregue')

    def test_kimi_fora_deixa_de_ser_despachavel(self):
        self.assertNotIn('kimi', CATALOG)
        self.assertNotIn('kimi', self.js)
        with mock.patch('central_dispatch.shutil.which', lambda _n: 'x'):
            with self.assertRaisesRegex(ValueError, 'desconhecida'):
                validar({'ia': 'kimi'})


class ZcodeBatido(unittest.TestCase):
    """Fonte: zcode --help 0.16.9 (--model provider/model) + registro local."""

    def test_modelos_do_plano_disponiveis(self):
        modelos = CATALOG['zcode']['modelos']
        self.assertIn('zai/GLM-5.3', modelos)
        self.assertIn('zai/GLM-5.3-Flash', modelos)

    def test_linha_cli_zcode_com_modelo_antes_do_prompt(self):
        linha = _linha_cli('zcode', 'zai/GLM-5.3-Flash', '—', '$PROMPT', 'p')
        self.assertIn('--model zai/GLM-5.3-Flash -p', linha)
        sem_modelo = _linha_cli('zcode', 'padrão', '—', '$PROMPT', 'p')
        self.assertNotIn('--model', sem_modelo)

    def test_validar_aceita_provider_barra_modelo(self):
        with mock.patch('central_dispatch.shutil.which', lambda _n: 'x'):
            self.assertEqual(
                validar({'ia': 'zcode', 'modelo': 'zai/GLM-5.3'}),
                ('zcode', 'zai/GLM-5.3', 'padrão'),
            )


class CodexBatido(unittest.TestCase):
    """Fonte: enabled-reasoning-efforts do ~/.codex/config.toml (codex 0.163)."""

    def test_ultra_e_max_presentes_minimal_fora(self):
        efforts = CATALOG['codex']['efforts']
        self.assertIn('ultra', efforts)
        self.assertIn('max', efforts)
        self.assertNotIn('minimal', efforts)

    def test_validar_aceita_ultra_e_rejeita_minimal(self):
        with mock.patch('central_dispatch.shutil.which', lambda _n: 'x'):
            self.assertEqual(validar({'ia': 'codex', 'effort': 'ultra'}), ('codex', 'padrão', 'ultra'))
            with self.assertRaisesRegex(ValueError, 'Effort'):
                validar({'ia': 'codex', 'effort': 'minimal'})

    def test_linha_cli_codex_com_ultra(self):
        linha = _linha_cli('codex', 'padrão', 'ultra', '$PROMPT', 'p')
        self.assertIn('model_reasoning_effort="ultra"', linha)


class ClaudeBatido(unittest.TestCase):
    """Fonte: claude --help 2.1.302 (--effort low..max; --model aceita fable)."""

    def test_efforts_xhigh_e_max(self):
        efforts = CATALOG['claude']['efforts']
        self.assertIn('xhigh', efforts)
        self.assertIn('max', efforts)
        self.assertNotIn('minimal', efforts)

    def test_modelo_fable_disponivel(self):
        self.assertIn('fable', CATALOG['claude']['modelos'])

    def test_linha_cli_claude_com_xhigh(self):
        linha = _linha_cli('claude', 'fable', 'xhigh', '$PROMPT', 'p')
        self.assertIn('--model fable', linha)
        self.assertIn('--effort xhigh', linha)


if __name__ == '__main__':
    unittest.main()
