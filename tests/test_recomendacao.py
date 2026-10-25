"""Testes das funções de src/. Rodar na raiz do projeto: pytest"""
import numpy as np
import pandas as pd
import pytest
from scipy import sparse

from src.dados import (criar_obras, extrair_pais, filtrar_sinal, limpar_livros, montar_catalogo, montar_interacoes,
                       normalizar_texto, populares_bem_avaliados)
from src.estatistica import odds_ratio, regra_iqr, teste_mann_whitney, teste_spearman
from src.recomendacao import (EASE, Aleatorio, FatoracaoSVD, Popularidade, VizinhosItens,
                              acerto_por_livros_informados, avaliar_recomendador, comparar_lista,
                              explicar_recomendacao, livros_mal_avaliados, matriz_usuario_item, montar_matrizes,
                              recomendar_para_leitor, separar_por_usuario)


def livros_exemplo():
    return pd.DataFrame({
        'isbn': ['1', '2', '3', '4'],
        'titulo': ['Angels &amp; Demons', 'Angels & Demons (Paperback)', 'The Hobbit', 'Creating the X-Men\\";Michael T"'],
        'autor': ['Dan Brown', 'Dan Brown', 'J. R. R. Tolkien', '2000'],
        'ano': ['2000', '2001', '1937', 'DK Publishing'],
        'editora': ['Pocket', 'Pocket', 'Houghton', 'url_p'],
        'capa_p': ['p1', 'p2', 'p3', 'url_m'], 'capa_m': ['m1', 'm2', 'm3', 'url_g'], 'capa_g': ['g1', 'g2', 'g3', None]})


def test_limpar_livros_conserta_deslocadas_e_entidades():
    livros = limpar_livros(livros_exemplo())
    assert livros.loc[0, 'titulo'] == 'Angels & Demons'
    deslocada = livros.loc[3]
    assert deslocada['titulo'] == 'Creating the X-Men' and deslocada['autor'] == 'Michael T'
    assert deslocada['ano'] == 2000 and deslocada['editora'] == 'DK Publishing' and deslocada['capa_g'] == 'url_g'


def test_criar_obras_junta_variacoes_de_texto_do_autor():
    livros = criar_obras(limpar_livros(livros_exemplo()))
    assert livros.loc[0, 'id_obra'] == 'angels demons | danbrown'
    assert livros.loc[2, 'id_obra'] == criar_obras(pd.DataFrame({'titulo': ['The Hobbit'], 'autor': ['J.R.R. Tolkien']}))['id_obra'][0]
    assert normalizar_texto(pd.Series(['  The  Lovely Bones: A Novel! '])).iloc[0] == 'the lovely bones a novel'


def test_montar_interacoes_fica_com_a_maior_nota_da_obra():
    livros = criar_obras(pd.DataFrame({'isbn': ['a', 'b', 'c'], 'titulo': ['X', 'X', 'Y'], 'autor': ['Z', 'Z', 'W']}))
    avaliacoes = pd.DataFrame({'id_usuario': [1, 1, 2, 2], 'isbn': ['a', 'b', 'c', 'fora'], 'nota': [0, 8, 5, 9]})
    interacoes = montar_interacoes(avaliacoes, livros)
    assert len(interacoes) == 2  # duas edições viram uma obra; o ISBN fora do cadastro sai
    assert interacoes.set_index('id_usuario').loc[1, 'nota'] == 8
    assert interacoes['explicita'].all()


def test_montar_catalogo_aplica_o_corte_de_notas():
    livros = criar_obras(pd.DataFrame({'isbn': ['a', 'b'], 'titulo': ['X', 'Y'], 'autor': ['Z', 'W'], 'ano': [2000, 2001],
                                       'capa_m': ['m', 'm'], 'capa_g': ['g', 'g']}))
    avaliacoes = pd.DataFrame({'id_usuario': [1, 2, 3, 1], 'isbn': ['a', 'a', 'a', 'b'], 'nota': [8, 6, 0, 9]})
    catalogo = montar_catalogo(montar_interacoes(avaliacoes, livros), livros, avaliacoes, min_notas=2)
    assert catalogo.index.tolist() == ['x | z']
    assert catalogo.loc['x | z', 'n_notas'] == 2 and catalogo.loc['x | z', 'n_leitores'] == 3
    assert catalogo.loc['x | z', 'nota_media'] == pytest.approx(7)


def test_filtrar_sinal_e_populares():
    interacoes = pd.DataFrame({'nota': [0, 5, 8], 'explicita': [False, True, True]})
    assert [len(filtrar_sinal(interacoes, s)) for s in ['gostou', 'explicitas', 'todas']] == [1, 2, 3]
    with pytest.raises(ValueError):
        filtrar_sinal(interacoes, 'outro')
    catalogo = pd.DataFrame({'nota_media': [4.4, 8.0, 7.5], 'n_leitores': [900, 100, 300]}, index=['wild', 'b', 'c'])
    assert populares_bem_avaliados(catalogo, n=2).index.tolist() == ['c', 'b']


def test_extrair_pais():
    assert extrair_pais(pd.Series(['nyc, new york, usa', 'porto, , ', 'x, n/a', None])).tolist()[0] == 'usa'
    assert extrair_pais(pd.Series(['porto, , ', 'x, n/a'])).isna().all()


@pytest.fixture
def interacoes_sinteticas():
    """60 usuários em 2 grupos de gosto: o grupo A lê os livros 0-4, o grupo B lê os livros 5-9."""
    gerador = np.random.default_rng(0)
    linhas = []
    for usuario in range(60):
        livros = range(5) if usuario < 30 else range(5, 10)
        for livro in livros:
            if gerador.random() < 0.9:
                linhas.append({'id_usuario': usuario, 'id_obra': f'L{livro}', 'nota': int(gerador.integers(7, 11))})
    interacoes = pd.DataFrame(linhas)
    interacoes['explicita'] = True
    return interacoes


def test_separar_por_usuario_60_20_20(interacoes_sinteticas):
    conjunto = separar_por_usuario(interacoes_sinteticas, min_gostou=5, semente=1)
    por_usuario = interacoes_sinteticas.groupby('id_usuario').size()
    for usuario, grupo in conjunto.groupby(interacoes_sinteticas['id_usuario']):
        contagem = grupo.value_counts()
        if por_usuario[usuario] >= 5:
            assert contagem['validacao'] == 1 and contagem['teste'] == 1
        else:
            assert set(grupo) == {'treino'}
    assert conjunto.equals(separar_por_usuario(interacoes_sinteticas, min_gostou=5, semente=1))


@pytest.mark.parametrize('modelo', [VizinhosItens('cosseno'), VizinhosItens('cosseno', k=3, encolhimento=1),
                                    VizinhosItens('euclidiana'), FatoracaoSVD(n_componentes=2), EASE(lambda_=1)])
def test_modelos_recomendam_livros_do_mesmo_grupo(interacoes_sinteticas, modelo):
    itens = np.array([f'L{i}' for i in range(10)])
    conjunto = separar_por_usuario(interacoes_sinteticas, min_gostou=5, semente=1)
    X_treino, X_hist, X_alvo = montar_matrizes(interacoes_sinteticas, conjunto, itens, alvo='teste')
    modelo.fit(X_treino)
    listas = modelo.recomendar(X_hist, n=2)
    assert not any(X_hist[linha, item] for linha, lista in enumerate(listas) for item in lista)  # nunca repete
    resumo, por_usuario = avaliar_recomendador(modelo, X_hist, X_alvo, n=2)
    resumo_sorteio, _ = avaliar_recomendador(Aleatorio().fit(X_treino), X_hist, X_alvo, n=2)
    assert resumo['acerto@2'] > resumo_sorteio['acerto@2'] and resumo['acerto@2'] > 0.8
    assert len(por_usuario) == X_alvo.shape[0]


def test_avaliar_recomendador_calcula_as_metricas():
    class Fixo(Popularidade):
        def pontuar(self, X_historico):
            return np.tile([3.0, 2.0, 1.0, 0.0], (X_historico.shape[0], 1))

    X_hist = sparse.csr_matrix(np.zeros((2, 4)))
    X_alvo = sparse.csr_matrix(np.array([[1, 0, 0, 1], [0, 0, 0, 1]]))
    resumo, por_usuario = avaliar_recomendador(Fixo(), X_hist, X_alvo, n=2, popularidade=[0.5, 0.3, 0.1, 0.1])
    assert resumo['acerto@2'] == 0.5 and resumo['precisão@2'] == 0.25 and resumo['recall@2'] == 0.25
    assert por_usuario.loc[0, 'ndcg'] == pytest.approx(1 / (1 + 1 / np.log2(3)))
    assert resumo['cobertura'] == 0.5 and resumo['popularidade média'] == pytest.approx(0.4)


def test_explicacao_soma_a_pontuacao_e_leitor_novo(interacoes_sinteticas):
    itens = np.array([f'L{i}' for i in range(10)])
    usuarios = np.sort(interacoes_sinteticas['id_usuario'].unique())
    modelo = EASE(lambda_=1).fit(matriz_usuario_item(interacoes_sinteticas, usuarios, itens))
    recomendados = recomendar_para_leitor(modelo, [0, 1], len(itens), n=3)
    assert set(recomendados) <= {2, 3, 4}
    explicacao = explicar_recomendacao(modelo, [0, 1], recomendados[0], nomes=itens)
    historico = sparse.csr_matrix(([1.0, 1.0], ([0, 0], [0, 1])), shape=(1, 10))
    assert explicacao['contribuição'].sum() == pytest.approx(modelo.pontuar(historico)[0, recomendados[0]])
    assert explicacao['fração'].sum() == pytest.approx(1) and set(explicacao.index) == {'L0', 'L1'}
    tabela = comparar_lista(modelo, historico, sparse.csr_matrix(([1.0], ([0], [recomendados[0]])), shape=(1, 10)),
                            0, itens, n=3)
    assert tabela.iloc[0]['gostou (escondido)?'] == '✅'


def test_filtro_de_qualidade_bloqueia_livros_mal_avaliados(interacoes_sinteticas):
    itens = np.array([f'L{i}' for i in range(10)])
    interacoes = interacoes_sinteticas.copy()
    interacoes.loc[interacoes['id_obra'] == 'L2', 'nota'] = 3  # L2: muito lido, mas mal avaliado
    sem_nota = pd.DataFrame({'id_usuario': [99], 'id_obra': ['L5'], 'nota': [0], 'explicita': [False]})
    bloqueados = livros_mal_avaliados(pd.concat([interacoes, sem_nota]), itens, nota_minima=5)
    assert bloqueados.tolist() == [2]  # a interação sem nota não entra na média
    usuarios = np.sort(interacoes['id_usuario'].unique())
    modelo = EASE(lambda_=1).fit(matriz_usuario_item(interacoes, usuarios, itens))
    assert 2 in recomendar_para_leitor(modelo, [0, 1], len(itens), n=3)
    assert 2 not in recomendar_para_leitor(modelo, [0, 1], len(itens), n=3, excluir=bloqueados)


def test_acerto_por_livros_informados(interacoes_sinteticas):
    itens = np.array([f'L{i}' for i in range(10)])
    conjunto = separar_por_usuario(interacoes_sinteticas, min_gostou=5, semente=1)
    X_treino, X_hist, X_alvo = montar_matrizes(interacoes_sinteticas, conjunto, itens, alvo='teste')
    tabela = acerto_por_livros_informados(EASE(lambda_=1).fit(X_treino), X_hist, X_alvo, quantidades=(1, 2, 3, 4), n=2)
    assert tabela.index.tolist() == [1, 2, 3, 4]
    assert tabela.loc[1, 'usuários'] == X_alvo.shape[0]  # todo avaliado tem pelo menos 1 livro no histórico
    assert tabela.loc[4, 'usuários'] == 0 and np.isnan(tabela.loc[4, 'acerto@2'])  # ninguém tem 4 no histórico
    assert tabela['acerto@2'].dropna().between(0, 1).all() and tabela.loc[3, 'acerto@2'] > 0.8


def test_testes_estatisticos_com_tamanho_de_efeito():
    a, b = np.arange(10, 30), np.arange(0, 20)
    assert teste_mann_whitney(a, b)['tamanho do efeito'] > 0
    assert teste_spearman(a, a ** 2)['tamanho do efeito'] == pytest.approx(1)
    assert odds_ratio([1, 1, 1, 0, 0, 0, 1, 0], [1, 1, 0, 0, 0, 1, 1, 0]) == pytest.approx(9)  # (3·3) ÷ (1·1)
    assert regra_iqr(pd.Series([1, 2, 3, 4, 100]))['outliers'] == 1
