# 260813 — Aspirador de código do megabrain

Ferramenta: `bin/mb-aspirador.py`.

Função: varrer um diretório de código e apontar sujeira mecânica segura —
espaços no fim de linha, linhas em branco excessivas, tabs misturados com
espaços, quebras de linha mistas e imports não usados (Python).

## Princípio não destrutivo

- **Dry-run por padrão.** Sem `--aplicar`, o script só lê e relata.
- **Backup obrigatório.** Com `--aplicar`, o arquivo original é copiado para
  `.mb-aspirador/backups/<timestamp>/` antes de qualquer alteração.
- **Nunca apaga arquivos.** Arquivos vazios ou binários são reportados, não
  removidos.
- **Nunca muda lógica, nomes ou comentários.** Apenas ajustes mecânicos.

## Uso

```bash
python bin/mb-aspirador.py --dir ./meu-projeto
python bin/mb-aspirador.py --dir ./meu-projeto --aplicar
python bin/mb-aspirador.py --dir ./meu-projeto --ext py,js,ts
```

## O que detecta

| Tipo | Descrição | Corrige? |
|---|---|---|
| `trailing-whitespace` | espaços no final da linha | sim |
| `linhas-branco-fim` | mais de uma linha vazia no final do arquivo | sim |
| `tabs-mistos` | tab em arquivo que já usa espaços | sim |
| `quebra-mista` | CRLF e LF misturados | sim |
| `import-nao-usado` | import Python não referenciado | não (reportar e revisar) |
| `syntax-error` | arquivo Python com erro de sintaxe | não (revisar manualmente) |
| `nao-texto` | arquivo binário | não |

## Saída

- Markdown: `.mb-aspirador/relatorio-YYYYMMDD-HHMMSS.md`
- HTML: `.mb-aspirador/relatorio-YYYYMMDD-HHMMSS.html`

O HTML é autocontido (CSS inline), traz metadados para IA (`<meta>` e JSON-LD),
resumo em cards, tabela de arquivos, snippets com a linha problemática
destacada, documentação da ferramenta embutida e anexa notas locais `.md`/`.txt`
encontradas em `.mb-aspirador/` (exceto env files, relatórios antigos e
arquivos maiores que 100 KB). A documentação do projeto vive no relatório DNA,
não no relatório do aspirador.
