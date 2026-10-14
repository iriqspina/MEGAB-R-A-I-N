"""Editable input lanes; deterministic suggestion, explicitly not semantic certainty."""
import copy, re, unicodedata
from central_store import validate_process

def stage(id,title,role='creator',model='codex',instruction='',required=False):
    return dict(id=id,title=title,role=role,model=model,effort='max' if model=='glm' else 'xhigh',instruction=instruction,enabled=True,required=required)

DEFAULT_ROUTES={'routes':[
 {'id':'pergunta','title':'Tirar uma dúvida','description':'Resposta direta, sem montar uma produção.','keywords':['explica','explique','o que e','como funciona','duvida'], 'stages':[stage('responder','Responder com clareza',instruction='Explique em linguagem simples. Diga quando não sabe. Não transforme conversa em projeto.')]},
 {'id':'pesquisa','title':'Pesquisar e entender','description':'Fontes, comparação e conclusão verificável.','keywords':['pesquisa','pesquise','investigue','compare','fontes','mercado'], 'stages':[stage('investigar','Investigar as fontes',instruction='Use somente o contexto fornecido; liste lacunas que exigem busca atual. Não invente URLs nem alegue pesquisa sem ferramenta.'),stage('sintetizar','Transformar em decisão',instruction='Compare opções por adequação, manutenção e limitações; diferencie fato e inferência.'),stage('revisar','Revisar as conclusões','reviewer','glm','Procure premissas sem prova, desatualização e conclusões universais indevidas.',True)]},
 {'id':'visual','title':'Criar design','description':'Referência, direção visual, criação, prova e revisão.','keywords':['design','landing page','layout','figma','frontend','front-end','visual','interface'], 'stages':[stage('brief','Entender o pedido',instruction='Defina usuário, resultado, restrições e critérios de aceite.'),stage('referencias','Escolher referências',instruction='Relacione as referências reais fornecidas às decisões. Se faltarem, declare a lacuna.'),stage('criar','Desenhar a solução',model='claude',instruction='Proponha hierarquia, tipografia, grade, estados e comportamento. Preserve coesão e decisões humanas.'),stage('testar','Definir e conferir provas',instruction='Liste o que está comprovado e o que precisa de render/teste. Texto não prova interface funcional.',required=True),stage('revisar','Revisar com GLM principal','reviewer','glm','Revise clareza, consistência, cobertura de estados e afirmações sem prova.',True),stage('entregar','Integrar e explicar',instruction='Integre correções defensáveis e entregue uma decisão clara com limitações.',required=True)]},
 {'id':'codigo','title':'Construir ou corrigir código','description':'Problema, implementação planejada, testes e revisão.','keywords':['codigo','bug','erro','api','backend','programar','implementar','teste'], 'stages':[stage('diagnostico','Entender a causa',instruction='Separe causa observada de hipótese e peça evidência faltante.'),stage('solucao','Propor a mudança',instruction='Prefira alteração localizada, preservando o trabalho existente.'),stage('testar','Definir a verificação',instruction='Dê testes significativos, riscos e reversão. Não afirme que executou testes.',required=True),stage('revisar','Revisar a solução','reviewer','glm','Procure regressões, lacunas e problemas de segurança concretos.',True)]},
 {'id':'revisao','title':'Revisar algo pronto','description':'Ler o original, encontrar problemas e priorizar ajustes.','keywords':['revise','revisar','audite','critique','avaliar','corrija'], 'stages':[stage('preparar','Entender o material',instruction='Identifique intenção, fonte e critérios; não refaça sem necessidade.'),stage('revisar','Revisão independente','reviewer','glm','Classifique achados por evidência e efeito para o usuário.',True)]},
 {'id':'organizacao','title':'Organizar ou automatizar','description':'Mapa atual, rotas prontas, proposta e revisão.','keywords':['organize','organizar','automacao','automatizar','pipeline','esteira','processo'], 'stages':[stage('mapear','Mapear o trabalho',instruction='Mapeie entradas, saídas, responsáveis e pontos de atrito.'),stage('desenhar','Desenhar o processo',instruction='Compare rotas prontas; proponha o menor mecanismo útil e reversível.'),stage('revisar','Revisar o processo','reviewer','glm','Procure complexidade desnecessária e passos sem evidência.',True)]}
]}

# Keep the exact previous defaults for a reversible, field-wise migration.
# User-written instructions and custom categories are never replaced by a template.
LEGACY_ROUTES=copy.deepcopy(DEFAULT_ROUTES)
EXECUTION_CHANGES={
 'pesquisa':{'investigar':dict(capability='research',model='claude',instruction='Pesquise fontes atuais na web com WebSearch e WebFetch. Priorize documentação e fontes primárias. Cite os links efetivamente consultados e as datas; diferencie fato, inferência e lacuna.')},
 'visual':{
  'referencias':dict(capability='research',model='claude',instruction='Busque referências e documentação reais para o pedido; explique qual decisão cada fonte sustenta. Não copiar marcas nem alegar aprovação estética.'),
  'testar':dict(capability='code',model='codex',title='Executar e conferir a solução',instruction='Inspecione o código produzido na área do pedido. Rode testes reais adequados, corrija defeitos encontrados e registre comandos/resultados. Para HTML, valide estrutura e comportamento testável, sem fingir inspeção visual.')},
 'codigo':{
  'solucao':dict(capability='code',model='codex',title='Implementar a mudança',instruction='Implemente de verdade na área isolada do pedido. Preserve os arquivos de entrada. Crie código e testes significativos; use dependências já disponíveis ou biblioteca padrão. Execute os testes e corrija falhas. Não faça instalação, publicação ou mutação git.'),
  'testar':dict(capability='code',model='codex',title='Executar os testes',instruction='Leia a implementação e execute testes reais de comportamento. Use python -m unittest, pytest ou node --test quando pertinentes. Corrija falhas dentro da área do pedido. Não substitua teste executado por texto ou arquivo afirmando PASS.')},
 'organizacao':{'desenhar':dict(capability='code',model='codex',title='Criar o processo utilizável',instruction='Transforme o pedido em artefato utilizável na área isolada: configuração, script ou interface conforme necessário. Implemente e execute testes significativos com dependências disponíveis. Não aplicar em contas, originais ou sistemas externos.')}
}
IMPLEMENT_VISUAL=dict(id='implementar',title='Construir a interface',role='creator',model='codex',effort='xhigh',instruction='Implemente a direção visual definida por Claude como interface funcional na área isolada. Para prévia na central prefira HTML autossuficiente, CSS e JavaScript inline sem CDN, rede ou instalação. Inclua e execute testes reais adequados. Não publique nem altere originais.',enabled=True,required=True,capability='code')

def upgrade_legacy(data):
    result=copy.deepcopy(data)
    if result.get('execution_schema')==2:return result
    for route in result.get('routes',[]):
        legacy=next((r for r in LEGACY_ROUTES['routes'] if r['id']==route.get('id')),None)
        for s in route.get('stages',[]):
            s.setdefault('capability','textual')
            change=EXECUTION_CHANGES.get(route.get('id'),{}).get(s.get('id'),{})
            original=next((x for x in legacy['stages'] if x['id']==s.get('id')),None) if legacy else None
            for key,value in change.items():
                if key in {'capability','model'} or (original and s.get(key)==original.get(key)):s[key]=value
        if route.get('id')=='visual' and not any(s['id']=='implementar' for s in route['stages']):
            index=next((i for i,s in enumerate(route['stages']) if s['id']=='testar'),len(route['stages']))
            route['stages'].insert(index,copy.deepcopy(IMPLEMENT_VISUAL))
        if route.get('id')=='codigo':route['description']='Implementação real, testes executados e revisão independente.'
    result['execution_schema']=2
    return result

DEFAULT_ROUTES=upgrade_legacy(DEFAULT_ROUTES)

def routing_document(store,pid):
    key='routing:'+pid; doc=store.get(key,DEFAULT_ROUTES)
    if doc['data'].get('execution_schema')!=2:
        from central_store import Conflict
        try:doc=store.put(key,doc['revision'],upgrade_legacy(doc['data']))
        except Conflict:doc=store.get(key,DEFAULT_ROUTES)
    return doc

def execution_plan(stages):
    caps={s.get('capability','textual') for s in stages}
    return dict(summary='Pesquisa na web e produção isolada, com evidências por etapa.' if caps-{'textual'} else 'Resposta ou revisão textual, sem execução de ferramentas.',
        tools=(['Pesquisa e leitura de páginas públicas'] if 'research' in caps else [])+(['Leitura, escrita e testes em área isolada'] if 'code' in caps else [])+['GLM principal revisa quando previsto na esteira'],
        write_scope=['Área exclusiva deste pedido; originais do projeto preservados'] if 'code' in caps else ['Nenhuma escrita nos arquivos originais'],
        checks=(['Fontes e consultas observadas'] if 'research' in caps else [])+(['Arquivos produzidos e comandos de teste concluídos'] if 'code' in caps else []),
        capabilities=sorted(caps),max_repair_rounds=1)
def norm(value): return ''.join(c for c in unicodedata.normalize('NFD',value.lower()) if unicodedata.category(c)!='Mn')
def matches_word(keyword,text): return bool(re.search(r'\b'+re.escape(norm(keyword))+r'\b',text))
def validate_routing(data):
    if not isinstance(data,dict) or not isinstance(data.get('routes'),list) or not 1<=len(data['routes'])<=20: raise ValueError('Inclua de uma a vinte categorias.')
    seen=set()
    for route in data['routes']:
        rid=route.get('id','')
        if not re.fullmatch(r'[a-z][a-z0-9_-]{0,39}',rid) or rid in seen: raise ValueError('Identificador de categoria inválido ou repetido.')
        seen.add(rid)
        if not isinstance(route.get('title'),str) or not 1<=len(route['title'])<=100: raise ValueError('Dê um nome à categoria.')
        keywords=route.get('keywords',[])
        if not isinstance(keywords,list) or len(keywords)>40 or any(not isinstance(k,str) or len(k)>80 for k in keywords): raise ValueError('Sinais de classificação inválidos.')
        validate_process(dict(mode='execution',stages=route.get('stages')))
        original=next((r for r in DEFAULT_ROUTES['routes'] if r['id']==rid),None)
        required={s['id'] for s in original['stages'] if s.get('required')} if original else set()
        enabled={s['id'] for s in route['stages'] if s.get('enabled',True)}
        if required-enabled: raise ValueError('Esta categoria mantém as etapas obrigatórias: '+', '.join(sorted(required-enabled)))
        for s in route['stages']:
            expected=next((x for x in original['stages'] if x['id']==s['id']),None) if original else None
            if expected and expected.get('required') and expected['role']=='reviewer' and (s.get('role')!='reviewer' or s.get('model')!='glm'):
                raise ValueError('A etapa obrigatória de revisão mantém GLM principal como revisor.')
            if expected and expected.get('required') and expected.get('capability')=='code' and s.get('capability')!='code':
                raise ValueError('A etapa obrigatória de execução não pode virar apenas análise.')
        if any(s.get('capability') in {'code','research'} and s.get('enabled',True) for s in route['stages']) and not any(s.get('role')=='reviewer' and s.get('model')=='glm' and s.get('enabled',True) for s in route['stages']):
            raise ValueError('A produção com ferramentas inclui uma revisão GLM principal.')
        tools=[i for i,s in enumerate(route['stages']) if s.get('enabled',True) and s.get('capability') in {'code','research'}]
        reviews=[i for i,s in enumerate(route['stages']) if s.get('enabled',True) and s.get('role')=='reviewer' and s.get('model')=='glm']
        if tools and (not reviews or max(reviews)<max(tools)):
            raise ValueError('Posicione uma revisão GLM depois da última etapa de pesquisa ou código.')
    return data
def preview(data,prompt,category=None,categories=None):
    routes=data['routes']; normalized=norm(prompt)
    if categories:
        if not isinstance(categories,list) or not 1<=len(categories)<=2 or len(set(categories))!=len(categories): raise ValueError('Combine uma ou duas esteiras diferentes.')
        selections=[preview(data,prompt,category=rid) for rid in categories]
        stages=[]
        for selection in selections:
            for s in selection['stages']:
                s['id']=selection['category'][:20]+'_'+s['id'][:35]
                s['source_category']=selection['category']; stages.append(s)
        validate_process({'mode':'analysis','stages':stages})
        plan=execution_plan(stages)
        return dict(category=categories[0],categories=categories,title=' → '.join(s['title'] for s in selections),reason='Duas esteiras escolhidas por você, executadas na ordem exibida; nenhuma etapa obrigatória é omitida.',matches=[],stages=stages,classification='combinação explícita',execution_scope=plan['summary'],execution_plan=plan,multiple_categories=True)
    scores=[(sum(1 for k in r.get('keywords',[]) if matches_word(k,normalized)),i,r) for i,r in enumerate(routes)]
    ranked=sorted(scores,key=lambda x:(x[0],-x[1]),reverse=True)
    if category:
        route=next((r for r in routes if r['id']==category),None)
        if not route: raise ValueError('Categoria não encontrada.')
    else: route=ranked[0][2] if ranked[0][0] else routes[0]
    matches=[dict(category=r['id'],title=r['title'],signals=[k for k in r.get('keywords',[]) if matches_word(k,normalized)]) for score,i,r in ranked if score]
    stages=copy.deepcopy([s for s in route['stages'] if s.get('enabled',True)]);plan=execution_plan(stages)
    return dict(category=route['id'],title=route['title'],reason='Categoria escolhida por você.' if category else 'Sugestão por palavras do pedido; você pode trocar a categoria.',matches=matches,stages=stages,classification='heurística editável',execution_scope=plan['summary'],execution_plan=plan,multiple_categories=len(matches)>1)
