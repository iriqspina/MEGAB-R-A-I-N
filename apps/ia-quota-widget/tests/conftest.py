import sys
from pathlib import Path

import pytest

APP_ROOT = Path(__file__).resolve().parent.parent
if str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))


@pytest.fixture(scope="session")
def qt_app():
    # Um unico QApplication pra sessao inteira de teste. QCoreApplication (sem
    # GUI) e QApplication nao podem coexistir no mesmo processo — dois arquivos
    # de teste criando singletons diferentes (um QCoreApplication, outro
    # QApplication) travava o processo no meio da suite. QApplication cobre os
    # dois usos (sinais/threadpool headless E QWidget de verdade).
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication([])
    yield app
