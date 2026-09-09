"""Place a human-facing artifact in the project's single inbox, without overwriting."""
import argparse
from datetime import datetime
from pathlib import Path
import shutil


def entregar(projeto, origem, nome=None):
    projeto = Path(projeto).resolve(strict=True)
    origem = Path(origem).resolve(strict=True)
    if not origem.is_file() or not origem.is_relative_to(projeto):
        raise ValueError('A origem precisa ser um arquivo do projeto')
    pasta = (projeto / '00_PARA-VOCE').resolve()
    if not pasta.is_relative_to(projeto):
        raise ValueError('A pasta de entrega sai do projeto')
    nome = nome or origem.name
    if Path(nome).name != nome or '/' in nome or '\\' in nome:
        raise ValueError('Nome precisa ser simples, sem diretórios')
    if not (len(nome) > 7 and nome[:6].isdigit() and nome[6] == '_'):
        nome = datetime.now().strftime('%y%m%d_') + nome
    destino = pasta / nome
    pasta.mkdir(exist_ok=True)
    if origem == destino:
        return destino
    with destino.open('xb') as out, origem.open('rb') as src:
        shutil.copyfileobj(src, out)
    return destino


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--projeto', required=True)
    parser.add_argument('--origem', required=True)
    parser.add_argument('--nome')
    args = parser.parse_args()
    print(entregar(args.projeto, args.origem, args.nome))
