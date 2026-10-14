"""Gera demo.html com todos os ícones de icones.svg (vitrine para escolher)."""
from pathlib import Path
import re
E = Path(__file__).resolve().parent
svg = (E / 'icones.svg').read_text(encoding='utf-8')
nomes = re.findall(r'<symbol id="i-([a-z0-9-]+)"', svg)
cards = ''.join(f'<div class="c"><svg class="ic"><use href="#i-{n}"/></svg><code>{n}</code></div>' for n in nomes)
html = ('<!doctype html><html lang="pt-BR"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
        '<title>Ícones dos relatórios</title><style>body{margin:0;background:#0b0b16;color:#d5d1e5;font:15px system-ui,sans-serif;padding:24px}'
        'h1{color:#fff;font-weight:800;letter-spacing:-.03em}.g{display:grid;grid-template-columns:repeat(auto-fill,minmax(130px,1fr));gap:10px}'
        '.c{background:#191927;border:1px solid #34304a;border-radius:12px;padding:16px;display:grid;justify-items:center;gap:10px}'
        '.ic{width:32px;height:32px;color:#5fd0e6}code{font:12px ui-monospace,monospace;color:#cfc8e6}</style></head><body>'
        + svg + f'<h1>Ícones dos relatórios · {len(nomes)}</h1><div class="g">{cards}</div></body></html>')
(E / 'demo.html').write_text(html, encoding='utf-8')
print(len(nomes), 'ícones')
