"""Consultar a esteira ou salvar uma escolha explícita de sensibilidade."""
import argparse, json, sys
from pathlib import Path
from mb_triagem import classificar, ler_config, salvar_config
def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--projeto',type=Path,default=Path(__file__).resolve().parents[1])
    p.add_argument('--prompt',default=''); p.add_argument('--context-json',default='{}')
    p.add_argument('--sensibilidade'); p.add_argument('--salvar',action='store_true')
    a=p.parse_args()
    try:
        if a.salvar:
            if not a.sensibilidade: p.error('--salvar exige --sensibilidade')
            result=salvar_config(a.projeto,a.sensibilidade)
        else: result=classificar(a.prompt,a.sensibilidade or ler_config(a.projeto)['sensibilidade'],json.loads(a.context_json))
        print(json.dumps(result,ensure_ascii=False,indent=2)); return 0
    except (ValueError,OSError) as exc: print(str(exc),file=sys.stderr); return 2
if __name__=='__main__': raise SystemExit(main())
