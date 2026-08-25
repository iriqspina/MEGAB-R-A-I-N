# Especificação: `mb-recuperar-megabrain.py`

## TL;DR

Restaura a pasta `MEGABRAIN/` de um projeto a partir da central, sem depender de "outro projeto" como fonte. Usa fontes em ordem de confiança decrescente, prova que a restauração funcionou e recusa declarar sucesso quando a conferência falha.

---

## 1. Propósito

1.1. `mb-recuperar-megabrain.py` é o caminho de recuperação da cópia magra de projeto (`MEGABRAIN/` com ~143 arquivos, layout plano — medido em `DECISOES.md` §260825z).

1.2. Ele reconstrói essa cópia a partir da central (`<MEGABRAIN_ROOT>/`), usando uma das fontes disponíveis.

1.3. A versão anterior dependia de "outro projeto" como última fonte. Isso obrigava a manter cópias de projeto gordas só para alimentar o restaurador. Esta especificação remove essa fonte (decisão `260825z` em `memoria/estado/DECISOES.md`).

---

## 2. Fontes de restauração (ordem de confiança)

| # | Fonte | O que prova | Quando é usada |
|---|-------|-------------|----------------|
| 1 | **Central viva** | Estado atual da central | `e_central(central)` passa |
| 2 | **Git da central** | Histórico versionado | `.git/` existe e `HEAD` é legível |
| 3 | **`.mb-backup/*.zip`** | Foto datada da central | Zip mais recente em `.mb-backup/` |
| 4 | **`_github/repo-local`** | Estrutura e código (sanitizado) | `VERSAO.txt` existe; sem lições nem identidade |
| 5 | **`.mb-origem.json` do projeto** | Central registrada pelo sync | Arquivo `MEGABRAIN/.mb-origem.json` aponta para uma central válida |

2.1. A fonte **central viva** delega a montagem para `bin/mb-check-version.py`, em vez de copiar a central inteira. Isso evita trazer `_github/`, `90_arquivo/`, `99_to_delete/` e outros conteúdos que não pertencem à cópia de projeto.

2.2. A fonte **_github/repo-local** sempre gera aviso explícito no output: "SANITIZADO — sem lições nem identidade".

2.3. Nenhuma outra pasta de projeto vizinha é fonte válida.

---

## 3. CLI

```text
mb-recuperar-megabrain.py --projeto CAMINHO                # detecta a melhor fonte
mb-recuperar-megabrain.py --projeto CAMINHO --fonte X      # força a fonte X
mb-recuperar-megabrain.py --projeto CAMINHO --listar-fontes  # só lista fontes
```

3.1. `--projeto` (obrigatório): pasta do projeto que contém (ou deve conter) `MEGABRAIN/`.

3.2. `--fonte` (opcional): caminho para uma central, uma pasta `MEGABRAIN/`, ou um arquivo `.zip`.

3.3. `--listar-fontes` (opcional): não restaura; apenas imprime as fontes disponíveis, da mais confiável para a menos.

---

## 4. Algoritmo

4.1. Resolve o caminho absoluto de `--projeto`.

4.2. Resolve a central padrão:
   - Usa a variável de ambiente `MEGABRAIN_CENTRAL`, se definida.
   - Caso contrário, usa o diretório pai de `bin/`.

4.3. Se `--listar-fontes`:
   - Chama `fontes_disponiveis(projeto, central)`.
   - Imprime as fontes ou mensagem de ausência.
   - Retorna `0` se houver fonte; `1` se não houver.

4.4. Se `--fonte` for fornecido:
   - Resolve e verifica se existe.
   - Se não existir, retorna `1` com mensagem de erro.

4.5. Se não houver `--fonte`:
   - Chama `encontrar_fonte(projeto, central)` e retorna `1` se nenhuma fonte for detectada.

4.6. Define `mb_destino = projeto / "MEGABRAIN"` e `base_segura = projeto.resolve()`.

4.7. Executa a restauração conforme o tipo da fonte:
   - **Arquivo `.zip`** → `extrair_zip(fonte, mb_destino, base_segura)`.
   - **Central viva** → delega para `mb-check-version.py --projeto <projeto> --central <fonte> --auto --offline`.
   - **Pasta** → `copiar_pasta(fonte_normalizada, mb_destino, base_segura)`.

4.8. Se a restauração falhar, retorna `1` com orientação para usar `--listar-fontes`.

4.9. Chama `conferir(mb_destino)`.
   - Se passar, imprime o número de arquivos e a versão.
   - Se falhar, imprime cada problema encontrado e retorna `1`.

---

## 5. Funções principais

### 5.1. `detectar_central() -> str`
Retorna o caminho absoluto da central via `MEGABRAIN_CENTRAL` ou via `__file__`.

### 5.2. `listar_backups(central: Path) -> list[Path]`
Lista arquivos `.zip` em `.mb-backup/`, ordenados por `st_mtime` decrescente.

### 5.3. `central_do_ponteiro(projeto: Path) -> Path | None`
Lê `MEGABRAIN/.mb-origem.json` e retorna o campo `central` ou `repo_central`.

### 5.4. `fontes_disponiveis(projeto: Path, central: Path) -> list[tuple[str, Path, str]]`
Retorna tuplas `(rótulo, caminho, prova)` para cada fonte encontrada, na ordem de confiança da tabela da seção 2.

### 5.5. `encontrar_fonte(projeto: Path, central: Path) -> Path | None`
Retorna o caminho da primeira fonte disponível.

### 5.6. `conferir(destino: Path) -> tuple[bool, list[str]]`
Verifica:
- A pasta existe.
- `VERSAO.txt` existe e não está vazio.
- `VERSAO.txt` contém uma linha reconhecível (`" · v"`).
- `MEGABRAIN.md` existe e não está vazio.
- Há pelo menos 5 arquivos no destino.

Retorna `(True, [])` se tudo passar; `(False, problemas)` caso contrário.

### 5.7. `copiar_pasta(src: Path, dst: Path, base: Path) -> bool`
- Verifica se `dst` está contido em `base`.
- Remove `dst` antigo com `safe_rmtree`.
- Copia via `shutil.copytree`.
- Retorna `True` se bem-sucedido.

### 5.8. `extrair_zip(zip_path: Path, dst: Path, base: Path) -> bool`
- Verifica se `dst` está contido em `base`.
- Remove `dst` antigo.
- Detecta se o zip contém a central (`bin/` + `referencias/`/`motor/referencias/`) ou uma pasta `MEGABRAIN/`.
- Extrai apenas os membros sob o prefixo correto, validando cada caminho contra `base`.
- Extrai para diretório temporário dentro de `dst.parent` e move os arquivos para o destino final.

### 5.9. `normalizar_fonte(fonte: Path, central: Path) -> Path | None`
Aceita:
- Arquivo `.zip`.
- Pasta central: contém `bin/` e `referencias/`.
- Pasta `MEGABRAIN/`: contém `VERSAO.txt`.
Retorna `None` se a fonte não se encaixar em nenhum caso.

---

## 6. Formato de saída

6.1. Em caso de sucesso:
   ```text
   MEGABRAIN/ escrito em <caminho>
   CONFERIDO: <n> arquivo(s) · versão <versão>
   ```

6.2. Em caso de falha na conferência:
   ```text
   MEGABRAIN/ escrito em <caminho>
   RESTAURAÇÃO INCOMPLETA — não declaro sucesso:
     ✗ <problema 1>
     ✗ <problema 2>
   ```

6.3. Em caso de ausência de fontes:
   ```text
   ERRO: não consegui detectar uma fonte automaticamente.
   Dica: --listar-fontes mostra o que existe.
   ```

---

## 7. Segurança

7.1. Todo caminho de destino é verificado contra `base_segura = projeto.resolve()` via `resolve_within`.

7.2. `safe_rmtree` só remove árvores contidas em `base_segura`.

7.3. Arquivos de zip são extraídos para diretório temporário e movidos um a um; caminhos que sairiam da área permitida são pulados.

7.4. O script nunca sobrescreve fora de `projeto/MEGABRAIN/`.

---

## 8. Integração

8.1. **Backup**: `bin/mb-backup-central.py` cria os zips consumidos pela fonte 3.

8.2. **Sync**: `bin/mb-check-version.py` monta a cópia de projeto a partir da central viva (fonte 1).

8.3. **Ponteiro**: `bin/mb-sync*.py` escreve `MEGABRAIN/.mb-origem.json` para ativar a fonte 5.

8.4. **Testes**: `motor/tests/test_mb_recuperar.py` cobre conferência, ordem das fontes, ausência de "outro projeto", leitura do ponteiro e detecção de central viva.

---

## 9. Critérios de aceitação

9.1. `--listar-fontes` mostra apenas as fontes que existem no disco, na ordem correta.

9.2. Restaurar a partir de uma central viva produz uma cópia plana (`MEGABRAIN/` com os arquivos certos, não a central inteira).

9.3. Restaurar a partir de um zip traz a estrutura correta, tanto se o zip for da central quanto se for de uma pasta `MEGABRAIN/`.

9.4. Restaurar a partir de `_github/repo-local` funciona, mas o output avisa que é sanitizado.

9.5. Uma restauração com `VERSAO.txt` vazio, `MEGABRAIN.md` ausente ou menos de 5 arquivos é reprovada por `conferir()` e retorna código `1`.

9.6. Nenhuma pasta de outro projeto é aceita como fonte.

9.7. A suíte de testes `motor/tests/test_mb_recuperar.py` passa.
