# Capacidades visuais do agente — roteador (v1, 260901)

Pra que o megabrain use as ferramentas certas em tarefa de imagem, design e
reprodução visual. Lido no Gate 1 (enquadrar) quando a entrega é peça visual,
adaptação de formato, leitura de referência ou geração de imagem. Detalhe e prova:
`memoria/cerebro/wiki/260901_pipeline-ai-para-figma.md`,
`…/260901_obter-imagens-para-o-agente.md`, `…/260901_interpretacao-de-imagem-pelo-agente.md`,
`…/260901_acervo-visual-para-reproducao.md`; imagens em `memoria/cerebro/visual/`.

## 1 · Ordem fixa antes de produzir qualquer imagem

1. Já existe no disco? `ls -lat` na pasta do cliente/projeto. Export 72 ppi é a leitura barata.
2. Existe referência medida no acervo? `memoria/cerebro/visual/<tema>/LEIAME.md`.
3. Se o dado é visual e vai virar decisão, medir (cor, posição, largura) antes de descrever.
4. Só então gerar/expandir/reconstruir.

## 2 · Verbo → ferramenta

| Verbo | Ferramenta | Nota |
|---|---|---|
| Ler PDF, .ai, proposta | `Read` (PDF) · `pymupdf` (texto com baseline, imagens, pranchetas) | .ai = PDF; caminho `S:\` |
| Ler PSD/JPG/PNG grande | PIL miniatura ≤ 900 px → `Read` | original só pra medir |
| Medir cor | PIL `getpixel` em colunas/linhas do export de referência | resultado vira paint/token |
| Medir posição de rosto/objeto | (u,v) normalizado na foto × retângulo da foto no frame | detector local ainda não instalado |
| Medir fonte substituta | Figma: texto temporário por candidato, `width` ÷ largura original | manter tamanho original |
| Construir/editar no Figma | `plugin:figma` `use_figma` (skill `figma:figma-use` antes) | ≤10 ops/chamada; 1 prancheta/chamada; paralelo |
| Subir imagem pro Figma | `upload_assets` → `curl -F` → `imageHash` | apagar o frame solto |
| Exportar do Figma | `get_screenshot` (1× máx.) · preset `exportSettings` pra ≥1× | `exportAsync` 2× não passa pelo canal |
| Hospedar pra Adobe | `asset_initialize_file_upload` → `curl PUT` → `asset_finalize_file_upload` | `adobe_mandatory_init` antes |
| Expandir fundo | Adobe `image_generative_expand` (lados que faltam) · fallback Magnific `images_expand` | conta de pixels na skill estagi_a_rio §4 |
| Recortar fundo, máscara, ajuste tonal, vetorizar | Adobe `image_remove_background`, `image_select_*`, `image_apply_adjustments`, `image_vectorize` | entrada = URL pré-assinada |
| Gerar do zero | Magnific `images_generate` / `images_models_list` | texto e logo nunca por IA |
| Comparar versões | PIL lado a lado, mesma altura, rótulo em cima | guardar no acervo |
| Peça fixa (poster, deck) do zero | Adobe `create_visual_design_express_skill` (HTML → Express) | perguntar destino antes |
| Referência de UI viva | Chrome MCP + `getComputedStyle` (lição 260804) | número, não adjetivo |

## 3 · Armadilhas já pagas
- `gradientTransform` do Figma é a inversa (lição 260901); radial: `sx=0.5/rx, tx=0.5−cx·sx`.
- `/s/…` do Git Bash quebra MuPDF e PIL; usar `S:/…`.
- `node.query` não aceita acento no seletor.
- Extração de PDF pode vir espelhada; conferir contra o export final.
- Fonte Adobe não existe no Figma remoto; fallback por largura medida.
- Screenshot do Figma renderiza o nó isolado; overlay se valida lendo propriedades.
- Versão nova ao lado da anterior; não mover o que o <USUARIO> mandou ficar.

## 4 · O que ainda não existe (próximo caso real cria)
- Detector de rosto local; endpoint próprio pra hospedar imagens; pastas de UI no acervo
  (`visual/ui-*`), estilos visuais medidos por `getComputedStyle`.
