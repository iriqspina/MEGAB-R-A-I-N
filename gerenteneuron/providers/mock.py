"""Provedor mock para validação local sem API keys."""


class MockProvider:
    nome = "Mock (validação local)"

    @staticmethod
    def send(mensagem: str, config: dict | None = None, historico: list | None = None, modelo: str = "mock/validacao-local"):
        resposta = (
            f"GerenteNeuron ativo. Você disse: \"{mensagem}\".\n\n"
            "No momento estou no modo de validação local — nenhuma API externa foi chamada. "
            "Configure as chaves em gerenteneuron/.env para ativar provedores reais."
        )
        return {
            "resposta": resposta,
            "modelo_usado": "mock/validacao-local",
            "provider": "mock",
            "custo_estimado_usd": 0.0,
            "tokens_entrada": len(mensagem.split()),
            "tokens_saida": len(resposta.split()),
        }
