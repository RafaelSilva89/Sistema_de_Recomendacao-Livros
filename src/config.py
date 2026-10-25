"""Configurações do projeto: caminhos, nomes das colunas, cortes do catálogo e semente."""
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
PASTA_DADOS = RAIZ / 'Datasets'
PASTA_MODELO = RAIZ / 'Model'
PASTA_REPORTS = RAIZ / 'reports'
PASTA_IMAGENS = RAIZ / 'Imagens'

SEMENTE = 42
SEMENTES_VALIDACAO = [42, 7, 123, 2024, 31]  # separações repetidas: média ± desvio das métricas

# Nome original (Book-Crossing) -> nome em português
NOMES_LIVROS = {'ISBN': 'isbn', 'Book-Title': 'titulo', 'Book-Author': 'autor', 'Year-Of-Publication': 'ano',
                'Publisher': 'editora', 'Image-URL-S': 'capa_p', 'Image-URL-M': 'capa_m', 'Image-URL-L': 'capa_g'}
NOMES_AVALIACOES = {'User-ID': 'id_usuario', 'ISBN': 'isbn', 'Book-Rating': 'nota'}
NOMES_USUARIOS = {'User-ID': 'id_usuario', 'Location': 'local', 'Age': 'idade'}

# Nota 0 = interação SEM nota (o usuário registrou o livro, mas não avaliou); notas de 1 a 10 são explícitas
NOTA_IMPLICITA = 0
NOTA_GOSTOU = 7          # nota >= 7: o usuário gostou do livro (é o que o recomendador tenta acertar)
MIN_NOTAS_CATALOGO = 50  # o catálogo tem só livros com pelo menos 50 notas explícitas (mesmo corte da v1)
MIN_GOSTOU_AVALIACAO = 5  # usuários com pelo menos 5 livros de que gostaram entram na avaliação
TAMANHO_LISTA = 10       # o recomendador devolve 10 livros
NOTA_MINIMA_RECOMENDAR = 5  # filtro de qualidade: livros com nota média abaixo disso nunca são recomendados
