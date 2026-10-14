"""Monta exemplo.html (autocontido) colando os dois componentes centrais no lugar dos marcadores."""
import pathlib
aqui = pathlib.Path(__file__).resolve().parent
cf = (aqui.parent / '261010_cursor-ferramentas' / 'cursor-ferramentas.js').read_text(encoding='utf-8')
dr = (aqui / 'decisoes-respondiveis.js').read_text(encoding='utf-8')
for js in (cf, dr):
    assert '</script' not in js.lower()
fonte = (aqui / 'exemplo-fonte.html').read_text(encoding='utf-8')
assert fonte.count('/*{{CF_JS}}*/') == 1 and fonte.count('/*{{DR_JS}}*/') == 1
(aqui / 'exemplo.html').write_text(fonte.replace('/*{{CF_JS}}*/', cf).replace('/*{{DR_JS}}*/', dr), encoding='utf-8')
print(aqui / 'exemplo.html')
