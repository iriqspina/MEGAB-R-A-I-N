"""Cofre local de credenciais do GerenteNeuron.

Usa Fernet (AES-128-CBC + HMAC) com chave derivada de senha via PBKDF2.
A chave mestra de criptografia dos dados é gerada aleatoriamente e armazenada
protegida pela senha do usuário e por uma chave de recuperação.
"""

import base64
import json
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


CABECALHO_RECUPERACAO = (
    "CHAVE DE RECUPERACAO DO COFRE DO GERENTENEURON\n"
    "Sem ela, esquecer a senha mestre significa perder as credenciais.\n"
    "NUNCA guarde este arquivo na pasta do cofre: quem tem os dois nao precisa\n"
    "da senha. Lugar certo: pendrive, gerenciador de senhas ou drive pessoal.\n\n"
)


def destino_padrao_recuperacao() -> Path:
    """Fora da pasta do app, por padrão.

    Gravar a chave de recuperação ao lado do cofre anula a senha mestre para
    quem tem acesso ao disco. O padrão precisa ser o seguro, porque ninguém
    move arquivo depois — o default é o que fica.
    """
    return Path.home() / "gerenteneuron-chave-de-recuperacao.txt"


def _restringir(caminho: Path):
    """Permissão só para o dono. Diretório precisa do bit de execução.

    0600 numa pasta tira o bit de travessia e impede criar arquivo lá dentro —
    o cofre não nascia. Passou despercebido porque root ignora a checagem.
    """
    try:
        caminho.chmod(0o700 if caminho.is_dir() else 0o600)
    except OSError:
        pass


def _garantir_vault_dir():
    VAULT_DIR.mkdir(parents=True, exist_ok=True)
    _restringir(VAULT_DIR)


def extrair_chave_recuperacao(bruto: str) -> str:
    """Aceita a chave crua ou o conteúdo inteiro do recovery.key.

    O arquivo é gravado com um cabeçalho de aviso; quem colava o arquivo todo
    recebia 'chave inválida' sem entender por quê.
    """
    linhas = [l.strip() for l in (bruto or "").splitlines() if l.strip()]
    return linhas[-1] if linhas else ""


def recuperacao_esta_exposta() -> bool:
    """True quando existe chave de recuperação dentro da pasta do cofre.

    Instalação antiga gravava ali. Quem tem a pasta tem cofre e chave juntos —
    a senha mestre vira decoração.
    """
    return RECOVERY_FILE.exists()


def aviso_recuperacao_exposta() -> str | None:
    if not recuperacao_esta_exposta():
        return None
    return (
        f"RISCO: {RECOVERY_FILE} está dentro da pasta do cofre. Quem tem acesso "
        f"ao disco abre o cofre sem a senha. Mova para {destino_padrao_recuperacao()} "
        f"ou para um pendrive e apague o original."
    )


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

    def criar(self, senha: str, destino_recuperacao: Path | None = None) -> tuple[str, Path]:
        """Cria cofre vazio.

        Retorna (chave_de_recuperacao, caminho_onde_foi_gravada). O padrão é a
        pasta pessoal do usuário, nunca `vault/`.
        """
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
        _restringir(VAULT_FILE)
        _restringir(SALT_FILE)
        destino = Path(destino_recuperacao) if destino_recuperacao else destino_padrao_recuperacao()
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_text(CABECALHO_RECUPERACAO + chave_recuperacao + "\n", encoding="utf-8")
        _restringir(destino)

        self._chave_dados = chave_dados
        self._dados = {}
        self._salvar_dados()
        return chave_recuperacao, destino

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
        chave_recuperacao = extrair_chave_recuperacao(chave_recuperacao)
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
        alvo = VAULT_DIR / "dados.enc"
        alvo.write_bytes(
            fernet.encrypt(json.dumps(self._dados, ensure_ascii=False).encode("utf-8")),
        )
        _restringir(alvo)

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
        # A chave de recuperação antiga foi consumida; gera outra no mesmo passo.
        nova_chave_recuperacao = secrets.token_urlsafe(32)
        fernet_recuperacao = Fernet(_derivar_chave(nova_chave_recuperacao, salt))
        envelope["recuperacao_cifrada"] = fernet_recuperacao.encrypt(self._chave_dados).decode("ascii")
        VAULT_FILE.write_text(json.dumps(envelope), encoding="utf-8")
        destino = destino_padrao_recuperacao()
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_text(CABECALHO_RECUPERACAO + nova_chave_recuperacao + "\n", encoding="utf-8")
        _restringir(destino)
        self.destino_recuperacao = destino
        return nova_chave_recuperacao
