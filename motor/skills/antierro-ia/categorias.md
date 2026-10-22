# categorias.md — taxonomia estável (slugs)

Slug nunca muda. Novo padrão → novo slug ou entra como exemplo do existente.
Formato de cada entrada: **slug** — definição em 1 linha · exemplos (IA · evidência).

1. **edicao-de-arquivo** — escrever em arquivo causa efeito invisível além do alvo.
   - CRLF→LF no arquivo inteiro ao trocar 1 linha (ZCode/GLM-5.3 · Portfolio licoes 261019).
   - Append em .md que perde linhas do fim (IA NÃO VERIFICADA · memória do projeto).
   - Normalização "por precaução" de .cmd muda quebras (ZCode · licao 260913).

2. **teste-do-reparo** — reparo declarado feito sem teste que exercite o reparo.
   - "5 reparos, 3/3 OK" com 2 reparos mortos (ZCode · veredito Claude 261019).
   - Teste que nunca falha (caminho não exercitado) usado como prova (ZCode · resumo_mudancas 261019).

3. **leitura-de-imagem** — agir como se tivesse visto imagem que não viu.
   - Read de PNG só faz upload CDN, sem exibir (ZCode · corpus A.1, reproduzido 2× em 261019).
   - Analisador externo alucinou termo do próprio prompt (ZCode+4.5v · corpus A.1).

4. **verificacao-visual** — conferir entrega visual sem olhar o render (ou olhando pedaço).
   - QA com print só da 1ª dobra (21% da página) (ZCode · parecer Claude Parte 1.b).
   - Print parcial lido como página inteira (Kimi K2.7 · licao 565).

5. **entrega-visual** — acabamento/composição abaixo do padrão do projeto.
   - Grid quebrado, etiqueta ilustração em print real, emoji no lugar da biblioteca
     de ícones, dead class, hierarquia de headings fora de ordem (ZCode · pares 261019).

6. **interpretacao-de-termo** — termo do <USUARIO> lido sem confirmar, com consequência.
   - "img2" (ZCode · pausa 261019): resolvido por descrição dos anexos por IA com visão.

7. **registro-e-evidencia** — documento afirma o que o disco não prova; horário/prova fake.
   - "Figma PENDENTE" em docs após feito (ZCode · veredito D).
   - Horários com placeholder "19:2x"/"19:5x" (ZCode · pares 261019).
   - "entregue" sem artefato (licao 260906).

8. **afirmacao-sem-prova** — frase factual sem evidência citada.
   - "igual à produção", "roteiro já existe" sem medição/arquivo (ZCode · parecer Claude P1/P2).

9. **contagem** — número afirmado ≠ número real.
   - 136 candidatos confundidos com 134 supressões (GLM · 261009).
   - "189 entradas" em arquivo com 100 medidas (GLM · 261019).

10. **escopo-e-roteamento** — ação além do pedido, ou peça despachada para IA errada.
    - Desligar Local sob leitura não confirmada do termo (ZCode · veredito E.1, mitigado por reversibilidade).
    - Peça visual nova por GLM contra preferência "Claude/Codex criam" (coordenador · CLAUDE central).

11. **vies-de-confirmacao** — decidir/evidenciar a favor da própria hipótese.
    - Opção do executor pré-destacada em caixa de decisão (ZCode · parecer Claude P1-3).

13. **referencia-nao-batida** — construir/editar/afirmar sem conferir as referências vigentes ANTES de fazer.
   - Regra de ícone (biblioteca, nunca emoji) conferida só nos h2; botões seguiram com ✓ ↩ ✎ e seta ↓ (ZCode · print do <USUARIO> 261019 noite).
   - Frase escrita sem bater na fonte (afirmacao-sem-prova é a consequência; a causa é esta).

12. **shell-e-ambiente** — Windows/Git Bash/caminhos/permissões mordendo a execução.
    - PermissionError em arquivo oculto lido por outro processo (ZCode · corpus A.4).
    - Crases/heredoc comidos; caminho com espaço duplo; stdin pendurado segurando fila
      (ZCode · corpus A.5–A.6, B.7).

## Não é erro de IA (não catalogar como tal)

- Ferramenta/processo: ponte Figma depende do plugin aberto; file:// bloqueado por política;
  Playwright sem headless shell próprio (usa channel:'chrome').
- Conta/crédito: Magnific/Higgsfield sem crédito.
- Plataforma do cliente não renderizar algo — vira erro da IA só quando ela não declara
  nem contorna (verificacao-visual + registro-e-evidencia).
- Decisão de despacho do coordenador (escopo-e-roteamento registra o despacho, não a IA).
