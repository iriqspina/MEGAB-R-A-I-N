from pathlib import Path
import sys,hashlib,json,re,datetime
ROOT=Path(__file__).resolve().parents[2];HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(ROOT/'bin'))
import mb_trava as t
def edit(relative,fn):
    p=ROOT/relative
    with t.travado(p,agente='codex-plataforma-2242',motivo='Registrar estado de plataforma preservando histórico'):
        old=p.read_text(encoding='utf-8-sig') if p.exists() else ''
        backup=HERE/'backup'/relative;backup.parent.mkdir(parents=True,exist_ok=True)
        if not backup.exists() and p.exists():backup.write_bytes(p.read_bytes())
        new=fn(old)
        if new!=old:p.write_text(new,encoding='utf-8')
headline='''## Vigente · 260916 · organização e experiência MEGABRAIN

TL;DR: entrada fixa `00_PARA-VOCE/INICIO.html`, registro explícito e navegação no aplicativo existente; triagem proporcional comum e controle de sensibilidade local. Caminhos completos clicáveis/copiáveis padronizados na identidade. Nenhum acervo antigo movido.
Provas: `evidence/260916_plataforma/` (situação inicial, testes, navegador, aplicativo, revisão e backups). Revisão textual V6 `260916_175608_306d11cb` aprovada; implementação testada separadamente. Não equivale a validação universal de clientes.
Aberto: consolidar aplicações, migrar acervo por lotes mapeados, concorrência no orçamento e provas em novas sessões de cada cliente. Fonte: `dados/plataforma-backlog.json`.
Próximo: usar a entrada fixa e comparar recuperação de tarefas antes/depois; implementar apenas a próxima etapa com critério e reversão. Sem commit/push nesta sessão.

'''
edit('memoria/estado/ESTADO.md',lambda old:old.replace('MODO: otimizado\n','MODO: otimizado\n\n'+headline,1) if '## Vigente · 260916 · organização' not in old else old)
block='''<!-- MB:PARA-VOCE:ATUAL:INICIO -->
## PARA VOCÊ
<!-- Nenhuma ação humana obrigatória nesta entrega. Entrada aberta pelo agente. -->
<!-- MB:PARA-VOCE:ATUAL:FIM -->

## HANDOFF vigente · 260916 · plataforma

Feito: auditoria humana/IA, contrato fixo de pastas e respostas, catálogo pesquisável, controle de sensibilidade no dashboard existente, triagem no hook, correções de contexto de subprojeto e saúde de cota, bloco humano vigente.
Verificação e limites: `evidence/260916_plataforma/verificacao-final.json`. O catálogo organiza acesso; o acervo não foi fisicamente migrado. Casos futuros podem corrigir a heurística. Identidade instalada não prova recarga de sessões abertas.
Aberto/próximo: `dados/plataforma-backlog.json`; conferir critérios antes de implementar PLAT-03 a PLAT-08. Preservar funções e links antigos até migração comprovada.
Entrada: `S:\\projetos multi i.a\\MEGA B R A I  N\\00_PARA-VOCE\\INICIO.html`. Análise em `00_PARA-VOCE/260916_plataforma/260916_ANALISE.html`.
Reversão: `evidence/260916_plataforma/REVERTER.md`; comparar hashes antes de restaurar qualquer backup. TRAVADO_POR: livre. Nenhuma mutação git.

'''
edit('memoria/estado/HANDOFF.md',lambda old:old.replace('# HANDOFF — megabrain core\n','# HANDOFF — megabrain core\n\n'+block,1) if '## HANDOFF vigente · 260916 · plataforma' not in old else old)
lesson='''\n## 260916 — catálogo precisa de estado explícito
GATILHO: muitas entregas e sessões dividem uma pasta humana e um HANDOFF acumulado.
LIÇÃO: o primeiro bloco PARA VOCÊ recuperava aprovação já concluída; mover pastas não corrigiria a fonte de estado.
ATALHO: manter uma entrada fixa, ler bloco vigente explícito, registrar origem/estado e testar abrir-copiar-voltar; legados sem prova permanecem não verificados.
'''
edit('memoria/nucleo/licoes-megabrain.md',lambda old:old+lesson if '## 260916 — catálogo precisa de estado explícito' not in old else old)
intro='''# MEGABRAIN · entrada e mapa fixo

Abra [Início](00_PARA-VOCE/INICIO.html) ou `01_acoes/00_ABRIR-MEGABRAIN.vbs`.

- Entregas humanas: `00_PARA-VOCE/`; uma pasta por tarefa.
- Estado atual: `memoria/estado/`; bloco vigente antes do histórico.
- Conhecimento: `memoria/cerebro/`; regras: `memoria/identidade/` e `motor/skills/`.
- Programa: `bin/`, `motor/`, `apps/`; provas e backups: `evidence/`.
- Evolução: `dados/plataforma-backlog.json`; contrato: `motor/referencias/260916_plataforma-contrato.md`.

'''
edit('INDICE.md',lambda old:intro+old.replace('(wiki/260916_amadurecer-uso-e-creditos.md)','(memoria/cerebro/wiki/260916_amadurecer-uso-e-creditos.md)') if '# MEGABRAIN · entrada e mapa fixo' not in old else old)
print('Estado, handoff, índice e lição atualizados sem remover histórico.')
