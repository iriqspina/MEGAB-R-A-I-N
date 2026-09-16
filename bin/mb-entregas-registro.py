import argparse,json
from pathlib import Path
from mb_entregas_registro import registrar
p=argparse.ArgumentParser(description='Registrar metadados de uma entrega existente.')
p.add_argument('--projeto',required=True,type=Path);p.add_argument('--item',required=True,type=Path)
a=p.parse_args()
print(registrar(a.projeto,json.loads(a.item.read_text(encoding='utf-8-sig'))))
