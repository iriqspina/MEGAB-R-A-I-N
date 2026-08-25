# Modelo visual do relatório vivo — tema `console` (260825)

**TL;DR:** o relatório vivo de projeto (`bin/mb-relatorio-projeto.py`) usa o tema `console` por
padrão desde 25/08/2026. O tema anterior (`padrao`, claro/azulado) foi rejeitado pelo usuário e
**não serve mais de referência** para relatório novo.

## Por quê

O `padrao` lia como documento genérico: fundo azul-acinzentado, cantos arredondados, navegação em
pílulas, hierarquia de títulos rasa. Num relatório de 600+ linhas o leitor não achava onde estava.
O `megabrain` (papel quente, rail à esquerda) resolvia a navegação mas trazia um rótulo fixo de
outro projeto no `nav::before` e continuava claro demais para leitura longa em tela.

## O que o `console` fixa

| Eixo | Decisão |
|---|---|
| Ground | escuro (`#0b0e13`), superfícies `#11161d`, hairlines `#232c38` |
| Acento | um só (`#5fd0e6`) — neutro de marca de propósito, serve qualquer projeto |
| Sinais | ok `#4ad295` · atenção `#f0b429` · ruim `#ff6b5e`, só na faixa de versão e no TL;DR |
| Tipo | Inter para texto, mono para rótulo/label; título `clamp(2.1rem,4.6vw,3.7rem)` |
| Forma | raio 0, sem sombra — hierarquia por borda e espaçamento |
| Navegação | rail fixo de 15,5rem à esquerda; vira barra horizontal abaixo de 62rem |
| Hierarquia | h2 seção · h3 acento com régua · h4 branco com régua · h5 mono maiúsculo |
| Impressão | `@media print` inverte para papel e esconde o rail |

## Regras ao mexer nisso

1. O tema é CSS dentro do gerador (`css_console()`), não arquivo solto — o relatório precisa abrir
   como arquivo único, sem rede.
2. `VERSAO_CSS` é concatenado **depois** de `css(tema)`: para vencer a faixa de versão, use
   seletor mais específico (`.wrap .versao-mb--ruim`), não `!important`.
3. Nada de rótulo fixo de projeto em `content:` — foi o defeito do tema `megabrain`.
4. Contraste é responsabilidade do tema, não do `.ps1` do projeto. Se um projeto precisar injetar
   CSS depois de gerar, o tema está errado.
5. Trocar de tema é `--tema console|padrao|megabrain`. Relatório antigo só muda quando for regerado.

Ver `Portfolio/DECISOES.md` 013.
