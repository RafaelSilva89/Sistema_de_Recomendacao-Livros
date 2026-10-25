"""Teste do app Streamlit (precisa do modelo gerado pelo notebook em Model/)."""
import pickle
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
CAMINHO_MODELO = RAIZ / 'Model' / 'recomendador_livros.pkl'
pytestmark = pytest.mark.skipif(not CAMINHO_MODELO.exists(), reason='modelo não gerado (rode o notebook até a Fase 05)')


def posicao_do_livro(inicio):
    with open(CAMINHO_MODELO, 'rb') as arquivo:
        itens = pickle.load(arquivo)['itens']
    return next(i for i, obra in enumerate(itens) if obra.startswith(inicio))


def test_app_sem_historico_mostra_os_populares_bem_avaliados():
    from streamlit.testing.v1 import AppTest

    app = AppTest.from_file(str(RAIZ / 'app.py'), default_timeout=60).run()
    assert not app.exception
    assert app.subheader[0].value == 'Mais lidos entre os bem avaliados'
    assert not any('Wild Animus' in m.value for m in app.markdown)  # muito lido, mas mal avaliado


def test_app_recomenda_e_explica_a_partir_de_harry_potter():
    from streamlit.testing.v1 import AppTest

    app = AppTest.from_file(str(RAIZ / 'app.py'), default_timeout=60).run()
    app.multiselect[0].set_value([posicao_do_livro('harry potter and the sorcerers stone book 1')]).run()
    assert not app.exception
    assert app.subheader[0].value == 'Recomendações a partir de 1 livro(s)'
    motivos = [c.value for c in app.caption if c.value.startswith('Porque você gostou de')]
    assert len(motivos) == 10
    assert 'Para leitores que informaram 1 livro(s)' in app.info[0].value  # acerto esperado (Fase 04)
    assert any('Harry Potter' in m.value for m in app.markdown if m.value.startswith('**1.'))
