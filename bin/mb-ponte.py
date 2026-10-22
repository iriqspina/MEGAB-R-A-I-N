#!/usr/bin/env python3
"""Ponte MegaBrain pela linha de comando: as IAs da ordem usam isto para abrir
orquestradores e workers, esperar por eles e concluir a ordem.

Só biblioteca padrão; a lógica mora em apps/megabrain-dashboard/central_bridge.py.

  python mb-ponte.py vendors                         IAs ativas neste MegaBrain
  python mb-ponte.py despachar --ordem DIR --pai n0 --papel worker --vendor gpt --titulo T --tarefa-arquivo F
  python mb-ponte.py aguardar --ordem DIR --nos n1,n2 [--timeout 3600]
  python mb-ponte.py estado --ordem DIR [--json]
  python mb-ponte.py concluir --ordem DIR --status corrigido --resumo TEXTO [--prova X] [--pendencia Y]
  python mb-ponte.py parar --ordem DIR
  python mb-ponte.py iniciar --projeto RAIZ --vendor gpt --texto "pedido" [--modo janela]
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'apps' / 'megabrain-dashboard'))
import central_bridge as ponte  # noqa: E402

try:
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
except (AttributeError, ValueError):
    pass


def _imprimir(valor, como_json: bool) -> None:
    if como_json:
        print(json.dumps(valor, ensure_ascii=False, indent=2))
    else:
        print(valor)


def _arvore(est: dict) -> str:
    filhos: dict = {}
    for no in est['nos']:
        filhos.setdefault(no.get('pai'), []).append(no)
    linhas = [f"Ordem {est['ordem_id']} · {est['situacao']} · planejador {est['nome_vendor']} · {est['ativos']} rodando"]

    def desce(pai, nivel):
        for no in filhos.get(pai, []):
            marca = no.get('status_observado') or no.get('status')
            linhas.append(f"{'  ' * nivel}- {no['id']} {no['papel']} [{no['nome_vendor']}] {marca}: {no.get('titulo') or ''}")
            desce(no['id'], nivel + 1)
    desce(None, 1)
    if est.get('resultado'):
        linhas.append(f"Resultado: {est['resultado'].get('status')} · {est['resultado'].get('resumo')}")
    return '\n'.join(linhas)


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog='mb-ponte', description='Ponte MegaBrain: planejador → orquestradores → workers.')
    sub = p.add_subparsers(dest='cmd', required=True)

    s = sub.add_parser('vendors', help='IAs ativas neste MegaBrain')
    s.add_argument('--json', action='store_true')

    s = sub.add_parser('despachar', help='abre um orquestrador, worker ou revisor')
    s.add_argument('--ordem', required=True)
    s.add_argument('--pai', required=True)
    s.add_argument('--papel', required=True, choices=['orquestrador', 'worker', 'revisor'])
    s.add_argument('--vendor', help='sobreposição explícita; ausente herda o papel da pipeline')
    s.add_argument('--modelo', help='modelo explícito, validado no catálogo')
    s.add_argument('--effort', help='esforço nativo explícito, validado para o modelo')
    s.add_argument('--titulo', required=True)
    g = s.add_mutually_exclusive_group(required=True)
    g.add_argument('--tarefa')
    g.add_argument('--tarefa-arquivo')
    s.add_argument('--esperar', action='store_true', help='bloqueia até o nó terminar')
    s.add_argument('--timeout', type=int, default=ponte.TIMEOUT_PADRAO)
    s.add_argument('--json', action='store_true')

    s = sub.add_parser('aguardar', help='espera nós terminarem e mostra o resultado de cada um')
    s.add_argument('--ordem', required=True)
    s.add_argument('--nos', required=True, help='lista separada por vírgula, ex.: n1,n2')
    s.add_argument('--timeout', type=int, default=ponte.TIMEOUT_PADRAO)

    s = sub.add_parser('estado', help='árvore da ordem')
    s.add_argument('--ordem', required=True)
    s.add_argument('--json', action='store_true')

    s = sub.add_parser('concluir', help='registra o resultado da ordem')
    s.add_argument('--ordem', required=True)
    s.add_argument('--status', required=True, choices=['corrigido', 'parcial', 'falhou'])
    s.add_argument('--resumo', required=True)
    s.add_argument('--prova', action='append', default=[])
    s.add_argument('--pendencia', action='append', default=[])

    s = sub.add_parser('parar', help='pede para todos os nós ativos pararem')
    s.add_argument('--ordem', required=True)

    s = sub.add_parser('iniciar', help='abre uma ordem nova sem passar pelo app')
    s.add_argument('--projeto', required=True)
    s.add_argument('--vendor', required=True)
    s.add_argument('--texto', required=True)
    s.add_argument('--modo', default='segundo_plano', choices=list(ponte.MODOS))
    s.add_argument('--coordenacao', default='')

    s = sub.add_parser('_supervisionar')
    s.add_argument('--no', required=True)
    s = sub.add_parser('_marcar')
    s.add_argument('--no', required=True)
    s.add_argument('--status')
    s.add_argument('--rc', type=int)

    a = p.parse_args(argv)
    try:
        if a.cmd == 'vendors':
            lista = ponte.vendors()
            if a.json:
                _imprimir(lista, True)
            else:
                for v in lista:
                    print(f"{'✓' if v['ativo'] else '·'} {v['id']:7} {v['nome']} ({v['cli']}) — {v['motivo']}{' ' + v['aviso'] if v['aviso'] else ''}")
        elif a.cmd == 'despachar':
            tarefa = a.tarefa if a.tarefa is not None else Path(a.tarefa_arquivo).read_text(encoding='utf-8-sig')
            no = ponte.despachar(a.ordem, a.pai, a.papel, a.vendor, a.titulo, tarefa, esperar=a.esperar, timeout=a.timeout,
                                 modelo=a.modelo, effort=a.effort)
            if a.json:
                _imprimir(no, True)
            else:
                print(f"{no['id']} {no['papel']} [{no['vendor']} · {no.get('modelo')} · {no.get('effort')}] {no['status']}: {no['titulo']}")
                if a.esperar:
                    est = ponte.estado_ordem(a.ordem)
                    alvo = next(n for n in est['nos'] if n['id'] == no['id'])
                    print(alvo.get('resumo') or alvo.get('saida') or '(sem saída)')
        elif a.cmd == 'aguardar':
            ids = [x.strip() for x in a.nos.split(',') if x.strip()]
            limite = time.monotonic() + a.timeout
            while True:
                est = ponte.estado_ordem(a.ordem)
                alvo = [n for n in est['nos'] if n['id'] in ids]
                faltando = set(ids) - {n['id'] for n in alvo}
                if faltando:
                    raise ponte.PonteErro('Nó inexistente: ' + ', '.join(sorted(faltando)))
                pendentes = [n for n in alvo if n['status'] in {'criado', 'iniciando', 'rodando'} and not n.get('status_observado')]
                if not pendentes or time.monotonic() > limite:
                    break
                time.sleep(5)
            for n in alvo:
                print(f"== {n['id']} {n['papel']} [{n['nome_vendor']}] {n.get('status_observado') or n['status']} (saída {n.get('exit_code')}) · {n.get('titulo')}")
                print((n.get('resumo') or n.get('saida') or '(sem saída)').strip())
                print()
            if pendentes:
                print('Tempo de espera esgotado; nós ainda rodando: ' + ', '.join(n['id'] for n in pendentes))
                return 2
        elif a.cmd == 'estado':
            est = ponte.estado_ordem(a.ordem)
            _imprimir(est if a.json else _arvore(est), a.json)
        elif a.cmd == 'concluir':
            r = ponte.concluir(a.ordem, a.status, a.resumo, a.prova, a.pendencia)
            print(f"Ordem concluída: {r['status']}. O app MegaBrain atualiza o comentário em alguns segundos.")
        elif a.cmd == 'parar':
            print('Pedido de parada: ' + (', '.join(ponte.parar(a.ordem)) or 'nenhum nó ativo'))
        elif a.cmd == 'iniciar':
            info = ponte.criar_ordem(a.projeto, [dict(id='cli-' + time.strftime('%y%m%d%H%M%S'), at=ponte.agora(), texto=a.texto)],
                                     a.vendor, modo=a.modo, coordenacao=a.coordenacao, origem='linha-de-comando')
            ponte.iniciar_planejador(info['dir'], a.modo)
            print(f"Ordem {info['ordem_id']} aberta com o planejador {a.vendor}: {info['dir']}")
        elif a.cmd == '_supervisionar':
            ponte.supervisionar(a.no)
        elif a.cmd == '_marcar':
            ponte.marcar(a.no, a.status, a.rc)
    except ponte.PonteErro as erro:
        print('ponte: ' + str(erro), file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
