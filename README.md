# 📚 Sistema de Recomendação de Livros

Um recomendador que sugere a cada leitor **10 livros** que ele ainda não leu, a partir do que leitores com gosto parecido leram e gostaram, e que **mede quantas vezes acerta**.

<div align="center">
<img src="Imagens/Capa.PNG" width="400px">
</div>

### ✨ Destaques

- 🎯 **40,7% de acerto:** em 4 de cada 10 leitores, pelo menos 1 dos 10 livros recomendados é um livro de que a pessoa gostou, contra **11,9%** de uma vitrine de best-sellers.
- 🔍 **A v1 não funcionava:** a configuração original acertava **3,8%**, praticamente o mesmo que sortear livros (3,5%).
- 💎 **O dado "inútil" era o mais valioso:** as interações sem nota (62% da base), descartadas na v1, foram o maior ganho do modelo.
- 🛡️ **Popularidade não é qualidade:** um filtro tira das listas o livro mais "lido" da base (*Wild Animus*, nota 4,4) sem perder acerto. O app explica cada recomendação.

## 📑 Sumário

1. [Contexto do problema](#1--contexto-do-problema)
2. [Objetivo](#2--objetivo)
3. [Base de dados](#3--base-de-dados)
4. [Estrutura do projeto](#4--estrutura-do-projeto)
5. [Como executar](#5--como-executar)
6. [Etapas do projeto (CRISP-DM)](#6--etapas-do-projeto-crisp-dm)
7. [Principais descobertas da análise exploratória](#7--principais-descobertas-da-análise-exploratória)
8. [Construção da solução](#8--construção-da-solução)
9. [Resultado do modelo](#9--resultado-do-modelo)
10. [App interativo (Streamlit)](#10--app-interativo-streamlit)
11. [O que mudou da v1 para a v2](#11--o-que-mudou-da-v1-para-a-v2)
12. [Insights](#12--insights)
13. [Limites](#13--limites)
14. [Próximos passos](#14--próximos-passos)

## 1. 🏢 Contexto do problema

Uma livraria online tem centenas de milhares de títulos, mas cada cliente vê só alguns na tela. Mostrar a todos os mesmos best-sellers é fácil, porém deixa de fora o que **cada leitor** gostaria de ler. Um sistema de recomendação usa o histórico de milhares de pessoas para sugerir a cada cliente os livros que leitores parecidos com ele leram e gostaram.

## 2. 🎯 Objetivo

Recomendar a cada leitor 10 livros que ele ainda não leu e de que provavelmente vai gostar, e **medir o acerto** contra o que a livraria faria sem modelo: mostrar os mais populares.

**O que conta como acerto:** um livro que o usuário avaliou com **nota 7 ou mais**, escondido do modelo, aparecer entre os 10 recomendados.

## 3. 🗂️ Base de dados

[Book-Crossing Dataset](https://www.kaggle.com/datasets/arashnic/book-recommendation-dataset) (Cai-Nicolas Ziegler, 2004), em três tabelas na pasta `Datasets/`:

| Tabela | Linhas | Colunas usadas |
|---|---|---|
| `Books.csv` | 271.360 ISBNs | título, autor, ano, capa |
| `Ratings.csv` | 1.149.780 interações | usuário, ISBN, nota (**0 = interação sem nota**; 1 a 10 = nota) |
| `Users.csv` | 278.858 usuários | local e idade (só na análise exploratória) |

> ⚠️ A nota 0 **não** é nota ruim: significa que o usuário registrou o livro, mas não avaliou. É 62,3% da base.

## 4. 📁 Estrutura do projeto

```
├── app.py                       # App Streamlit (gerado pela última célula do notebook)
├── Datasets/                    # Books.csv, Ratings.csv, Users.csv
├── docs/
│   └── decisoes_analiticas.md   # Decisões DA-01 a DA-13 (contexto, decisão, alternativas)
├── Imagens/                     # Gráficos usados no README (os da v1 continuam aqui)
├── Model/
│   ├── recomendador_livros.pkl  # Modelo EASE + catálogo + filtro de qualidade
│   └── ficha_modelo.json        # Sinal, lambda, métricas no teste, avisos
├── Notebooks/
│   ├── Sistema de Recomendação - Livros.ipynb        # v1 (original, mantido)
│   └── Sistema de Recomendação - Livros - v2.ipynb   # v2 (CRISP-DM)
├── reports/
│   ├── comparacao_modelos.csv   # Os 6 recomendadores na validação
│   └── busca_hiperparametros.csv
├── src/
│   ├── config.py                # Caminhos, cortes, nota que conta como "gostou"
│   ├── dados.py                 # Leitura, limpeza, obras, interações, catálogo
│   ├── recomendacao.py          # Recomendadores, separação, métricas, explicação
│   ├── estatistica.py           # Testes estatísticos com tamanho do efeito
│   └── avaliacao.py             # Ficha do modelo
├── tests/                       # pytest das funções de src/ e do app
└── requirements.txt
```

## 5. ▶️ Como executar

```bash
# 1. Clonar o repositório
git clone https://github.com/RafaelSilva89/Sistema_de_Recomendacao-Livros.git
cd Sistema_de_Recomendacao-Livros

# 2. Instalar as dependências
pip install -r requirements.txt

# 3. Abrir o notebook v2 e executar todas as células (~8 min; gera Model/ e reports/)
jupyter notebook "Notebooks/Sistema de Recomendação - Livros - v2.ipynb"

# 4. Abrir o app
streamlit run app.py

# 5. Rodar os testes
pytest -v
```

## 6. 🗺️ Etapas do projeto (CRISP-DM)

| Fase | O que foi feito |
|---|---|
| **01. Entendimento do negócio** | Contexto, objetivo e o que conta como acerto |
| **02. Preparação dos dados** | Significado real das colunas, conserto de linhas deslocadas, obra = título + autor, outliers, 8 hipóteses com teste estatístico, catálogo de 642 obras |
| **03. Modelagem** | Separação 60/20/20 por usuário, 6 recomendadores, 5 separações repetidas, busca em grade, filtro de qualidade, tamanho da lista e teste anti-vazamento |
| **04. Avaliação** | Acerto por perfil de leitor e popularidade do livro, exemplos e explicação das recomendações |
| **05. Implantação** | Modelo e ficha salvos, simulação com leitores novos e app Streamlit |

## 7. 🔍 Principais descobertas da análise exploratória

- **62,3% das interações não têm nota**, e 26,1% dos usuários só têm interações sem nota.
- **A nota quase não depende** de quantas notas o livro tem, do país, da idade do leitor ou do ano do livro: todos os efeitos são desprezíveis.
- **Livros são lidos juntos:** entre quem leu *Harry Potter 1*, 41,6% leram o 2; entre os demais, 0,27%.

<div align="center">
<img src="Imagens/Similaridade entre livros.png" width="650px">
</div>

- **Muito lido ≠ bem avaliado:** *Wild Animus* tem quase o dobro de leitores do 2º colocado, mas nota média de 4,39, contra 7,88 dos outros 49 livros mais lidos.

<div align="center">
<img src="Imagens/H8 - Wild Animus.png" width="650px">
</div>

### 🧪 Testes estatísticos

Com centenas de milhares de interações, quase toda diferença tem p-valor minúsculo. **O que importa é o tamanho do efeito, não o p.**

| # | Hipótese | Resultado | Tamanho do efeito |
|---|---|---|---|
| H1 | A maioria das interações não tem nota | ✅ Confirmada | 62,3% (binomial) |
| H2 | Mais notas → nota média maior | ❌ Rejeitada | Spearman 0,046 |
| H3 | Quem avalia mais é mais crítico | ❌ Rejeitada (efeito contrário e pequeno) | Spearman 0,112 |
| H4 | Notas dos EUA são diferentes | ⚠️ Desprezível | Mann-Whitney, postos 0,069 |
| H5 | A idade se relaciona com a nota | ❌ Rejeitada | Spearman 0,023 |
| H6 | Livros recentes têm notas maiores | ❌ Rejeitada | Spearman 0,007 |
| H7 | Quem leu HP 1 lê o 2 | ✅ Confirmada (enorme) | odds ratio 268, V de Cramér 0,491 |
| H8 | Muito lido ≠ bem avaliado | ✅ Confirmada | Mann-Whitney, postos −0,743 |

## 8. 🛠️ Construção da solução

1. **Obras:** título + autor normalizados juntam as edições de um livro sem misturar livros diferentes com o mesmo título.
2. **Catálogo:** as 642 obras com 50 notas ou mais (150.275 interações de 35.339 usuários).
3. **Separação por usuário:** para os 2.311 leitores com 5 ou mais livros de que gostaram, 20% desses livros ficam escondidos para a validação e 20% para o teste.
4. **6 recomendadores** na validação (notas explícitas, como na v1):

<div align="center">
<img src="Imagens/Comparacao dos recomendadores.png" width="800px">
</div>

| Modelo | acerto@10 | Com 5 separações |
|---|---|---|
| Sorteio | 3,5% | 3,5% |
| Popularidade (best-sellers) | 11,1% | 11,4% ± 0,9% |
| Vizinhos euclidianos (**v1**) | 3,8% | 3,5% ± 0,4% |
| Vizinhos por cosseno | 27,2% | 27,8% ± 0,7% |
| Fatoração SVD | 20,2% | 21,2% ± 0,8% |
| **EASE** | **31,1%** | **31,3% ± 0,6%** |

5. **Ajuste fino:** a busca em grade mostrou que **usar também as interações sem nota** é o que mais melhora o modelo (EASE de 31,5% para 36,5% na validação), com lambda = 200.
6. **Filtro de qualidade:** com as interações sem nota, *Wild Animus* entraria em 35,8% das listas. Livros com nota média abaixo de 5 no treino deixam de ser recomendados, e o acerto ainda sobe um pouco (37,5% → 37,9%).
7. **Teste anti-vazamento:** se o modelo visse os livros do teste, o acerto subiria para 58,2%. A separação impede isso.

> **EASE** é uma regressão que aprende, para cada livro, quanto ter lido cada um dos outros aponta para ele. Por ser linear, cada recomendação se explica pelos livros que o leitor já leu.

## 9. 📊 Resultado do modelo

No **teste**, aberto uma única vez:

| Métrica | EASE (modelo final) | Popularidade |
|---|---|---|
| **acerto@10** (leitores com pelo menos 1 acerto) | **40,7%** | 11,9% |
| precisão@10 | 5,5% | 1,4% |
| recall@10 (livros escondidos encontrados) | 26,7% | 6,1% |
| NDCG@10 (acertos no topo da lista) | 0,196 | 0,036 |
| cobertura do catálogo | 84,3% | 8,1% |

<div align="center">
<img src="Imagens/Acerto por tamanho da lista.png" width="650px">
</div>

- **Com uma única vaga na tela**, o modelo acerta para 352 dos 2.311 leitores do teste; a vitrine de populares, para 27.
- **Para quem leu pouco** (até 9 livros no histórico), o acerto é de 38,1%, contra 5,3% da popularidade.
- **Na cauda longa:** o modelo encontra 44,7% dos livros escondidos entre os 50 mais lidos e 16,1% dos menos lidos. A popularidade só recomenda o topo.
- **Quanto mais livros o leitor informa, melhor a lista.** Simulando o app no teste (o modelo vê só k livros de que o usuário gostou):

| Livros informados | EASE | Popularidade |
|---|---|---|
| 1 | **18,3%** | 9,5% |
| 3 | **27,6%** | 9,6% |
| 5 | **30,8%** | 10,7% |
| 10 | **43,5%** | 18,7% |

## 10. 🖥️ App interativo (Streamlit)

O app recebe os livros de que o leitor gostou (busca pelo título na barra lateral) e mostra:

- **10 recomendações com capa**, nota média e número de leitores;
- **o motivo de cada uma**: "porque você gostou de *Angels & Demons*", com a parte da pontuação que veio de cada livro escolhido;
- **o acerto esperado** para o número de livros escolhidos (ex.: 18% com 1 livro, 28% com 3) e quanto ele sobe com mais livros;
- sem livros escolhidos, os mais lidos entre os bem avaliados (sem *Wild Animus*);
- uma aba de **livros parecidos** com um livro escolhido.

```bash
streamlit run app.py
```

## 11. 🔄 O que mudou da v1 para a v2

| Item | v1 | v2 |
|---|---|---|
| Base | "3.150 clientes da Amazon" | Book-Crossing: 278.858 usuários, 1.149.780 interações |
| Nota 0 | Lida como nota ruim e descartada | **Interação sem nota**, usada no treino (maior ganho do modelo) |
| Identificação do livro | Só o título (livros diferentes misturados) | Título + autor normalizados; linhas deslocadas e entidades HTML corrigidas |
| Modelo | Vizinhos com distância euclidiana sobre notas | EASE (comparado com 5 alternativas) |
| Avaliação | Um exemplo (Harry Potter) | Separação 60/20/20 por usuário, acerto@10, 5 separações, teste aberto uma vez |
| Acerto@10 | **3,5%** (medido na v2 com a configuração da v1, igual ao sorteio) | **40,7%** no teste (37,9% ± 0,8% na validação) |
| Livro mal avaliado | Nenhum tratamento | Filtro de qualidade (*Wild Animus* fora das listas) |
| Explicação | Nenhuma | "Porque você gostou de X" e acerto esperado por número de livros informados, no notebook e no app |
| Produção | Nenhuma | Modelo salvo, ficha JSON, app Streamlit, testes e CI |

## 12. 💡 Insights

1. **Medir antes de afirmar:** o exemplo de Harry Potter da v1 parecia ótimo, mas na média o método acertava como um sorteio.
2. **O sinal que parecia lixo era o mais valioso:** as interações sem nota elevaram o acerto do EASE de 31,5% para 36,5%.
3. **Popularidade não é qualidade:** sem o filtro, um livro com nota 4,4 apareceria para mais de um terço dos leitores.
4. **Personalizar vale mais para quem lê pouco:** 38,1% de acerto contra 5,3% da vitrine.
5. **Séries e autores puxam as recomendações:** *Violets Are Blue* é recomendado sobretudo por *Roses Are Red*, o livro anterior da série.

## 13. ⚠️ Limites

- **Base de 2004, sem datas:** o modelo foi avaliado em adivinhar livros escondidos, não em prever o próximo livro.
- **Catálogo de 642 obras:** livros novos ou de nicho precisam de leitores para entrar.
- **Acerto ≠ venda:** o efeito em compras exige um teste A/B.
- **Sem conteúdo:** o modelo não sabe o gênero nem o resumo dos livros.
- **Interações sem nota são ambíguas:** mostram que a pessoa registrou o livro, não que gostou.

## 14. 🚀 Próximos passos

1. Teste A/B na vitrine: EASE × best-sellers.
2. Separação no tempo, quando houver datas.
3. Modelo híbrido (autor, gênero, descrição) para livros sem leitores.
4. Diversidade na lista: no máximo 2 ou 3 livros da mesma série por lista.
5. Publicar o app no Streamlit Community Cloud.
