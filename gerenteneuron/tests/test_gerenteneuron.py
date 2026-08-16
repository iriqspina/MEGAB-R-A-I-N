#!/usr/bin/env python3
"""Testes do GerenteNeuron — stdlib pura, sem pytest.

    python tests/test_gerenteneuron.py

Regra do megabrain: garantia real é script, não markdown. O corolário da
auditoria v5.1 é que script sem teste é markdown com extensão .py — o app
inteiro estava nessa condição. Cada caso aqui falha contra a versão anterior.
"""

import json
import os
import sys
import unittest
from datetime import date
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

import precos  # noqa: E402
import router  # noqa: E402
import gerente  # noqa: E402
from providers.base import estimar_tokens_por_palavras, historico_para_openai  # noqa: E402


class TestPricing(unittest.TestCase):
    """pricing.json é a fonte única — se ele quebra, o roteamento mente."""

    def test_arquivo_valido_e_completo(self):
        for m in precos.modelos():
            for campo in ("provider", "api_id", "nome", "classe", "in", "out"):
                self.assertIn(campo, m, f"{m.get('api_id')} sem campo {campo}")
            self.assertIn(m["classe"], ("quick", "standard", "deep"), m["api_id"])
            self.assertGreaterEqual(m["in"], 0)
            self.assertGreaterEqual(m["out"], 0)

    def test_sem_id_duplicado(self):
        ids = [(m["provider"], m["api_id"]) for m in precos.modelos()]
        self.assertEqual(len(ids), len(set(ids)), "modelo duplicado em pricing.json")

    def test_toda_classe_tem_pelo_menos_um_modelo_pago(self):
        for classe in ("quick", "standard", "deep"):
            pagos = [m for m in precos.modelos()
                     if m["classe"] == classe and m.get("fonte") != "local"]
            self.assertTrue(pagos, f"classe {classe} sem modelo pago — fila cai direto no mock")

    def test_custo_usa_a_tabela_e_nao_zero(self):
        custo = precos.custo("anthropic", "claude-sonnet-5", 1_000_000, 1_000_000)
        m = precos.buscar("anthropic", "claude-sonnet-5")
        esperado = (m["in"] + m["out"]) * m.get("fator_token", 1.0)
        self.assertAlmostEqual(custo, esperado, places=6)

    def test_custo_de_modelo_desconhecido_nao_explode(self):
        self.assertEqual(precos.custo("inexistente", "nada", 1000, 1000), 0.0)

    def test_fila_por_classe_vem_ordenada_do_mais_barato(self):
        fila = precos.fila_por_classe("standard")
        self.assertTrue(fila)
        custos = [precos.custo_ponderado(precos.buscar(p, m)) for p, m in fila]
        self.assertEqual(custos, sorted(custos), "fila não está ordenada por custo")

    def test_validade_da_tabela_e_detectada(self):
        cfg = precos.carregar()
        verificado = date.fromisoformat(cfg["verificado_em"])
        dias = cfg.get("revalidar_em_dias", 60)
        self.assertFalse(precos.esta_vencida(verificado))
        futuro = date.fromordinal(verificado.toordinal() + dias + 1)
        self.assertTrue(precos.esta_vencida(futuro))
        self.assertIsNotNone(precos.aviso_validade(futuro))


class TestClassificador(unittest.TestCase):
    """A normalização é o conserto: sem ela, várias regras nunca disparavam."""

    def test_pontuacao_nao_impede_o_casamento(self):
        self.assertEqual(router.classificar_estrategia("faz uma auditoria?"), "deep")

    def test_acento_nao_impede_o_casamento(self):
        self.assertEqual(router.classificar_estrategia("preciso de uma decisão"), "deep")

    def test_termo_de_duas_palavras_dispara(self):
        # Contra o código anterior (set de palavras) isto retornava 'cheap'.
        self.assertEqual(router.classificar_estrategia("olha esse design system"), "deep")
        self.assertEqual(router.classificar_estrategia("o que e isso"), "cheap")

    def test_codigo_vai_para_rota_local(self):
        self.assertEqual(router.classificar_estrategia("tem um bug no script"), "local_code")

    def test_mensagem_longa_vira_deep(self):
        self.assertEqual(router.classificar_estrategia("a" * 1300), "deep")

    def test_termo_nao_casa_dentro_de_outra_palavra(self):
        # 'api' não pode disparar dentro de 'rapidez'.
        self.assertNotEqual(router.classificar_estrategia("rapidez"), "local_code")


class TestFilaDoRoteador(unittest.TestCase):
    def _cfg(self, **keys):
        provs = {}
        for pid in ("openai", "anthropic", "gemini", "moonshot"):
            provs[pid] = {"nome": pid, "key": keys.get(pid), "local": False, "modelos": []}
        provs["ollama"] = {"nome": "ollama", "key": None, "local": True, "modelos": []}
        provs["mock"] = {"nome": "mock", "key": "mock", "local": True, "modelos": []}
        return {"providers": provs, "modo": "auto"}

    def test_sem_key_a_fila_cai_no_mock(self):
        fila = router.montar_fila(self._cfg(), "deep")
        self.assertEqual(fila[-1], ("mock", "mock/validacao-local"))
        pagos = [f for f in fila if f[0] in ("openai", "anthropic", "gemini", "moonshot")]
        self.assertFalse(pagos, "provedor sem key entrou na fila")

    def test_fila_respeita_ordem_de_preco(self):
        fila = router.montar_fila(self._cfg(openai="k", anthropic="k", gemini="k", moonshot="k"), "deep")
        pagos = [(p, m) for p, m in fila if p != "mock"]
        custos = [precos.custo_ponderado(precos.buscar(p, m)) for p, m in pagos]
        self.assertEqual(custos, sorted(custos))

    def test_local_code_tenta_o_local_antes_do_pago(self):
        fila = router.montar_fila(self._cfg(openai="k", anthropic="k"), "local_code")
        self.assertEqual(fila[0][0], "ollama", "rota de código não priorizou o modelo local")

    def test_fila_nao_repete_candidato(self):
        fila = router.montar_fila(self._cfg(openai="k"), "local_code")
        self.assertEqual(len(fila), len(set(fila)))

    def test_boost_sobe_de_classe(self):
        self.assertEqual(router.BOOST_DE["cheap"], "standard")
        self.assertEqual(router.BOOST_DE["standard"], "deep")
        self.assertEqual(router.BOOST_DE["deep"], "deep", "boost em deep não pode ciclar")


class TestHistorico(unittest.TestCase):
    """O bug mais caro: o chat não tinha memória nenhuma."""

    def test_provider_recebe_o_historico(self):
        capturado = {}

        class Espiao:
            @staticmethod
            def send(mensagem, config, historico=None, modelo=""):
                capturado["historico"] = historico
                return {"resposta": "ok", "provider": "espiao", "modelo_usado": modelo}

        original = router.PROVIDERS.get("mock")
        router.PROVIDERS["mock"] = Espiao
        try:
            hist = [{"role": "user", "content": "meu nome é Iriq"}]
            router._executar_fila(
                "qual é meu nome?",
                {"providers": {"mock": {"key": "mock", "local": True}}},
                [("mock", "x")], "auto", "cheap", hist,
            )
        finally:
            router.PROVIDERS["mock"] = original

        self.assertEqual(capturado["historico"], hist,
                         "route descartava o histórico — o chat respondia sem memória")

    def test_historico_vira_mensagens_na_ordem_certa(self):
        msgs = historico_para_openai(
            [{"role": "user", "content": "oi"}, {"role": "assistant", "content": "olá"}],
            "e agora?",
        )
        self.assertEqual([m["role"] for m in msgs], ["user", "assistant", "user"])
        self.assertEqual(msgs[-1]["content"], "e agora?")

    def test_historico_ignora_papel_invalido_e_vazio(self):
        msgs = historico_para_openai(
            [{"role": "hacker", "content": "x"}, {"role": "user", "content": ""}],
            "oi",
        )
        self.assertEqual(len(msgs), 1)


class TestTokens(unittest.TestCase):
    def test_estimativa_bate_com_a_constante_documentada(self):
        # Antes: docstring dizia 0.75 e o código multiplicava por 1.0.
        from providers.base import TOKENS_POR_PALAVRA_PT
        texto = "uma frase com seis palavras aqui"
        esperado = int(len(texto.split()) * TOKENS_POR_PALAVRA_PT)
        self.assertEqual(estimar_tokens_por_palavras(texto), esperado)

    def test_texto_vazio_nao_da_zero(self):
        self.assertGreaterEqual(estimar_tokens_por_palavras(""), 1)


class TestGerente(unittest.TestCase):
    def test_projeto_sem_campos_nao_derruba(self):
        projetos = [{"keywords": ["portfolio"]}, {"id": "x", "nome": "X", "keywords": []}]
        self.assertIsNotNone(gerente.identificar_projeto("mexer no portfolio", projetos))

    def test_sem_evidencia_nao_chuta_projeto(self):
        projetos = [{"id": "a", "nome": "A", "keywords": ["zzz"]}]
        self.assertIsNone(gerente.identificar_projeto("bom dia", projetos))

    def test_intencao_de_status(self):
        self.assertEqual(gerente.identificar_intencao("onde estamos no projeto"), "status")


class TestOrigem(unittest.TestCase):
    """Sem esta checagem, qualquer site aberto no navegador falava com a API."""

    def _handler(self, headers):
        from app import APIHandler

        class Fake(APIHandler):
            def __init__(self):
                self.headers = headers

        return Fake()

    def test_origem_externa_e_recusada(self):
        h = self._handler({"Host": "127.0.0.1:8787", "Origin": "https://site-qualquer.com"})
        self.assertFalse(h._origem_confiavel())

    def test_origem_local_e_aceita(self):
        h = self._handler({"Host": "127.0.0.1:8787", "Origin": "http://localhost:8787"})
        self.assertTrue(h._origem_confiavel())

    def test_sem_origin_e_aceito(self):
        self.assertTrue(self._handler({"Host": "127.0.0.1:8787"})._origem_confiavel())

    def test_host_estranho_e_recusado(self):
        # Defesa contra DNS rebinding: nome externo resolvendo para 127.0.0.1.
        h = self._handler({"Host": "malicioso.example.com:8787"})
        self.assertFalse(h._origem_confiavel())


class TestVault(unittest.TestCase):
    def test_extrai_chave_do_arquivo_colado_inteiro(self):
        try:
            import vault
        except ImportError:
            self.skipTest("cryptography não instalado neste ambiente")
        conteudo = vault.CABECALHO_RECUPERACAO + "abc123-chave-de-teste\n"
        self.assertEqual(vault.extrair_chave_recuperacao(conteudo), "abc123-chave-de-teste")
        self.assertEqual(vault.extrair_chave_recuperacao("abc123-chave-de-teste"), "abc123-chave-de-teste")
        self.assertEqual(vault.extrair_chave_recuperacao(""), "")


class TestCofreCriado(unittest.TestCase):
    """Ciclo real do cofre em pasta temporária — inclusive onde a chave cai."""

    def setUp(self):
        try:
            import vault
        except ImportError:
            self.skipTest("cryptography não instalado neste ambiente")
        import tempfile
        self.vault = vault
        self.tmp = tempfile.TemporaryDirectory()
        base = Path(self.tmp.name)
        self._orig = (vault.VAULT_DIR, vault.VAULT_FILE, vault.SALT_FILE, vault.RECOVERY_FILE)
        vault.VAULT_DIR = base / "vault"
        vault.VAULT_FILE = vault.VAULT_DIR / "vault.json"
        vault.SALT_FILE = vault.VAULT_DIR / "salt"
        vault.RECOVERY_FILE = vault.VAULT_DIR / "recovery.key"
        self.destino = base / "fora" / "chave.txt"

    def tearDown(self):
        (self.vault.VAULT_DIR, self.vault.VAULT_FILE,
         self.vault.SALT_FILE, self.vault.RECOVERY_FILE) = self._orig
        self.tmp.cleanup()

    def test_chave_de_recuperacao_nao_fica_na_pasta_do_cofre(self):
        v = self.vault.Vault()
        chave, caminho = v.criar("senha-de-teste", destino_recuperacao=self.destino)
        self.assertEqual(caminho, self.destino)
        self.assertTrue(caminho.exists())
        self.assertFalse(self.vault.RECOVERY_FILE.exists(),
                         "chave de recuperação voltou para dentro do cofre")
        self.assertNotIn(self.vault.VAULT_DIR.resolve(), caminho.resolve().parents)
        self.assertIn(chave, caminho.read_text(encoding="utf-8"))

    def test_pasta_do_cofre_continua_gravavel_apos_restringir(self):
        # 0600 numa pasta tira o bit de travessia: o cofre não nasce.
        # Só falha para usuário sem privilégio — root ignora a checagem.
        v = self.vault.Vault()
        v.criar("senha-de-teste", destino_recuperacao=self.destino)
        modo = self.vault.VAULT_DIR.stat().st_mode & 0o777
        self.assertTrue(modo & 0o100, f"pasta do cofre sem bit de execução: {oct(modo)}")
        v.set("CHAVE_NOVA", "valor")  # precisa conseguir escrever depois
        self.assertEqual(v.get("CHAVE_NOVA"), "valor")
        dados = self.vault.VAULT_DIR / "dados.enc"
        self.assertEqual(dados.stat().st_mode & 0o077, 0, "dados.enc legível por outros")

    def test_destino_padrao_fica_fora_do_app(self):
        padrao = self.vault.destino_padrao_recuperacao().resolve()
        self.assertNotIn(self.vault.RAIZ.resolve(), padrao.parents)

    def test_senha_certa_abre_e_errada_nao(self):
        v = self.vault.Vault()
        v.criar("senha-de-teste", destino_recuperacao=self.destino)
        v.set("OPENAI_API_KEY", "sk-abc")

        outro = self.vault.Vault()
        with self.assertRaises(ValueError):
            outro.desbloquear("senha-errada")
        outro.desbloquear("senha-de-teste")
        self.assertEqual(outro.get("OPENAI_API_KEY"), "sk-abc")

    def test_recuperacao_preserva_dados_e_queima_a_chave_antiga(self):
        v = self.vault.Vault()
        chave, caminho = v.criar("senha-antiga", destino_recuperacao=self.destino)
        v.set("ANTHROPIC_API_KEY", "sk-ant-xyz")

        outro = self.vault.Vault()
        # Aceita o arquivo colado inteiro, com cabeçalho de aviso.
        outro.redefinir_senha_com_recuperacao(caminho.read_text(encoding="utf-8"), "senha-nova")

        terceiro = self.vault.Vault()
        terceiro.desbloquear("senha-nova")
        self.assertEqual(terceiro.get("ANTHROPIC_API_KEY"), "sk-ant-xyz")

        quarto = self.vault.Vault()
        with self.assertRaises(ValueError):
            quarto.desbloquear_com_recuperacao(chave)  # a antiga foi queimada

    def test_aviso_dispara_so_quando_a_chave_esta_dentro_do_cofre(self):
        v = self.vault.Vault()
        v.criar("senha-de-teste", destino_recuperacao=self.destino)
        self.assertIsNone(self.vault.aviso_recuperacao_exposta())
        self.vault.RECOVERY_FILE.write_text("chave-antiga", encoding="utf-8")
        self.assertIsNotNone(self.vault.aviso_recuperacao_exposta())


class TestProjetosJson(unittest.TestCase):
    def test_projetos_json_e_valido_se_existir(self):
        caminho = RAIZ / "projetos.json"
        if not caminho.exists():
            self.skipTest("projetos.json não existe (normal em instalação nova)")
        dados = json.loads(caminho.read_text(encoding="utf-8"))
        for p in dados.get("projetos", []):
            for campo in ("id", "nome", "skill", "keywords"):
                self.assertIn(campo, p, f"projeto {p.get('id')} sem campo {campo}")


if __name__ == "__main__":
    os.environ.pop("OPENAI_API_KEY", None)
    unittest.main(verbosity=2)
