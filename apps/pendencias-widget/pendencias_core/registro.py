"""Registro de pendências — CRUD atômico sobre dados/pendencias.json.

Contrato (v1):
- Escrito SOMENTE por este módulo (via bin/mb-pendencias.py). O widget lê.
- Escrita atômica (tmp validado + replace); `.bak` nunca é sobrescrito por
  conteúdo não validado (lição da revisão gpt2 260916: recuperar de um
  principal corrompido e salvar de novo destruía o backup).
- Comandos que alteram o registro rodam sob trava de arquivo (dois CLIs
  simultâneos não perdem escrita).
- Campos desconhecidos são preservados. "Pausar" projeto nunca apaga nada.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import secrets
import tempfile
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

VERSAO = 1

ITEM_ABERTA = "aberta"
ITEM_FEITA = "feita"
ITEM_REMOVIDA = "removida"
_ESTADOS_ITEM = {ITEM_ABERTA, ITEM_FEITA, ITEM_REMOVIDA}


def agora_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def _normalizar(texto: str) -> str:
    return re.sub(r"\s+", " ", (texto or "").strip())


def sem_acento(texto: str) -> str:
    trocas = str.maketrans("áàâãäéèêëíìîïóòôõöúùûüçñÁÀÂÃÄÉÈÊËÍÌÎÏÓÒÔÕÖÚÙÛÜÇÑ",
                           "aaaaaeeeeiiiiooooouuuucnAAAAAEEEEIIIIOOOOOUUUUCN")
    return (texto or "").translate(trocas).casefold()


class ErroRegistro(ValueError):
    pass


class ErroNaoEncontrado(ErroRegistro):
    """Projeto/item inexistente — pode virar criação; ambiguidade não."""


@contextmanager
def trava(caminho: Path):
    """Trava exclusiva entre processos para a sequência carregar→alterar→salvar."""
    lock = Path(str(caminho) + ".lock")
    lock.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(str(lock), os.O_CREAT | os.O_RDWR)
    try:
        try:
            import msvcrt

            limite = datetime.now().timestamp() + 5
            while True:
                try:
                    msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
                    break
                except OSError:
                    if datetime.now().timestamp() > limite:
                        raise ErroRegistro("outra escrita do registro em andamento")
                    import time

                    time.sleep(0.1)
        except ImportError:  # não-Windows: best effort
            pass
        yield
    finally:
        try:
            import msvcrt

            msvcrt.locking(fd, msvcrt.LK_UNLCK, 1)
        except (ImportError, OSError):
            pass
        os.close(fd)


def vazio(raiz: str = "") -> dict:
    return {"versao": VERSAO, "raiz": raiz, "projetos": [], "atualizado_em": agora_iso()}


def _validar(dados: dict) -> None:
    if not isinstance(dados, dict):
        raise ErroRegistro("registro nao e um objeto")
    if dados.get("versao") != VERSAO:
        raise ErroRegistro(f"versao incompativel: {dados.get('versao')!r} (esperada {VERSAO})")
    if not isinstance(dados.get("projetos"), list):
        raise ErroRegistro("campo 'projetos' ausente ou nao e lista")
    for p in dados["projetos"]:
        if not isinstance(p, dict) or not isinstance(p.get("nome"), str) or not p["nome"].strip():
            raise ErroRegistro("projeto sem nome valido")
        if not isinstance(p.get("itens", []), list):
            raise ErroRegistro(f"itens de {p.get('nome')!r} nao e lista")
        for i in p.get("itens", []):
            if not isinstance(i, dict) or not isinstance(i.get("titulo"), str) or not i["titulo"].strip():
                raise ErroRegistro(f"item invalido em {p['nome']!r}: {i!r}")
            if not isinstance(i.get("id"), str):
                raise ErroRegistro(f"item sem id em {p['nome']!r}")
            if i.get("estado") not in _ESTADOS_ITEM:
                raise ErroRegistro(f"estado invalido em item de {p['nome']!r}: {i.get('estado')!r}")


class Registro:
    """Fachada de leitura/escrita com recuperação pela última cópia válida."""

    def __init__(self, caminho: Path):
        self.caminho = Path(caminho)
        self.dados: dict = vazio()

    # -- io ---------------------------------------------------------------

    def _bak_path(self) -> Path:
        return self.caminho.with_suffix(self.caminho.suffix + ".bak")

    def _ler(self, caminho: Path) -> dict:
        try:
            dados = json.loads(caminho.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as e:
            raise ErroRegistro(f"{caminho.name} ilegivel: {e.__class__.__name__}") from e
        _validar(dados)
        return dados

    def carregar(self, obrigatorio: bool = False) -> "Registro":
        principal_ok = self.caminho.exists()
        if principal_ok:
            try:
                self.dados = self._ler(self.caminho)
                return self
            except ErroRegistro:
                pass  # cai pro backup
        if self._bak_path().exists():
            self.dados = self._ler(self._bak_path())  # ambos ruins => ErroRegistro sobe
            return self
        if principal_ok:
            raise ErroRegistro(f"{self.caminho.name} e o backup estao ilegiveis")
        if obrigatorio:
            raise ErroRegistro(f"registro inexistente: {self.caminho}")
        self.dados = vazio()
        return self

    def salvar(self) -> None:
        _validar(self.dados)
        self.dados["atualizado_em"] = agora_iso()
        self.caminho.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=str(self.caminho.parent), suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(self.dados, f, ensure_ascii=False, indent=2)
            self._ler(Path(tmp))  # valida o que foi escrito antes de instalar
            # .bak só recebe bytes VALIDADOS: se o principal atual está são,
            # vira a cópia; se está corrompido, o .bak bom fica intocado até
            # o replace — e então é renovado a partir do novo conteúdo válido.
            if self.caminho.exists():
                try:
                    self._ler(self.caminho)
                    self._bak_path().write_bytes(self.caminho.read_bytes())
                except (ErroRegistro, OSError):
                    pass
            os.replace(tmp, self.caminho)  # principal sempre trocado por conteúdo válido
            try:
                self._bak_path().write_bytes(self.caminho.read_bytes())
            except OSError:
                pass
        finally:
            if os.path.exists(tmp):
                os.unlink(tmp)

    # -- projetos ----------------------------------------------------------

    def _indice_projeto(self, nome: str) -> int:
        alvo = sem_acento(nome)
        iguais, prefixo = [], []
        for i, p in enumerate(self.dados["projetos"]):
            n = sem_acento(p["nome"])
            if n == alvo:
                iguais.append(i)
            elif n.startswith(alvo):
                prefixo.append(i)
        if len(iguais) == 1:
            return iguais[0]
        if len(iguais) > 1:
            nomes = ", ".join(self.dados["projetos"][i]["nome"] for i in iguais)
            raise ErroRegistro(f"{nome!r} casa com mais de um projeto: {nomes}")
        if len(prefixo) == 1:
            return prefixo[0]
        if prefixo:
            nomes = ", ".join(self.dados["projetos"][i]["nome"] for i in prefixo)
            raise ErroRegistro(f"{nome!r} e ambiguo: {nomes}")
        conhecidos = ", ".join(p["nome"] for p in self.dados["projetos"])
        raise ErroNaoEncontrado(f"projeto {nome!r} nao encontrado. Conhecidos: {conhecidos or '(nenhum)'}")

    def projeto(self, nome: str) -> dict:
        return self.dados["projetos"][self._indice_projeto(nome)]

    def garantir_projeto(self, nome: str, caminho: str | None = None) -> dict:
        try:
            return self.projeto(nome)
        except ErroNaoEncontrado:  # ambiguidade/erro continuam subindo
            p = {"nome": nome, "caminho": caminho, "ativo": True, "itens": []}
            self.dados["projetos"].append(p)
            return p

    def pausar(self, nome: str) -> dict:
        p = self.projeto(nome)
        p["ativo"] = False
        p["pausado_em"] = agora_iso()
        return p

    def retomar(self, nome: str) -> dict:
        p = self.projeto(nome)
        p["ativo"] = True
        p.pop("pausado_em", None)
        return p

    # -- itens manuais ------------------------------------------------------

    def add(self, nome_projeto: str, titulo: str, detalhe: str | None = None) -> dict:
        titulo = _normalizar(titulo)
        if not titulo:
            raise ErroRegistro("titulo vazio")
        p = self.garantir_projeto(nome_projeto)
        item = {
            "id": f"{datetime.now():%y%m%d-%H%M%S}-{secrets.token_hex(2)}",
            "origem": "manual",
            "titulo": titulo,
            "detalhe": _normalizar(detalhe) if detalhe else None,
            "criada_em": agora_iso(),
            "estado": ITEM_ABERTA,
        }
        p.setdefault("itens", []).append(item)
        return item

    def _item(self, nome_projeto: str, ref: str) -> tuple[dict, dict]:
        p = self.projeto(nome_projeto)
        ref_n = sem_acento(ref)
        abertas = [i for i in p.get("itens", []) if i.get("estado") == ITEM_ABERTA]
        for i in abertas:
            if i["id"] == ref or sem_acento(i["titulo"]) == ref_n:
                return p, i
        parciais = [i for i in abertas if ref_n in sem_acento(i["titulo"])]
        if len(parciais) == 1:
            return p, parciais[0]
        if len(parciais) > 1:
            opcoes = " | ".join(f"[{i['id']}] {i['titulo']}" for i in parciais)
            raise ErroRegistro(f"{ref!r} casa com varios itens em {p['nome']!r}: {opcoes}")
        raise ErroNaoEncontrado(f"item {ref!r} nao encontrado aberto em {p['nome']!r}")

    def feito(self, nome_projeto: str, ref: str) -> dict:
        _, item = self._item(nome_projeto, ref)
        item["estado"] = ITEM_FEITA
        item["fechada_em"] = agora_iso()
        return item

    def rm(self, nome_projeto: str, ref: str) -> dict:
        _, item = self._item(nome_projeto, ref)
        item["estado"] = ITEM_REMOVIDA
        item["fechada_em"] = agora_iso()
        return item

    def ocultar_auto(self, nome_projeto: str) -> dict:
        """Esconde a linha automática (próximo passo) até o ESTADO.md mudar."""
        p = self.projeto(nome_projeto)
        p["auto_oculto_hash"] = p.get("estado_hash") or "-"
        return p

    def mostrar_auto(self, nome_projeto: str) -> dict:
        p = self.projeto(nome_projeto)
        p.pop("auto_oculto_hash", None)
        return p

    # -- consultas ------------------------------------------------------------

    def resumo(self, incluir_pausados: bool = False) -> list[dict]:
        """Por projeto ativo: itens abertas + próximo passo auto visível."""
        saida = []
        for p in self.dados["projetos"]:
            if p.get("presente") is False:
                continue  # pasta sumiu: fora do radar até voltar
            if not p.get("ativo", True) and not incluir_pausados:
                continue
            itens = [i for i in p.get("itens", []) if i.get("estado") == ITEM_ABERTA]
            auto_visivel = bool(p.get("proximo_passo")) and p.get("auto_oculto_hash") != (p.get("estado_hash") or "-")
            saida.append({
                "nome": p["nome"],
                "caminho": p.get("caminho"),
                "ativo": p.get("ativo", True),
                "resumo": p.get("resumo"),
                "proximo_passo": p.get("proximo_passo") if auto_visivel else None,
                "estado_mtime": p.get("estado_mtime"),
                "pausado_sugerido": bool(p.get("pausado_sugerido")),
                "itens": itens,
            })
        return saida

    def contagem_ativa(self) -> tuple[int, int]:
        """(pendências manuais abertas em projetos ativos, projetos ativos com pendência)"""
        r = self.resumo()
        itens = sum(len(g["itens"]) + (1 if g["proximo_passo"] else 0) for g in r)
        projetos = sum(1 for g in r if g["itens"] or g["proximo_passo"])
        return itens, projetos


def hash_arquivo(caminho: Path) -> str:
    h = hashlib.sha1()
    h.update(Path(caminho).read_bytes())
    return h.hexdigest()
