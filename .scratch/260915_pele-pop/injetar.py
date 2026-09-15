"""Injeta <style id="mb-pop-skin"> antes de </head> (idempotente). Uso: injetar.py pele.css alvo.html"""
import re
import sys
from pathlib import Path

css = Path(sys.argv[1]).read_text(encoding="utf-8")
alvo = Path(sys.argv[2])
bruto = alvo.read_bytes()
nl = "\r\n" if b"\r\n" in bruto else "\n"
doc = bruto.decode("utf-8")
doc = re.sub(r'\s*<style id="mb-pop-skin">.*?</style>', "", doc, flags=re.S)
assert doc.count("</head>") == 1, "esperava exatamente um </head>"
bloco = f'<style id="mb-pop-skin">\n{css}</style>\n'.replace("\r\n", "\n").replace("\n", nl)
doc = doc.replace("</head>", bloco + "</head>", 1)
alvo.write_bytes(doc.encode("utf-8"))
print("ok", alvo)
