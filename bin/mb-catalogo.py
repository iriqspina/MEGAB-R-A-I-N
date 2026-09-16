import argparse,json,sys
from pathlib import Path
from mb_catalogo import coletar,gerar
def main():
    p=argparse.ArgumentParser(description='Atualizar a entrada fixa de entregas sem mover arquivos.')
    p.add_argument('--projeto',type=Path,default=Path(__file__).resolve().parents[1]);p.add_argument('--check',action='store_true')
    a=p.parse_args()
    try:
        if a.check: print(json.dumps(coletar(a.projeto),ensure_ascii=False,indent=2))
        else: print(gerar(a.projeto))
        return 0
    except (ValueError,OSError) as exc: print(str(exc),file=sys.stderr);return 2
if __name__=='__main__': raise SystemExit(main())
