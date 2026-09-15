# Agentes IA — widget vivo de processos (família Cotas IA)

Painel translúcido que mostra os processos vivos do dono (ZCode, claude, codex)
hospedando o board Agent Flow (`localhost:3001`) dentro de uma janela Qt sem
fundo, frameless, arrastável e redimensionável.

## Uso

- Abrir: `INSTALAR-E-ABRIR.cmd` (ou `launch.vbs`). Fechar a janela **para o server**.
- Arrastar: segure o cabeçalho fino ("Agentes IA"). Redimensionar: alça no canto
  inferior direito. Menu do cabeçalho (botão direito): sempre no topo, salvar
  posição, parar server.
- Névoa branca: slider no cabeçalho (gradiente radial 100→0%, opacidade ajustável).
- Settings: `~/.agentes-ia/settings.json` (posição, tamanho, névoa, topmost).

## Requisitos

- venv do Cotas IA: `apps\ia-quota-widget\.venv` (PySide6 6.11.2 + QtWebEngine).
- Server do board: `bin\mb-board.ps1` / `npx agent-flow-app` (o widget sobe sozinho
  se a porta 3001 estiver livre; se já estiver no ar, adota e fecha ao sair).

## Arquivos

- `agentes_ia_widget.py` — widget (casca + névoa + webview).
- `launch.vbs` / `INSTALAR-E-ABRIR.cmd` — lançadores (pythonw, sem console).
- Teste: `pythonw agentes_ia_widget.py --screenshot print.png --skip-singleton-guard`
