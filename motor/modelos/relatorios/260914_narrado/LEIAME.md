# 260914_narrado — modelo de relatório narrado

**O que é:** deck HTML autocontido (PowerPoint comentado) com narração,
legenda sincronizada, modo guiado, 3 temas de cor e animações de entrada.
Nasceu da entrega aprovada `Portfolio/00_PARA-VOCE/260914_RELACAO-GERAL-APRESENTACAO/`
e da revisão Fable médio de 14/09 (bugs T1–T3 já corrigidos NESTES modelos).

**Duas variantes (regra 260914: baratear — a LEVE é o padrão):**

| variante | arquivo | narração | custo | quando |
| --- | --- | --- | --- | --- |
| **LEVE** (padrão) | `MODELO-relatorio-narrado-LEVE.html` | voz do próprio navegador (Web Speech, offline, grátis); sem voz → leitura cronometrada | **zero** | dia a dia, rascunhos, tudo que não é grande decisão |
| **PREMIUM** (exceção) | `MODELO-relatorio-narrado.html` + `narr_NN.mp3` | TTS cloud pt-BR gravado | TTS + eventual revisão | decisão importante, terceiros, voz do sistema decepcionou |

**Mínimo para funcionar:**
- LEVE: copiar o 1 arquivo, preencher `═══ EDITE`, abrir. Sem passo de áudio.
- PREMIUM: HTML + mp3 (texto idêntico ao `NARR`) na MESMA pasta.
- Ambos: pasta em `00_PARA-VOCE/`; conferir nomes de classe únicos (lição T1).

Skill de uso: `motor/skills/relatorio-narrado/SKILL.md` (passos, regras, lições).

