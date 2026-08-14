# Usar o megabrain offline

A pasta `MEGABRAIN/` dentro de um projeto é uma **cópia local completa** do
protocolo. Ela funciona sozinha — não depende de internet, GitHub nem de
qualquer repositório remoto.

## Quando usar este modo

- Você está sem internet.
- O GitHub está fora do ar.
- Você não quer/pode clonar o repositório público.
- Você copiou o projeto de outra máquina e só quer continuar trabalhando.

## O que funciona offline

Todos os scripts dentro de `MEGABRAIN/bin/` rodam localmente:

- `mb-sync.py` — trava/libera o `HANDOFF.md` do projeto.
- `mb-sync-memoria.py` — sincroniza seu perfil de identidade para
  `CLAUDE.md`/`GEMINI.md`/`AGENTS.md`.
- `mb-aspirador.py` — limpa e revisa código local.
- `mb-relatorio-projeto.py` — gera o relatório de projeto.
- `mb-relatorio-dna.py` — gera o relatório DNA do protocolo.

As referências em `MEGABRAIN/referencias/` e o DNA em `MEGABRAIN/dna/` também
estão disponíveis localmente.

## O que NÃO funciona offline

- `mb-check-version.py --verificar-git` — precisa consultar o remote.
- Atualizações automáticas vindo do repositório público.

Nesses casos o script avisa e continua usando a cópia local.

## Como atualizar quando a internet voltar

1. Se você tem a central do megabrain no disco:
   ```
   python MEGABRAIN/bin/mb-check-version.py --projeto "caminho/do/projeto"
   ```
2. Se a central também veio do git e está desatualizada:
   ```
   cd <pasta-da-central>
   git pull origin main
   python bin/mb-check-version.py --projeto "caminho/do/projeto"
   ```
3. Se você só tem o projeto (sem central separada), copie a pasta
   `MEGABRAIN/` de um projeto atualizado por cima da sua.

## Backup da central

Para não depender só do GitHub, faça backups periódicos da pasta central:

```
cd <pasta-central-do-megabrain>
python bin/mb-backup-central.py
```

O backup vai para `.mb-backup/central-YYYYMMDD-HHMMSS.zip`. Guarde esse
zip em outro lugar (HD externo, nuvem, outra máquina).

## Recuperar um projeto se a central sumir

Se a pasta `MEGABRAIN/` do projeto foi apagada/corrompida, recrie a partir
de outra fonte:

```
# De um backup zip:
python MEGABRAIN/bin/mb-recuperar-megabrain.py \
  --projeto "caminho/do/projeto" \
  --fonte "caminho/do/backup.zip"

# De outro projeto que ainda tenha MEGABRAIN/:
python MEGABRAIN/bin/mb-recuperar-megabrain.py \
  --projeto "caminho/do/projeto" \
  --fonte "outro/projeto/MEGABRAIN"

# Sem --fonte, ele tenta achar sozinho (central, outro projeto na mesma
# pasta, ou backup mais recente):
python MEGABRAIN/bin/mb-recuperar-megabrain.py \
  --projeto "caminho/do/projeto"
```

## Dica: mantenha o `MEGABRAIN/` do projeto atualizado

Sempre que tiver internet, rode o `mb-check-version.py` nos seus projetos.
Assim a cópia local fica fresca e você não fica dependendo do remoto na
hora do trabalho.
