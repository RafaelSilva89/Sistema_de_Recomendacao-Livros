"""Leitura, limpeza e montagem das interações usuário × livro da base Book-Crossing."""
import html

import numpy as np
import pandas as pd

from src.config import (MIN_NOTAS_CATALOGO, NOMES_AVALIACOES, NOMES_LIVROS, NOMES_USUARIOS, NOTA_GOSTOU,
                        NOTA_IMPLICITA, PASTA_DADOS)


def ler_bases(pasta=PASTA_DADOS):
    """Lê as três tabelas (livros, avaliações e usuários) com os nomes das colunas em português."""
    livros = pd.read_csv(pasta / 'Books.csv', dtype=str).rename(columns=NOMES_LIVROS)
    avaliacoes = pd.read_csv(pasta / 'Ratings.csv', dtype={'ISBN': str}).rename(columns=NOMES_AVALIACOES)
    usuarios = pd.read_csv(pasta / 'Users.csv').rename(columns=NOMES_USUARIOS)
    return livros, avaliacoes, usuarios


def limpar_livros(livros):
    """Limpa o cadastro de livros.

    - conserta as linhas em que título e autor vieram juntos ('Título\\";Autor"'): nelas, o ano está na coluna do
      autor, a editora na do ano e as capas uma coluna à esquerda;
    - troca entidades HTML pelo caractere ('Angels &amp; Demons' -> 'Angels & Demons');
    - converte o ano para número (texto inválido vira NaN).
    """
    livros = livros.copy()
    deslocadas = livros['titulo'].str.contains('";', regex=False, na=False)
    partes = livros.loc[deslocadas, 'titulo'].str.split(r'\\?";', n=1, expand=True, regex=True)
    colunas = ['ano', 'editora', 'capa_p', 'capa_m', 'capa_g']
    livros.loc[deslocadas, colunas] = livros.loc[deslocadas, ['autor', 'ano', 'editora', 'capa_p', 'capa_m']].to_numpy()
    livros.loc[deslocadas, 'titulo'] = partes[0].str.strip()
    livros.loc[deslocadas, 'autor'] = partes[1].str.strip('"').str.strip()
    for coluna in ['titulo', 'autor', 'editora']:
        livros[coluna] = livros[coluna].map(html.unescape, na_action='ignore')
    livros['ano'] = pd.to_numeric(livros['ano'], errors='coerce')
    return livros


def normalizar_texto(serie):
    """Minúsculas, só letras/números e espaços simples: 'J. K. Rowling' e 'J.K. Rowling ' viram 'jk rowling'."""
    texto = serie.fillna('').str.lower().str.replace(r'[^a-z0-9 ]', '', regex=True)
    return texto.str.split().str.join(' ')


def criar_obras(livros):
    """Identificador da obra = título + autor normalizados.

    Junta edições do mesmo livro (ISBNs diferentes) sem misturar livros diferentes que têm o mesmo título. No autor,
    os espaços também saem, para 'J.R.R. Tolkien' e 'J. R. R. Tolkien' serem a mesma pessoa ('jrrtolkien').
    """
    livros = livros.copy()
    autor = normalizar_texto(livros['autor']).str.replace(' ', '', regex=False)
    livros['id_obra'] = normalizar_texto(livros['titulo']) + ' | ' + autor
    return livros


def montar_interacoes(avaliacoes, livros):
    """Uma linha por usuário × obra, só com ISBNs do catálogo.

    Se o usuário tem mais de uma edição da mesma obra, fica a maior nota (uma nota explícita vale mais que a
    interação sem nota). A coluna 'explicita' marca as notas de 1 a 10.
    """
    interacoes = avaliacoes.merge(livros[['isbn', 'id_obra']], on='isbn', how='inner')
    interacoes = (interacoes.sort_values('nota', ascending=False)
                  .drop_duplicates(['id_usuario', 'id_obra'])[['id_usuario', 'id_obra', 'nota']]
                  .reset_index(drop=True))
    interacoes['explicita'] = interacoes['nota'] > NOTA_IMPLICITA
    return interacoes


def montar_catalogo(interacoes, livros, avaliacoes, min_notas=MIN_NOTAS_CATALOGO):
    """Obras com pelo menos `min_notas` notas explícitas, com o título, o autor e a capa mais conhecidos.

    Título e capa vêm da edição (ISBN) com mais interações; nota_media e n_notas usam só as notas explícitas.
    """
    explicitas = interacoes[interacoes['explicita']]
    resumo = explicitas.groupby('id_obra')['nota'].agg(n_notas='size', nota_media='mean')
    resumo = resumo[resumo['n_notas'] >= min_notas]
    edicoes = (avaliacoes['isbn'].value_counts().rename('n_isbn').reset_index()
               .merge(livros, on='isbn').sort_values('n_isbn', ascending=False)
               .drop_duplicates('id_obra').set_index('id_obra'))
    catalogo = resumo.join(edicoes[['isbn', 'titulo', 'autor', 'ano', 'capa_m', 'capa_g']], how='left')
    catalogo['n_leitores'] = interacoes[interacoes['id_obra'].isin(catalogo.index)].groupby('id_obra').size()
    return catalogo.sort_values('n_notas', ascending=False)


def filtrar_sinal(interacoes, sinal):
    """Interações que o modelo usa para aprender quais livros são lidos juntos.

    - 'gostou': só as notas >= NOTA_GOSTOU;
    - 'explicitas': todas as notas de 1 a 10 (o que a v1 usava);
    - 'todas': também as interações sem nota (nota 0), que a v1 descartava.
    """
    if sinal == 'gostou':
        return interacoes[interacoes['nota'] >= NOTA_GOSTOU]
    if sinal == 'explicitas':
        return interacoes[interacoes['explicita']]
    if sinal == 'todas':
        return interacoes
    raise ValueError("sinal deve ser 'gostou', 'explicitas' ou 'todas'")


def populares_bem_avaliados(catalogo, n=10, nota_minima=NOTA_GOSTOU):
    """Lista para quem ainda não tem histórico: os livros com mais leitores entre os de nota média >= nota_minima.

    O filtro da nota evita recomendar livros muito lidos e mal avaliados (ex.: Wild Animus, distribuído de graça).
    """
    return catalogo[catalogo['nota_media'] >= nota_minima].sort_values('n_leitores', ascending=False).head(n)


def extrair_pais(local):
    """Último trecho do campo 'cidade, estado, país', em minúsculas; vazio ou 'n/a' vira NaN."""
    pais = local.fillna('').str.split(',').str[-1].str.strip().str.lower()
    return pais.replace({'': np.nan, 'n/a': np.nan})
