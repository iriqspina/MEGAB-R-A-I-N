from pathlib import Path
import sys, hashlib
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'bin'))
import mb_trava
agent = 'codex-ponte-b2c2be-n0'
raw = ROOT / 'memoria/cerebro/raw/261020_cursor-pausa-design.md'
digest = hashlib.sha256(raw.read_bytes()).hexdigest()[:16]
entries = {
 'memoria/cerebro/INDICE.md': f'\n## Agrupamento opcional de ações · 261020\n- Página: [Agrupar ações relacionadas](wiki/261020_agrupar-acoes-relacionadas.md).\n- Fonte processada: `raw/261020_cursor-pausa-design.md` · SHA-256 `{digest}` · 261020 · skill agrupar-acoes e wiki.\n',
 'memoria/cerebro/260824_mapa-do-cerebro.md': '\n## Agrupamento opcional · 261020\n- [[261020_agrupar-acoes-relacionadas]] — análise de proximidade sem fundir funções.\n- [[261020_cursor-pausa-design]] — pedido literal do cursor e espera.\n',
 'memoria/nucleo/licoes-megabrain.md': '\n## 261020 — Proximidade visual preserva ações distintas\nGATILHO: agrupar controles relacionados para economizar espaço, como Aguardar retorno e Pausar projeto.\nLIÇÃO: <USUARIO> pediu uma ferramenta opcional de análise, não uma regra universal; semântica, área de clique e efeito real precisam continuar separados.\nATALHO: usar motor/skills/agrupar-acoes/SKILL.md quando pertinente; comparar separado e agrupado, testar acesso e consequência, e nunca inferir retomada pelo silêncio ou pela chegada de retorno.\n',
 'memoria/estado/HANDOFF.md': '\n## 261020 · cursor e espera · ordem b2c2be em andamento\nDESPACHO: Codex 1/GPT n0 coordena; worker GPT n1 executa controle/cursor/relatório em apps/megabrain-dashboard, fonte cursor e evidence/261020_cursor-pausa. Revisor GPT n2 independente lê contrato/skill; todos seguem pipeline congelada gpt-6-astra medium, não representam contas diferentes. N0 escreve skill agrupar-acoes, fonte humana e registros técnicos. Não retomar outras frentes. Escopo/travas e alterações anteriores conferidos; sem git/publicação. Estado final será anexado após testes e prova.\n'
}
for rel, content in entries.items():
    path = ROOT / rel
    marker = content.splitlines()[1]
    if marker not in path.read_text(encoding='utf-8'):
        mb_trava.anexar(path, content, agent, 'pedido cursor e agrupamento opcional', ROOT)
    print(rel)
