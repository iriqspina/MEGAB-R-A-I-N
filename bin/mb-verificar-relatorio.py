# -*- coding: utf-8 -*-
"""mb-verificar-relatorio.py — conformidade mínima com o modelo mestre POP (B-APP F0, PLANO_FINAL §5.4.4).

Três camadas, cada uma com estado próprio (conforme · nao_conforme · nao_verificado):
  conteudo   JSON do fornecedor contra conteudo.schema.json + regras que o schema não expressa
  html       relatório pronto: bloco de interações presente e igual ao componente vigente
  manifesto  hashes dos componentes do mestre conferem com manifest.json

    python bin/mb-verificar-relatorio.py conteudo motor/modelos/relatorios/260914_pop/fixtures/minima.json
    python bin/mb-verificar-relatorio.py html 00_PARA-VOCE/<tarefa>/<RELATORIO>.html
    python bin/mb-verificar-relatorio.py manifesto
    python bin/mb-verificar-relatorio.py manifesto --gravar   (recalcula; só quem mantém o mestre)

Conforme numa camada não aprova as outras: visual (1440/390, dois temas, Qt) e funcional
(clique, envio, recibo) continuam exigindo prova própria. Documento legado fora do padrão
continua acessível; o estado é informativo.
Saída: JSON. Código 0 conforme, 1 não conforme, 3 não verificado, 2 erro de uso.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime
from pathlib import Path

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI))
import mb_pop_tema  # noqa: E402

CONFORME, NAO_CONFORME, NAO_VERIFICADO = 'conforme', 'nao_conforme', 'nao_verificado'
CODIGO = {CONFORME: 0, NAO_CONFORME: 1, NAO_VERIFICADO: 3}
# Mesmo arranjo de mb_pop_tema: central (motor/modelos) ou cópia do projeto (MEGABRAIN/modelos).
RAIZ = AQUI.parent
MODELOS = next((b for b in (RAIZ / 'motor' / 'modelos', RAIZ / 'modelos') if b.is_dir()), RAIZ / 'motor' / 'modelos')
POP = MODELOS / 'relatorios' / '260914_pop'
# Caminhos relativos à raiz da central; na cópia do projeto motor/modelos/ vira modelos/.
COMPONENTES = (
    ('motor/modelos/relatorios/260914_pop/relatorio-pop.html', 'mestre'),
    ('motor/modelos/relatorios/260914_pop/conteudo.schema.json', 'schema'),
    ('motor/modelos/relatorios/260914_pop/fixtures/minima.json', 'fixture'),
    ('motor/modelos/interacoes/261010_cursor-ferramentas/cursor-ferramentas.js', 'interacao'),
    ('motor/modelos/interacoes/261010_decisoes-respondiveis/decisoes-respondiveis.js', 'interacao'),
    ('motor/modelos/interacoes/261011_agrupamento-visual/agrupamento.css', 'interacao'),
    ('motor/modelos/interacoes/261011_agrupamento-visual/agrupamento.js', 'interacao'),
    ('bin/mb_pop_tema.py', 'montador'),  # monta o bloco "vigente" que a camada html compara
)
META_VERSAO = re.compile(r'<meta\s+name=["\']mb-template["\']\s+content=["\']([^"\']+)["\']', re.I)
# Recurso que o navegador baixa sozinho; link <a href> e rel=preconnect não carregam nada e passam.
REMOTO_MIDIA = re.compile(r'<(?:script|img|iframe|video|audio|source|embed|object|track)\b[^>]*\b(?:src|srcset|data|poster)\s*=\s*["\']?[^"\'>]*https?://', re.I)
REMOTO_LINK = re.compile(r'<link\b[^>]*>', re.I)
REMOTO_CSS = re.compile(r'url\(\s*["\']?\s*https?://|@import\s+(?:url\()?\s*["\']?\s*https?://', re.I)


def recurso_remoto(texto: str) -> bool:
    if REMOTO_MIDIA.search(texto) or REMOTO_CSS.search(texto):
        return True
    for tag in REMOTO_LINK.findall(texto):
        if re.search(r'\brel\s*=\s*["\']?[^"\'>]*\b(?:stylesheet|icon|preload|modulepreload|manifest)\b', tag, re.I) \
                and re.search(r'\bhref\s*=\s*["\']?\s*https?://', tag, re.I):
            return True
    return False


def componente(caminho: str) -> Path:
    alvo = RAIZ / caminho
    if not alvo.exists() and caminho.startswith('motor/modelos/'):
        alvo = RAIZ / caminho.replace('motor/modelos/', 'modelos/', 1)
    return alvo


def resultado(camada, motivos, *, pendencias=(), **extra):
    estado = NAO_CONFORME if motivos else NAO_VERIFICADO if pendencias else CONFORME
    return dict(camada=camada, estado=estado, motivos=list(motivos), nao_verificado=list(pendencias), **extra)


def _data(valor):
    try:
        d = datetime.fromisoformat(str(valor).replace('Z', '+00:00'))
    except ValueError:
        return None
    return d if d.tzinfo else None


def verificar_conteudo(dados) -> dict:
    motivos, pendencias = [], []
    try:
        import jsonschema
        esquema = json.loads((POP / 'conteudo.schema.json').read_text(encoding='utf-8'))
        validador = jsonschema.Draft202012Validator(esquema)
        for erro in sorted(validador.iter_errors(dados), key=lambda e: list(e.absolute_path)):
            onde = '/'.join(str(p) for p in erro.absolute_path) or '(raiz)'
            motivos.append(f'schema {onde}: {erro.message}')
    except ImportError:
        pendencias.append('jsonschema ausente: estrutura não validada pelo schema')
    if not isinstance(dados, dict):
        return resultado('conteudo', motivos or ['conteúdo não é objeto JSON'])
    # Regras que o schema não expressa.
    if 'responseAt' in dados and not _data(dados['responseAt']):
        motivos.append('responseAt sem data ISO com fuso')
    for i, s in enumerate(dados.get('sources') or []):
        if isinstance(s, dict) and s.get('observedAt') and not _data(s['observedAt']):
            motivos.append(f'sources/{i}: data inválida ou sem fuso')
    topicos = [t for t in dados.get('topics') or [] if isinstance(t, dict)]
    ids = [t.get('id') for t in topicos]
    if len(ids) != len(set(ids)):
        motivos.append('topics: id repetido')
    numeros = [t.get('number') for t in topicos]
    if len(numeros) != len(set(numeros)):
        motivos.append('topics: numeração repetida')
    for t in topicos:
        for f in t.get('figures') or []:
            if isinstance(f, dict) and f.get('role') == 'proof' and not (f.get('observedAt') or f.get('hash')):
                motivos.append(f'topics/{t.get("id")}: figura de prova sem data de observação nem hash')
            if isinstance(f, dict) and f.get('observedAt') and not _data(f['observedAt']):
                motivos.append(f'topics/{t.get("id")}: figura com data inválida')
        for m in t.get('metrics') or []:
            if not isinstance(m, dict):
                continue
            if m.get('observedAt') and not _data(m['observedAt']):
                motivos.append(f'topics/{t.get("id")}: número "{m.get("label")}" com data inválida')
            elif not m.get('estimate') and not (m.get('source') and m.get('observedAt')):
                motivos.append(f'topics/{t.get("id")}: número "{m.get("label")}" sem fonte e data; marque estimate=true se for [ESTIMATIVA]')
    vistos = set()
    for d in dados.get('decisions') or []:
        if not isinstance(d, dict):
            continue
        if d.get('id') in vistos:
            motivos.append(f'decisions: id repetido {d.get("id")}')
        vistos.add(d.get('id'))
        if d.get('contextTopicId') not in ids:
            motivos.append(f'decisions/{d.get("id")}: contexto aponta para tópico inexistente')
        opcoes = d.get('options') or []
        if opcoes and len(opcoes) < 2:
            motivos.append(f'decisions/{d.get("id")}: alternativa exige ao menos 2 opções')
        if d.get('recommended') and d['recommended'] not in opcoes:
            motivos.append(f'decisions/{d.get("id")}: recomendada fora das opções')
        if not opcoes and not d.get('explanation'):
            motivos.append(f'decisions/{d.get("id")}: sem opções nem campo de explicação')
    datas = [_data(h.get('at')) for h in dados.get('history') or [] if isinstance(h, dict)]
    if None in datas:
        motivos.append('history: data inválida ou sem fuso')
    elif any(a < b for a, b in zip(datas, datas[1:])):
        motivos.append('history: fora da ordem recente primeiro')
    return resultado('conteudo', motivos, pendencias=pendencias,
                     topicos=len(topicos), decisoes=len(vistos))


def verificar_html(texto: str) -> dict:
    motivos, pendencias = [], []
    i = texto.find(mb_pop_tema.MARCA_INTERACOES_INICIO)
    j = texto.find(mb_pop_tema.MARCA_INTERACOES_FIM, i if i >= 0 else 0)
    vigente = mb_pop_tema.html_interacoes()
    if i < 0 or j < 0:
        # Geradores antigos embutem o componente sem as marcas: existe, mas a versão não é comparável.
        if 'id="cf-script"' in texto and 'CursorFerramentas' in texto:
            pendencias.append('Ferramentas do cursor presentes fora das marcas mb-interacoes: versão não comparada')
        else:
            motivos.append('sem as Ferramentas do cursor')
    elif not vigente:
        pendencias.append('componente de interações vigente não encontrado para comparar')
    elif texto[i:j + len(mb_pop_tema.MARCA_INTERACOES_FIM)] != vigente:
        motivos.append('bloco de interações diferente do componente vigente (rode bin/mb-interacoes.py)')
    if recurso_remoto(texto):
        motivos.append('recurso remoto em script/estilo/mídia; o mestre exige arquivo offline')
    versao = META_VERSAO.search(texto)
    if not versao:
        pendencias.append('sem <meta name="mb-template">: versão do mestre não identificada')
    return resultado('html', motivos, pendencias=pendencias, versao=versao.group(1) if versao else None)


def _hash(caminho: Path) -> str | None:
    try:
        return hashlib.sha256(caminho.read_bytes()).hexdigest()
    except OSError:
        return None


def verificar_manifesto(gravar=False, arquivo=None) -> dict:
    arquivo = Path(arquivo) if arquivo else POP / 'manifest.json'
    atual = [dict(path=p, papel=papel, sha256=_hash(componente(p))) for p, papel in COMPONENTES]
    base = json.loads(arquivo.read_text(encoding='utf-8')) if arquivo.is_file() else None
    registrado = {c.get('path'): c.get('sha256') for c in (base or {}).get('componentes') or []}
    motivos = [f'{c["path"]}: arquivo ausente' for c in atual if c['sha256'] is None]
    diferentes = [c['path'] for c in atual if c['sha256'] and registrado.get(c['path']) != c['sha256']]
    if gravar and not motivos:
        # Regravar abençoa os hashes atuais: a versão anterior fica no histórico, com data, para a trilha.
        base = base or {}
        if base.get('componentes'):
            base.setdefault('historico', []).insert(0, dict(gravado_em=base.get('gravado_em'), componentes=base['componentes']))
        base.update(componentes=atual, gravado_em=datetime.now().astimezone().isoformat(timespec='seconds'))
        arquivo.write_text(json.dumps(base, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        return resultado('manifesto', [], pendencias=['regravado agora: conferência circular, vale a trilha em historico'] if diferentes else (),
                         componentes=len(atual), regravados=diferentes)
    if base is None:
        return resultado('manifesto', motivos, pendencias=['manifest.json ausente'])
    motivos += [f'{p}: hash difere do manifesto' for p in diferentes]
    return resultado('manifesto', motivos, componentes=len(atual))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description='conformidade mínima com o modelo mestre POP')
    ap.add_argument('camada', choices=('conteudo', 'html', 'manifesto'))
    ap.add_argument('arquivo', nargs='?')
    ap.add_argument('--gravar', action='store_true', help='manifesto: recalcula e grava os hashes')
    a = ap.parse_args(argv)
    if a.gravar and a.camada != 'manifesto':
        print(json.dumps(dict(erro='--gravar só vale para a camada manifesto'), ensure_ascii=False))
        return 2
    if a.camada == 'manifesto':
        saida = verificar_manifesto(a.gravar)
    elif not a.arquivo or not Path(a.arquivo).is_file():
        print(json.dumps(dict(erro='informe um arquivo existente'), ensure_ascii=False))
        return 2
    elif a.camada == 'conteudo':
        try:
            dados = json.loads(Path(a.arquivo).read_text(encoding='utf-8-sig'))
        except ValueError as erro:
            saida = resultado('conteudo', [f'JSON inválido: {erro}'])
        else:
            saida = verificar_conteudo(dados)
    else:
        saida = verificar_html(Path(a.arquivo).read_text(encoding='utf-8', errors='replace'))
    print(json.dumps(saida, ensure_ascii=False, indent=2))
    return CODIGO[saida['estado']]


if __name__ == '__main__':
    raise SystemExit(main())
