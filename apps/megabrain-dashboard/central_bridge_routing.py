"""Perfis explícitos da ponte; preferências experimentais recuperadas do cérebro.

Não consulta modelo, não converte esforços entre fornecedores e não faz fallback.
"""
from __future__ import annotations

import copy

PAPEIS = ('planejador', 'orquestrador', 'worker', 'revisor')
FONTE = 'memoria/cerebro/wiki/261011_prioridades-vendors-por-tarefa.md'
ENSAIO = 'memoria/cerebro/wiki/261011_ensaios-modelos-workers-central.md'
CATALOGO = [
    {'vendor': 'gpt', 'nome': 'Codex · conta principal', 'fonte': FONTE, 'modelos': [
        {'id': 'gpt-6-astra', 'nome': 'Astra', 'efforts': ['low', 'medium', 'high', 'xhigh', 'max', 'ultra']},
        {'id': 'gpt-6.1-sol', 'nome': 'Sol 6.1', 'efforts': ['low', 'medium', 'high', 'xhigh', 'max', 'ultra']},
        {'id': 'gpt-6-luna', 'nome': 'Luna', 'efforts': ['low', 'medium', 'high', 'xhigh', 'max']},
    ]},
    {'vendor': 'claude', 'nome': 'Claude Code', 'fonte': FONTE, 'modelos': [
        {'id': 'claude-opus-5-5', 'nome': 'Opus 5.5', 'efforts': ['low', 'medium', 'high', 'xhigh', 'max']},
        {'id': 'fable', 'nome': 'Fable (alias da CLI)', 'efforts': ['low', 'medium', 'high', 'xhigh', 'max'],
         'aviso': 'Versão final e acesso pela assinatura serão confirmados no retorno; alias pode mudar.'},
        {'id': 'sonnet', 'nome': 'Sonnet (alias da CLI)', 'efforts': ['low', 'medium', 'high', 'xhigh', 'max'],
         'aviso': 'Versão final e acesso pela assinatura serão confirmados no retorno; alias pode mudar.'},
    ]},
    {'vendor': 'glm', 'nome': 'ZCode · GLM principal', 'fonte': ENSAIO,
     'aviso': 'Modelo textual. Parecer sobre texto não comprova inspeção visual de pixels.', 'modelos': [
        {'id': 'GLM-5.3', 'nome': 'GLM-5.3 principal', 'efforts': ['low', 'high', 'max'], 'visual': False},
    ]},
    {'vendor': 'gemini', 'nome': 'Gemini CLI', 'fonte': FONTE, 'modelos': [],
     'aviso': 'Perfil explícito indisponível: modelo e esforço ainda não certificados nesta ponte.'},
]
PADROES = {
    'gpt': {'vendor': 'gpt', 'modelo': 'gpt-6-astra', 'effort': 'medium'},
    'claude': {'vendor': 'claude', 'modelo': 'claude-opus-5-5', 'effort': 'high'},
    'glm': {'vendor': 'glm', 'modelo': 'GLM-5.3', 'effort': 'max'},
    # Ordens antigas sem perfil continuam legíveis; ordens novas exigem perfil certificado.
}


def catalogo(central=None):
    return copy.deepcopy(CATALOGO)


def validar_rota(rota, *, parcial=False):
    if not isinstance(rota, dict) or set(rota) - {'vendor', 'modelo', 'effort'}:
        raise ValueError('Rota inválida: use somente vendor, modelo e effort.')
    if not parcial and set(rota) != {'vendor', 'modelo', 'effort'}:
        raise ValueError('Rota explícita exige vendor, modelo e effort completos.')
    if not rota:
        return {}
    if any(not isinstance(v, str) or not v.strip() for v in rota.values()):
        raise ValueError('Vendor, modelo e effort precisam de valores de texto.')
    vendor = rota.get('vendor')
    if vendor is None:
        if parcial:
            return dict(rota)
        raise ValueError('Escolha o fornecedor da rota.')
    if vendor not in PADROES:
        raise ValueError('Fornecedor sem modelo certificado nesta ponte: ' + vendor + '.')
    perfil = dict(PADROES[vendor], **rota)
    modelos = next(x['modelos'] for x in CATALOGO if x['vendor'] == vendor)
    modelo = next((x for x in modelos if x['id'] == perfil['modelo']), None)
    if modelo is None:
        raise ValueError('Modelo indisponível no catálogo deste fornecedor: ' + perfil['modelo'] + '.')
    if perfil['effort'] not in modelo['efforts']:
        raise ValueError('Esforço indisponível para ' + perfil['modelo'] + ': ' + perfil['effort'] + '.')
    return perfil


def normalizar_pipeline(pipeline=None, vendor='gpt'):
    if pipeline is not None and (not isinstance(pipeline, dict) or set(pipeline) - set(PAPEIS)):
        raise ValueError('Pipeline inválida: use planejador, orquestrador, worker e revisor.')
    pipeline = pipeline or {}
    base = validar_rota({'vendor': vendor}, parcial=True)
    saida = {}
    for papel in PAPEIS:
        rota = pipeline.get(papel) or {}
        if not isinstance(rota, dict):
            raise ValueError('Perfil inválido para o papel ' + papel + '.')
        # Mudar só o vendor seleciona o padrão daquele fornecedor, jamais modelo alheio.
        herdado = PADROES.get(rota.get('vendor'), base) if rota.get('vendor') else base
        saida[papel] = validar_rota(dict(herdado, **rota))
    return saida


def presets(central=None):
    def perfil(vendor, modelo=None, effort=None):
        return dict(PADROES[vendor], **({'modelo': modelo} if modelo else {}), **({'effort': effort} if effort else {}))
    def item(id, nome, descricao, tradeoff, criador, revisor):
        return dict(id=id, nome=nome, descricao=descricao, tradeoff=tradeoff, fonte=FONTE,
                    fontes=[FONTE, ENSAIO], experimental=True,
                    pipeline=dict(planejador=criador, orquestrador=criador,
                                  worker=copy.deepcopy(criador), revisor=revisor))
    return [
        item('visual', 'Direção visual', 'Hipótese: Opus explora e refina com referência visual.',
             'Revisão em Astra exige imagem transportada e inspeção real; transferência perde contexto.',
             perfil('claude'), perfil('gpt', effort='high')),
        item('integracao', 'Integração e fechamento', 'Hipótese: Astra coordena integração; Opus revisa independentemente.',
             'Pode ampliar testes; contrato deve delimitar escopo e prova.',
             perfil('gpt', effort='high'), perfil('claude')),
        item('delimitado', 'Execução delimitada', 'Sol cria; GLM principal máximo revisa texto e código com teste objetivo.',
             'GLM é textual: revisão visual final precisa de observador com imagem comprovada.',
             perfil('gpt', 'gpt-6.1-sol', 'xhigh'), perfil('glm')),
    ]
