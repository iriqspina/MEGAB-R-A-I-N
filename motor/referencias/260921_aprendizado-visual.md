# Aprendizado visual verificável — 260921

## Quando carregar
Peça, fotografia, recorte, composição, adaptação de formato ou crítica visual:
rodar `mb-inicio-sessao.py --visual`, ler este protocolo/catálogo e recuperar
somente o caso pertinente com `--caso-visual ID`. Nunca impor o exemplo de
residência a outro projeto. Recuperar o exemplo
pertinente em cerebro/visual. Em conversa simples não iniciar pipeline visual.
Fase: pesquisa → análise → ideação → design. Não editar antes de explicitar o
problema observável e o que precisa continuar reconhecível.

## Primeiro: invariantes do template (correção humana 260921)
Em adaptação de uma matriz existente, congelar tipografia (família, tamanho,
peso, quebra, hierarquia), grade e dinâmica/posição das faixas. Otimizar a foto
DENTRO desses limites. Mais foto ou mais rostos não autorizam reformular layout,
redimensionar textos, criar faixa superior ou alterar quebras sem pedido explícito.
Comparar a fonte humana indicada com o candidato: render + propriedades por nó.
Fidelidade à fonte e reconhecimento do template são critérios obrigatórios,
independentes da narrativa da fotografia. Se houver conflito, preservar a matriz
e propor alternativa delimitada; não impor redesenho por suposto ganho visual.
Revisor deve testar também as invariantes, não apenas rostos, legibilidade e grupo.

Se a revisão técnica passou e <USUARIO> rejeitou, preservar o parecer histórico,
mas marcar a versão REJEITADO_HUMANO e superseded. Não continuar ensinando-a como
exemplo positivo final. Registrar o que a rubrica não viu e comparar a nova cópia
com a fonte humana. Aprovação técnica nunca prevalece sobre a decisão do dono.

## Separar autoria e evidência
- DECISÃO HUMANA: fala literal + data + escopo/formato. Não completar razões que
  <USUARIO> não deu. Aprovação de Spotify não aprova Feed/Stories/YouTube.
- FATO OBSERVADO: imagem inspecionada + versão/hash/frame + região/coordenada.
  Descrever o visível; profissão real, intenção psicológica e especialidade não
  são provadas por uma foto de banco.
- INFERÊNCIA DO AGENTE: hipótese explicativa com efeito esperado e teste visual.
  Uma razão plausível para uma aprovação não vira fala do usuário.

## Ler antes de compor
1. Escrever a narrativa em uma frase observável: quem faz o quê, em relação a
   quem/qual objeto. Mapear protagonista, interlocutor, contexto e objetos que
   sustentam a leitura. Uma pessoa desfocada ainda pode definir grupo/reunião.
2. Marcar no quadro os elementos que precisam continuar reconhecíveis. Recorte
   não é decidido só por centralizar rosto: verificar relação entre pessoas,
   mãos, olhar, objetos e a cena. Corte parcial pode ser consciente e válido.
3. Declarar escala e âncora: aumento proporcional, borda fixa e área resultante.
   Não esticar corpos. Confirmar no render, não apenas no bounding box.
4. Avaliar área útil: cada região de foto/fundo/título tem função? Aumentar foto
   pode resolver contexto neste caso; não existe percentual universal de foto
   nem regra global contra fundo liso. Tipografia e identidade permanecem
   restrições salvo autorização específica.
5. Adaptar por formato. Travar o aprovado. Expansão generativa autorizada de
   ambiente não autoriza gerar/substituir pessoas nem retocar rostos. Conferir
   a foto-base e a região protegida antes/depois; resultado disponível não prova
   preservação. A regra global continua priorizando pessoas fotografadas reais.

## Produzir, revisar, aprender
Antes: salvar render e propriedades da base, frame ID/hash e estado de aceite.
Depois: render por formato, mesma versão inspecionada, comparação lado a lado
quando útil e revisão independente por critério. Registrar também efeito
colateral e o que permaneceu pendente. Métrica geométrica sustenta escala/âncora;
legibilidade narrativa exige inspeção da imagem, não presença de arquivo.

Para cada critério guardar: id, expectativa contextual, resultado
PASSOU/FALHOU/PENDENTE, evidência (imagem/hash/região), observação concreta,
revisor e data. Sem render inspecionado ou com revisão contraditória = PENDENTE,
nunca PASSOU. Estado técnico da revisão é distinto de aprovação humana.

## Regressão visual em trabalhos futuros
Ao iniciar adaptação semelhante, recuperar o caso e aplicar seus critérios ao
novo render, não copiar suas coordenadas/porcentagens. Caso de residência:
`memoria/cerebro/visual/residencia-genetica/260921_caso-regressao.json`.
Os critérios de exemplo são perguntas de revisão com contexto; não são um
classificador automático. Acrescentar nova execução com fonte/resultado/evidência
sem substituir o histórico. Um teste de caminhos/JSON só prova carregamento;
nunca certifica que a imagem comunica reunião, preserva identidade ou agrada.

Erros a capturar: remover contexto desfocado por tratá-lo como ruído; perder
pessoa/objeto que explica a ação; preencher o quadro distorcendo pessoas; reduzir
foto para evitar todo corte; aplicar aprovação de um formato nos demais;
registrar a interpretação do agente como motivo declarado pelo usuário.

## Limite do aprendizado
Isto muda recuperação, critérios e verificações do trabalho dos agentes. Não
altera pesos do modelo nem garante inteligência visual futura. O benefício só
é comprovado em execuções posteriores com erros detectados/corrigidos.
