"""Recibos de notas já recebidas, independentes do armazenamento do aparelho."""
import json
import re


def note_receipts(store, project, fid, digest):
    # Inclui resolvidos: esconder da fila não apaga o recibo nem autoriza reenvio.
    # A consulta não usa listing(), cujo limite serve à interface, não ao histórico.
    with store.db() as connection:
        rows = connection.execute(
            "SELECT data FROM comments WHERE project=? AND json_extract(data,'$.target')=? ORDER BY rowid",
            (project, 'file:' + fid))
        received = []
        for row in rows:
            comment = json.loads(row['data'])
            feedback = comment.get('feedback')
            if not isinstance(feedback, dict):
                continue
            notes = feedback.get('notas', [])
            if not isinstance(notes, list):
                continue
            for note in notes:
                if (not isinstance(note, dict) or not isinstance(note.get('id'), str)
                        or not note['id'] or not isinstance(note.get('texto', ''), str)):
                    continue
                version = note.get('versao')
                if not isinstance(version, str) or not re.fullmatch('[a-f0-9]{64}', version):
                    version = comment.get('source_hash')
                if version != digest:
                    continue
                value=dict(id=note['id'], texto=note.get('texto', ''),
                           versao=digest, anexos=note.get('attachment_details', []))
                if isinstance(note.get('rota'),dict):
                    value['rota']={key:note['rota'][key] for key in ('vendor','modelo','effort') if isinstance(note['rota'].get(key),str)}
                received.append(value)
    return dict(notas=received)
