"""Recomendadores de livros (filtragem colaborativa), separação por usuário e métricas de acerto do top-N."""
import numpy as np
import pandas as pd
from scipy import sparse
from sklearn.decomposition import TruncatedSVD

from src.config import NOTA_GOSTOU, NOTA_MINIMA_RECOMENDAR, SEMENTE, TAMANHO_LISTA


def matriz_usuario_item(interacoes, usuarios, itens, valor=None):
    """Matriz esparsa usuários × itens (linhas na ordem de `usuarios`, colunas na de `itens`).

    Sem `valor`, cada interação vale 1 (o usuário leu/registrou o livro); com `valor`, usa essa coluna (ex.: a nota).
    Interações de usuários ou itens fora das listas são ignoradas.
    """
    pos_usuario = pd.Series(np.arange(len(usuarios)), index=pd.Index(usuarios))
    pos_item = pd.Series(np.arange(len(itens)), index=pd.Index(itens))
    dados = interacoes[interacoes['id_usuario'].isin(pos_usuario.index) & interacoes['id_obra'].isin(pos_item.index)]
    valores = np.ones(len(dados)) if valor is None else dados[valor].to_numpy(dtype=float)
    return sparse.csr_matrix((valores, (pos_usuario[dados['id_usuario']].to_numpy(),
                                        pos_item[dados['id_obra']].to_numpy())), shape=(len(usuarios), len(itens)))


def separar_por_usuario(interacoes, nota_gostou=NOTA_GOSTOU, proporcoes=(0.6, 0.2, 0.2), min_gostou=5,
                        semente=SEMENTE):
    """Separa os livros de que cada usuário gostou em treino, validação e teste (60/20/20 por usuário).

    Só usuários com pelo menos `min_gostou` livros com nota >= `nota_gostou` entram na validação e no teste (com pelo
    menos 1 livro em cada). As demais interações (notas baixas, sem nota e usuários com poucos livros) ficam no
    treino, porque ainda ensinam ao modelo quais livros são lidos juntos. A base não tem datas, então a separação é
    aleatória dentro de cada usuário. Devolve uma Series ('treino', 'validacao' ou 'teste') alinhada às interações.
    """
    gerador = np.random.default_rng(semente)
    conjunto = pd.Series('treino', index=interacoes.index)
    gostou = interacoes[interacoes['nota'] >= nota_gostou]
    tamanhos = gostou.groupby('id_usuario').size()
    for usuario in tamanhos[tamanhos >= min_gostou].index:
        indices = gerador.permutation(gostou.index[gostou['id_usuario'].to_numpy() == usuario].to_numpy())
        n_val = max(1, round(proporcoes[1] * len(indices)))
        n_teste = max(1, round(proporcoes[2] * len(indices)))
        conjunto[indices[:n_val]] = 'validacao'
        conjunto[indices[n_val:n_val + n_teste]] = 'teste'
    return conjunto


def montar_matrizes(interacoes, conjunto, itens, filtro=None, treino=('treino',), alvo='validacao', valor=None):
    """Matrizes para treinar e avaliar um recomendador.

    - X_treino: todos os usuários × itens, só com as interações dos conjuntos de `treino` (passadas por `filtro`,
      ex.: filtrar_sinal);
    - X_historico: as mesmas interações, só para os usuários avaliados (os que têm livros no conjunto `alvo`);
    - X_alvo: os livros escondidos (conjunto `alvo`) desses usuários.
    """
    base = interacoes[conjunto.isin(treino)]
    base = filtro(base) if filtro is not None else base
    usuarios = np.sort(interacoes['id_usuario'].unique())
    avaliados = np.sort(interacoes.loc[conjunto == alvo, 'id_usuario'].unique())
    return (matriz_usuario_item(base, usuarios, itens, valor), matriz_usuario_item(base, avaliados, itens, valor),
            matriz_usuario_item(interacoes[conjunto == alvo], avaliados, itens))


class Recomendador:
    """Base: `fit(X)` aprende com a matriz usuários × itens; `recomendar` devolve os N itens de maior pontuação."""

    def fit(self, X):
        return self

    def pontuar(self, X_historico):
        raise NotImplementedError

    def recomendar(self, X_historico, n=TAMANHO_LISTA, excluir=None):
        """Índices dos N itens recomendados para cada linha, sem repetir os livros que o usuário já tem.

        `excluir`: índices de livros que nunca entram na lista (ex.: o filtro de qualidade, `livros_mal_avaliados`).
        """
        pontos = np.asarray(self.pontuar(sparse.csr_matrix(X_historico)), dtype=float)
        pontos[sparse.csr_matrix(X_historico).nonzero()] = -np.inf
        if excluir is not None and len(excluir):
            pontos[:, np.asarray(excluir)] = -np.inf
        melhores = np.argpartition(-pontos, n - 1, axis=1)[:, :n]
        ordem = np.argsort(-np.take_along_axis(pontos, melhores, axis=1), axis=1)
        return np.take_along_axis(melhores, ordem, axis=1)


class Aleatorio(Recomendador):
    """Sorteia os livros: o piso de qualquer recomendador."""

    def __init__(self, semente=SEMENTE):
        self.semente = semente

    def fit(self, X):
        self.n_itens = X.shape[1]
        return self

    def pontuar(self, X_historico):
        return np.random.default_rng(self.semente).random((X_historico.shape[0], self.n_itens))


class Popularidade(Recomendador):
    """Recomenda os livros com mais leitores para todo mundo (o "modelo que chuta" de uma livraria)."""

    def fit(self, X):
        self.popularidade = np.asarray((X > 0).sum(axis=0)).ravel().astype(float)
        return self

    def pontuar(self, X_historico):
        return np.tile(self.popularidade, (X_historico.shape[0], 1))


class ItemItem(Recomendador):
    """Modelos lineares item a item: pontuação = histórico do usuário × matriz W (itens × itens).

    W[h, j] diz o quanto ter o livro h aponta para o livro j; por isso cada recomendação se explica pelos livros do
    histórico (`contribuicoes`).
    """

    def pontuar(self, X_historico):
        return np.asarray(X_historico @ self.W)

    def contribuicoes(self, historico, item):
        """Quanto cada livro do histórico (índices) somou à pontuação do `item`."""
        historico = np.asarray(historico)
        return pd.Series(self.W[historico, item], index=historico).sort_values(ascending=False)


class VizinhosItens(ItemItem):
    """Vizinhos mais próximos entre livros (filtragem colaborativa item a item).

    - metrica='cosseno': co-leitores ÷ (raiz do nº de leitores de cada livro + encolhimento). O encolhimento reduz a
      similaridade de pares com poucos leitores em comum;
    - metrica='euclidiana': 1 ÷ (1 + distância euclidiana entre as colunas), como na v1;
    - k: mantém só os k livros mais parecidos com cada livro (None = todos).
    """

    def __init__(self, metrica='cosseno', k=None, encolhimento=0.0):
        self.metrica, self.k, self.encolhimento = metrica, k, encolhimento

    def fit(self, X):
        X = sparse.csr_matrix(X, dtype=float)
        co = (X.T @ X).toarray()
        quadrados = np.diag(co).copy()
        if self.metrica == 'cosseno':
            normas = np.sqrt(quadrados)
            W = co / (np.outer(normas, normas) + self.encolhimento + 1e-12)
        elif self.metrica == 'euclidiana':
            distancia = np.sqrt(np.maximum(quadrados[:, None] + quadrados[None, :] - 2 * co, 0))
            W = 1 / (1 + distancia)
        else:
            raise ValueError("metrica deve ser 'cosseno' ou 'euclidiana'")
        np.fill_diagonal(W, 0)
        if self.k is not None and self.k < W.shape[0]:
            corte = np.partition(W, -self.k, axis=0)[-self.k]  # k-ésima maior similaridade de cada coluna
            W = np.where(W >= corte[None, :], W, 0)
        self.W = W
        return self


class FatoracaoSVD(ItemItem):
    """Fatoração da matriz (SVD truncado): cada livro vira um vetor de `n_componentes` "gostos" latentes.

    W = Vᵀ·V, então um usuário novo é pontuado só pelo histórico, sem retreinar.
    """

    def __init__(self, n_componentes=50, semente=SEMENTE):
        self.n_componentes, self.semente = n_componentes, semente

    def fit(self, X):
        svd = TruncatedSVD(n_components=self.n_componentes, random_state=self.semente).fit(sparse.csr_matrix(X))
        self.W = svd.components_.T @ svd.components_
        np.fill_diagonal(self.W, 0)
        return self


class EASE(ItemItem):
    """EASE (Steck, 2019): regressão linear que prevê cada livro a partir dos outros, com penalização L2 (lambda).

    Solução fechada: P = (XᵀX + λI)⁻¹ e W = -P / diag(P), com diagonal zero (um livro não explica a si mesmo).
    """

    def __init__(self, lambda_=500.0):
        self.lambda_ = lambda_

    def fit(self, X):
        X = sparse.csr_matrix(X, dtype=float)
        G = (X.T @ X).toarray() + self.lambda_ * np.eye(X.shape[1])
        P = np.linalg.inv(G)
        self.W = -P / np.diag(P)[None, :]
        np.fill_diagonal(self.W, 0)
        return self


def livros_mal_avaliados(interacoes, itens, nota_minima=NOTA_MINIMA_RECOMENDAR):
    """Índices dos livros com nota média (só notas explícitas das `interacoes`) abaixo de `nota_minima`.

    É o filtro de qualidade: na base, o livro com mais leitores (Wild Animus, distribuído de graça) tem nota 4,4, e a
    filtragem colaborativa o recomendaria por ser muito "lido". Passe só as interações de treino para não vazar.
    """
    media = interacoes[interacoes['explicita']].groupby('id_obra')['nota'].mean().reindex(itens)
    return np.flatnonzero(media.to_numpy() < nota_minima)


def avaliar_recomendador(modelo, X_historico, X_alvo, n=TAMANHO_LISTA, popularidade=None, excluir=None):
    """Métricas do top-N para os usuários avaliados (uma linha de X_historico/X_alvo por usuário).

    - acerto@N: % de usuários com pelo menos 1 livro escondido na lista;
    - precisão@N: dos N recomendados, quantos o usuário gostou;
    - recall@N: dos livros escondidos de que gostou, quantos a lista encontrou;
    - NDCG@N: como o recall, mas vale mais acertar no topo da lista (1 = acertos todos no topo);
    - cobertura: % do catálogo que aparece em alguma lista;
    - popularidade média: % de leitores que os livros recomendados têm (alta = recomenda só best-sellers).
    Devolve o resumo (dict) e as métricas por usuário (DataFrame).
    """
    X_alvo = sparse.csr_matrix(X_alvo)
    listas = modelo.recomendar(X_historico, n, excluir)
    acertos = np.take_along_axis(X_alvo.toarray() > 0, listas, axis=1)
    n_alvo = np.asarray(X_alvo.getnnz(axis=1))
    descontos = 1 / np.log2(np.arange(2, n + 2))
    dcg = (acertos * descontos).sum(axis=1)
    idcg = np.array([descontos[:min(k, n)].sum() for k in n_alvo])
    por_usuario = pd.DataFrame({'acertos': acertos.sum(axis=1), 'n_escondidos': n_alvo,
                                'recall': acertos.sum(axis=1) / np.maximum(n_alvo, 1),
                                'ndcg': dcg / np.maximum(idcg, 1e-12)})
    resumo = {f'acerto@{n}': float((por_usuario['acertos'] > 0).mean()),
              f'precisão@{n}': float(acertos.mean()), f'recall@{n}': float(por_usuario['recall'].mean()),
              f'ndcg@{n}': float(por_usuario['ndcg'].mean()),
              'cobertura': float(len(np.unique(listas)) / X_alvo.shape[1])}
    if popularidade is not None:
        resumo['popularidade média'] = float(np.asarray(popularidade)[listas].mean())
    return resumo, por_usuario


def explicar_recomendacao(modelo, historico, item, nomes=None):
    """Livros do histórico que mais puxaram a recomendação do `item` (só para modelos item a item).

    Devolve a contribuição de cada livro e a sua fração no total positivo; `nomes` troca índices por títulos.
    """
    contribuicao = modelo.contribuicoes(historico, item)
    tabela = pd.DataFrame({'contribuição': contribuicao,
                           'fração': contribuicao.clip(lower=0) / max(contribuicao.clip(lower=0).sum(), 1e-12)})
    if nomes is not None:
        tabela.index = [nomes[i] for i in tabela.index]
    return tabela


def comparar_lista(modelo, X_historico, X_alvo, linha, nomes, n=TAMANHO_LISTA, excluir=None):
    """Lista recomendada para um usuário (linha), marcando os livros escondidos de que ele gostou (gabarito)."""
    lista = modelo.recomendar(X_historico[linha], n, excluir)[0]
    escondidos = set(sparse.csr_matrix(X_alvo)[linha].indices)
    return pd.DataFrame({'livro recomendado': [nomes[i] for i in lista],
                         'gostou (escondido)?': ['✅' if i in escondidos else '' for i in lista]},
                        index=pd.RangeIndex(1, n + 1, name='posição'))


def recomendar_para_leitor(modelo, escolhidos, n_itens, n=TAMANHO_LISTA, excluir=None):
    """Recomendações para um leitor novo a partir dos índices dos livros de que ele gostou (sem retreinar)."""
    historico = sparse.csr_matrix((np.ones(len(escolhidos)), (np.zeros(len(escolhidos), dtype=int), escolhidos)),
                                  shape=(1, n_itens))
    return modelo.recomendar(historico, n, excluir)[0]


def acerto_por_livros_informados(modelo, X_historico, X_alvo, quantidades=(1, 2, 3, 5, 10), n=TAMANHO_LISTA,
                                 excluir=None, semente=SEMENTE):
    """Acerto@N quando o modelo vê só k livros do histórico de cada usuário (sorteados), como um leitor no app.

    Para cada k, entram os usuários com pelo menos k livros no histórico (nenhum = acerto vazio); os livros
    escondidos (X_alvo) continuam sendo o gabarito. Devolve uma tabela com k, o número de usuários e o acerto@N.
    """
    gerador = np.random.default_rng(semente)
    X_historico, X_alvo = sparse.csr_matrix(X_historico), sparse.csr_matrix(X_alvo)
    linhas = []
    for k in quantidades:
        usuarios = np.flatnonzero(X_historico.getnnz(axis=1) >= k)
        if len(usuarios) == 0:
            linhas.append({'livros informados': k, 'usuários': 0, f'acerto@{n}': np.nan})
            continue
        escolhidos = [gerador.choice(X_historico[u].indices, size=k, replace=False) for u in usuarios]
        parcial = sparse.csr_matrix((np.ones(len(usuarios) * k), (np.repeat(np.arange(len(usuarios)), k),
                                                                   np.concatenate(escolhidos))),
                                    shape=(len(usuarios), X_historico.shape[1]))
        resumo, _ = avaliar_recomendador(modelo, parcial, X_alvo[usuarios], n, excluir=excluir)
        linhas.append({'livros informados': k, 'usuários': len(usuarios), f'acerto@{n}': resumo[f'acerto@{n}']})
    return pd.DataFrame(linhas).set_index('livros informados')
