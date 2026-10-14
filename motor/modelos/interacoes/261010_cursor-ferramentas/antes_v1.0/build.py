"""Monta demo.html (página autocontida) colando cursor-ferramentas.js no lugar de /*{{CF_JS}}*/."""
import pathlib
aqui = pathlib.Path(__file__).resolve().parent
js = (aqui / 'cursor-ferramentas.js').read_text(encoding='utf-8')
assert '</script' not in js.lower()
fonte = (aqui / 'demo-fonte.html').read_text(encoding='utf-8')
assert fonte.count('/*{{CF_JS}}*/') == 1
(aqui / 'demo.html').write_text(fonte.replace('/*{{CF_JS}}*/', js), encoding='utf-8')
print(aqui / 'demo.html')
