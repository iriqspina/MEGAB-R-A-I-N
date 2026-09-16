"""Triagem local explicável. Recomenda etapas; nunca autoriza nem executa ações."""
from __future__ import annotations
import datetime as dt
import json
import re
import unicodedata
from pathlib import Path

SENSIBILIDADES = ('enxuta', 'equilibrada', 'criteriosa')
GATES = ('assumir contexto', 'enquadrar', 'orçar esforço', 'produzir', 'auditar', 'verificar', 'passar bastão', 'aprender')
def normalizar(texto):
    return ''.join(c for c in unicodedata.normalize('NFKD', texto.casefold()) if not unicodedata.combining(c))

def classificar(prompt, sensibilidade='equilibrada', contexto=None):
    if sensibilidade not in SENSIBILIDADES:
        raise ValueError('Sensibilidade inválida; escolha enxuta, equilibrada ou criteriosa.')
    if not isinstance(prompt, str):
        raise ValueError('O pedido precisa ser texto.')
    contexto = contexto or {}
    if not isinstance(contexto, dict):
        raise ValueError('Contexto precisa ser objeto JSON.')
    text = normalizar(prompt).strip()
    def has(pattern): return bool(re.search(pattern, text))
    sinais = []
    social = bool(re.fullmatch(r'(oi|ola|bom dia|boa tarde|boa noite|obrigad[oa]|valeu|bom trabalho)[!.\s]*', text))
    continuacao = bool(re.fullmatch(r'(sim|nao|ok|certo|continua|continue|pode|faz|manda|isso)[!.\s]*', text))
    risco = has(r'\b(public\w*|deploy|apagu?\w*|delet\w*|exclu\w*|sobrescrev\w*|compr(a|ar|e|ou|as)|pag(a|ar|ue|ou|amento|amentos)|transfer\w*|senha|segredo|token|remedio|dose|medic\w*|juridic\w*|invest\w*|producao|commit|push)\b')
    artefato = has(r'\b(cri\w*|fac[ao]|fazer|faz|gere?|gerar|mont\w*|implement\w*|corrig\w*|consert\w*|organiz\w*|padroniz\w*|refator\w*|otimiz\w*|reescrev\w*|edite?|alter\w*|melhor\w*|ajust\w*|analise|audit\w*|revis\w*|relatorio|arquivo|planilha|pagina|codigo|html|pdf|app|ux|ui|plano|template|atualiz\w*|adapt\w*|julg\w*|escrev\w*|redij\w*|desenh\w*|instal\w*|configur\w*|sincroniz\w*|migr\w*|traduz\w*|resum\w*|entreg\w*|trabalho|proposta|orcamento|peca|layout|logo|deck|apresentacao|widget|painel|dashboard|skill|hook|teste)\b')
    fontes = has(r'\b(pesquis\w*|verifi\w*|atual|hoje|preco|fonte|cite|dados|versao|lei|noticia)\b')
    completo = has(r'\b(completo|completa|capriche|detalh\w*|profund\w*|rigor\w*)\b')
    negacao = has(r'\b(nao|nunca|sem)\b')
    pergunta = has(r'^(o que|como|qual|quanto|quando|por que|porque|onde|quem)\b') or text.endswith('?')
    pendente = bool(contexto.get('pending_action'))
    ativo = bool(contexto.get('active_artifact'))
    explicito = contexto.get('explicit_kind')
    if explicito not in (None, 'conversa', 'resposta', 'entrega', 'critica'):
        raise ValueError('explicit_kind inválido.')
    if risco: sinais.append('assunto ou ação sensível; requer interpretação e autorização própria')
    if artefato: sinais.append('pedido ou assunto de entrega detectado')
    if fontes: sinais.append('evidência ou informação variável')
    if negacao: sinais.append('negação presente; não assumir intenção pela palavra detectada')
    if completo: sinais.append('profundidade explicitamente pedida')
    if continuacao: sinais.append('continuação depende do escopo da conversa')
    if pendente: sinais.append('há ação pendente no contexto')
    if ativo: sinais.append('há artefato ativo no contexto')
    if risco or (continuacao and pendente): rota = 'critica'
    elif ativo or explicito == 'entrega' or (artefato and not (pergunta and has(r'^(o que (e|significa)|qual a diferenca)\b'))): rota = 'entrega'
    elif social and not pendente: rota = 'conversa'
    else: rota = 'resposta'
    # Contexto explícito pode subir a exigência, jamais reduzir sinais sensíveis.
    ordem = {'conversa':0,'resposta':1,'entrega':2,'critica':3}
    if explicito and ordem[explicito] > ordem[rota]: rota = explicito
    ambigua = continuacao or not text or (rota == 'resposta' and not pergunta)
    gates=[]
    for idx,nome in enumerate(GATES):
        estado='condicional'; motivo='Ativar se o conteúdo ou a conversa exigir; a IA confere a triagem.'
        if idx in (0,3,4,5):
            estado='ativar'; motivo='Piso de contexto, resposta correta, revisão e verificação proporcional; não exige relatório.'
        elif rota in ('entrega','critica'):
            estado='ativar'; motivo='Entrega ou tema sensível pede enquadramento, esforço e registro proporcional.'
        elif rota == 'conversa':
            estado='dispensado'; motivo='Conversa sem artefato ou ação: não criar plano, arquivo ou relatório.'
        elif idx == 1 and ambigua:
            estado='ativar'; motivo='Recuperar o contexto; perguntar apenas se a resposta muda a execução.'
        gates.append({'id':idx,'nome':nome,'estado':estado,'motivo':motivo})
    obrigatorios=['respeitar escopo e instruções humanas','não inventar fatos ou conclusões','verificação proporcional à afirmação']
    if rota in ('entrega','critica'): obrigatorios += ['revisão independente para artefato não trivial','testar comportamento afetado e preservar reversão','destino completo, verificado e acessível']
    if risco or pendente: obrigatorios += ['avaliar autorização no contexto; a triagem não concede permissão']
    if fontes or risco: obrigatorios += ['consultar fonte apropriada antes de afirmar dado incerto ou variável']
    opcionais=[]
    if sensibilidade != 'enxuta' and rota not in ('conversa',): opcionais.append('explicitar hipóteses que afetam a resposta')
    if (sensibilidade == 'criteriosa' or completo) and rota != 'conversa': opcionais += ['segunda lente para premissas relevantes','comparar alternativas quando houver decisão real']
    return {'schema_version':1,'rota':rota,'sensibilidade':sensibilidade,'sinais':sinais,'gates':gates,'obrigatorios':obrigatorios,'opcionais':opcionais,'precisa_contexto':ambigua or pendente,'autoriza_execucao':False,'limite':'Heurística local por sinais. A IA deve corrigir falsos positivos e omissões com base na conversa; não substitui julgamento nem autorização.'}

def destino_local(projeto,nome):
    root=Path(projeto).resolve();p=(root/'dados'/nome).resolve()
    if not p.is_relative_to(root): raise ValueError('Destino de dados sai do projeto: '+str(p))
    return p
def config_path(projeto): return destino_local(projeto,'preferencias-megabrain.json')
def ler_config(projeto):
    p=config_path(projeto)
    if not p.exists(): return {'schema_version':1,'sensibilidade':'equilibrada','origem':'padrão explícito; nenhuma preferência salva'}
    d=json.loads(p.read_text(encoding='utf-8-sig'))
    if not isinstance(d,dict) or d.get('schema_version') != 1 or d.get('sensibilidade') not in SENSIBILIDADES:
        raise ValueError(f'Configuração inválida: {p}')
    return d

def salvar_config(projeto, sensibilidade):
    if sensibilidade not in SENSIBILIDADES: raise ValueError('Sensibilidade inválida')
    import mb_trava as t
    import mb_utils as u
    p=config_path(projeto)
    with t.travado(p,agente=t.agente_script('mb-preferencias'),motivo='Escolha explícita de sensibilidade'):
        d=ler_config(projeto); d.update(schema_version=1,sensibilidade=sensibilidade,atualizado_em=dt.datetime.now().astimezone().isoformat())
        d.pop('origem',None); p.parent.mkdir(parents=True,exist_ok=True)
        if not u.atomic_write_text(p,json.dumps(d,ensure_ascii=False,indent=2)+'\n'): raise OSError('Não foi possível salvar a preferência')
    return d

def instrucao(resultado):
    return ('### Triagem MEGABRAIN\nRota sugerida: '+resultado['rota']+'; sensibilidade: '+resultado['sensibilidade']+'. '
            +'A mesma triagem atende todo pedido. Só execute etapas pertinentes; conversa não gera relatório. '
            +'Piso: '+ '; '.join(resultado['obrigatorios'])+'. '
            +'Sinais: '+('; '.join(resultado['sinais']) or 'nenhum sinal especial')+'. '
            +'Passos opcionais: '+('; '.join(resultado['opcionais']) or 'nenhum acrescentado')+'. '
            +'Confirme o contexto antes de seguir uma continuação. Esta sugestão nunca autoriza ação. '
            +'Destinos: link com caminho absoluto verificado e pasta completa copiável; não prometer botão que o chat não oferece.')

def registrar_observacao(projeto, resultado, agente='desconhecido'):
    """Metadados limitados; não guarda pedido, resposta, segredo nem hash do pedido."""
    import mb_trava as t
    import mb_utils as u
    p=destino_local(projeto,'triagem-observacoes.json')
    with t.travado(p,agente=t.agente_script('mb-triagem-observacao'),motivo='Registrar somente rota e contadores'):
        doc=json.loads(p.read_text(encoding='utf-8-sig')) if p.exists() else {'schema_version':1,'total':0,'por_rota':{},'recentes':[]}
        if not isinstance(doc,dict) or doc.get('schema_version')!=1: raise ValueError('Registro de observações inválido')
        rota=resultado['rota'];doc['total']+=1;doc['por_rota'][rota]=doc['por_rota'].get(rota,0)+1
        doc['recentes']=(doc['recentes']+[{'data':dt.datetime.now().astimezone().isoformat(timespec='seconds'),'rota':rota,'sensibilidade':resultado['sensibilidade'],'agente':re.sub(r'[^a-zA-Z0-9_-]','',agente)[:40],'precisa_contexto':resultado['precisa_contexto']}])[-200:]
        p.parent.mkdir(parents=True,exist_ok=True)
        if not u.atomic_write_text(p,json.dumps(doc,ensure_ascii=False,indent=2)+'\n'): raise OSError('Falha registrando observação')
