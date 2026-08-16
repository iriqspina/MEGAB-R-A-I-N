"""Cofre local de credenciais do GerenteNeuron.

Usa Fernet (AES-128-CBC + HMAC) com chave derivada de senha via PBKDF2.
A chave mestra de criptografia dos dados é gerada aleatoriamente e armazenada
protegida pela senha do usuário e por uma chave de recuperação.
"""

import base64
import json
import os
import secrets
from pathlib import Path

try:
    from cryptography.fernet import Fernet, InvalidToken
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
except ImportError:
    raise ImportError("cryptography não está instalado. Rode: python gerenteneuron/setup-crypto.py")


RAIZ = Path(__file__).resolve().parent
VAULT_DIR = RAIZ / "vault"
VAULT_FILE = VAULT_DIR / "vault.json"
SALT_FILE = VAULT_DIR / "salt"
RECOVERY_FILE = VAULT_DIR / "recovery.key"


def _garantir_vault_dir():
    VAULT_DIR.mkdir(parents=True, exist_ok=True)


def _derivar_chave(senha: str, salt: bytes) -> bytes:
    """Deriva uma chave Fernet a partir de senha + salt."""
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=600_000,
    )
    return base64.urlsafe_b64encode(kdf.derive(senha.encode("utf-8")))


class Vault:
    def __init__(self):
        self._chave_dados: bytes | None = None  # chave real de criptografia do cofre
        self._dados: dict | None = None

    @property
    def is_desbloqueado(self) -> bool:
        return self._chave_dados is not None

    @staticmethod
    def existe() -> bool:
        return VAULT_FILE.exists() and SALT_FILE.exists()

    def criar(self, senha: str) -> str:
        """Cria cofre vazio. Retorna chave de recuperação (deve ser guardada pelo usuário)."""
        if self.existe():
            raise RuntimeError("Cofre já existe. Use reset ou desbloqueie.")

        _garantir_vault_dir()
        salt = secrets.token_bytes(32)
        chave_dados = Fernet.generate_key()  # chave real dos dados
        chave_recuperacao = secrets.token_urlsafe(32)

        fernet_senha = Fernet(_derivar_chave(senha, salt))
        fernet_recuperacao = Fernet(_derivar_chave(chave_recuperacao, salt))

        envelope = {
            "version": 1,
            "salt": base64.b64encode(salt).decode("ascii"),
            "dados_cifrados": fernet_senha.encrypt(chave_dados).decode("ascii"),
            "recuperacao_cifrada": fernet_recuperacao.encrypt(chave_dados).decode("ascii"),
        }

        VAULT_FILE.write_text(json.dumps(envelope), encoding="utf-8")
        SALT_FILE.write_bytes(salt)
        RECOVERY_FILE.write_text(
            "GUARDE ESTA CHAVE EM LOCAL SEGURO. SEM ELA, NÃO É POSSÍVEL RECUPERAR A SENHA.\n\n"
            + chave_recuperacao
            + "\n",
            encoding="utf-8",
        )

        self._chave_dados = chave_dados
        self._dados = {}
        self._salvar_dados()
        return chave_recuperacao

    def desbloquear(self, senha: str) -> dict:
        if not self.existe():
            raise RuntimeError("Cofre não existe. Rode setup primeiro.")
        envelope = json.loads(VAULT_FILE.read_text(encoding="utf-8"))
        salt = base64.b64decode(envelope["salt"])
        fernet = Fernet(_derivar_chave(senha, salt))
        try:
            self._chave_dados = fernet.decrypt(envelope["dados_cifrados"].encode("ascii"))
        except InvalidToken:
            raise ValueError("Senha incorreta")
        self._carregar_dados()
        return self._dados

    def desbloquear_com_recuperacao(self, chave_recuperacao: str) -> dict:
        if not self.existe():
            raise RuntimeError("Cofre não existe.")
        envelope = json.loads(VAULT_FILE.read_text(encoding="utf-8"))
        salt = base64.b64decode(envelope["salt"])
        fernet = Fernet(_derivar_chave(chave_recuperacao, salt))
        try:
            self._chave_dados = fernet.decrypt(envelope["recuperacao_cifrada"].encode("ascii"))
        except InvalidToken:
            raise ValueError("Chave de recuperação inválida")
        self._carregar_dados()
        return self._dados

    def _carregar_dados(self):
        dados_cifrados = VAULT_DIR / "dados.enc"
        if not dados_cifrados.exists():
            self._dados = {}
            return
        fernet = Fernet(self._chave_dados)
        try:
            self._dados = json.loads(fernet.decrypt(dados_cifrados.read_bytes()).decode("utf-8"))
        except InvalidToken:
            raise ValueError("Dados corrompidos ou chave errada")

    def _salvar_dados(self):
        if self._chave_dados is None:
            raise RuntimeError("Cofre não desbloqueado")
        fernet = Fernet(self._chave_dados)
        (VAULT_DIR / "dados.enc").write_bytes(
            fernet.encrypt(json.dumps(self._dados, ensure_ascii=False).encode("utf-8")),
        )

    def get(self, chave: str, padrao=None):
        if self._dados is None:
            raise RuntimeError("Cofre não desbloqueado")
        return self._dados.get(chave, padrao)

    def set(self, chave: str, valor):
        if self._dados is None:
            raise RuntimeError("Cofre não desbloqueado")
        self._dados[chave] = valor
        self._salvar_dados()

    def remover(self, chave: str):
        if self._dados is None:
            raise RuntimeError("Cofre não desbloqueado")
        if chave in self._dados:
            del self._dados[chave]
            self._salvar_dados()

    def listar(self) -> list[str]:
        if self._dados is None:
            raise RuntimeError("Cofre não desbloqueado")
        return sorted(self._dados.keys())

    def exportar_env(self) -> dict[str, str]:
        """Exporta credenciais como dict chave=valor para uso em .env/memória."""
        if self._dados is None:
            raise RuntimeError("Cofre não desbloqueado")
        return {k: str(v) for k, v in self._dados.items()}

    def alterar_senha(self, senha_atual: str, nova_senha: str):
        self.desbloquear(senha_atual)
        envelope = json.loads(VAULT_FILE.read_text(encoding="utf-8"))
        salt = base64.b64decode(envelope["salt"])
        fernet_nova = Fernet(_derivar_chave(nova_senha, salt))
        envelope["dados_cifrados"] = fernet_nova.encrypt(self._chave_dados).decode("ascii")
        VAULT_FILE.write_text(json.dumps(envelope), encoding="utf-8")

    def redefinir_senha_com_recuperacao(self, chave_recuperacao: str, nova_senha: str):
        self.desbloquear_com_recuperacao(chave_recuperacao)
        envelope = json.loads(VAULT_FILE.read_text(encoding="utf-8"))
        salt = base64.b64decode(envelope["salt"])
        fernet_nova = Fernet(_derivar_chave(nova_senha, salt))
        envelope["dados_cifrados"] = fernet_nova.encrypt(self._chave_dados).decode("ascii")
        VAULT_FILE.write_text(json.dumps(envelope), encoding="utf-8")
        # Gera nova chave de recuperação também, pois a antiga foi usada.
        nova_chave_recuperacao = secrets.token_urlsafe(32)
        fernet_recuperacao = Fernet(_derivar_chave(nova_chave_recuperacao, salt))
        envelope["recuperacao_cifrada"] = fernet_recuperacao.encrypt(self._chave_dados).decode("ascii")
        VAULT_FILE.write_text(json.dumps(envelope), encoding="utf-8")
        RECOVERY_FILE.write_text(
            "GUARDE ESTA CHAVE EM LOCAL SEGURO. SEM ELA, NÃO É POSSÍVEL RECUPERAR A SENHA.\n\n"
            + nova_chave_recuperacao
            + "\n",
            encoding="utf-8",
        )
        return nova_chave_recuperacao
