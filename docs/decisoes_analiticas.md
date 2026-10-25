# Registro de decisões analíticas

Este documento registra as principais decisões do projeto, no formato
**Contexto → Decisão → Alternativas consideradas → Consequência → Onde está**.
Cada decisão tem um código (DA-XX) para ser citada em commits e pull requests.

Os números vêm das saídas do notebook [`Notebooks/Sistema de Recomendação - Livros - v2.ipynb`](../Notebooks/).

| Código | Decisão |
|---|---|
| [DA-01](#da-01--nota-0--interação-sem-nota) | Nota 0 = interação sem nota |
| [DA-02](#da-02--obra--título--autor-normalizados) | Obra = título + autor normalizados |
| [DA-03](#da-03--catálogo-com-50-notas-ou-mais) | Catálogo com 50 notas ou mais |
| [DA-04](#da-04--gostou--nota-7-ou-mais) | "Gostou" = nota 7 ou mais |
| [DA-05](#da-05--separação-602020-por-usuário) | Separação 60/20/20 por usuário |
| [DA-06](#da-06--acerto10-contra-popularidade-e-sorteio) | Acerto@10 contra popularidade e sorteio |
| [DA-07](#da-07--ease-em-vez-dos-vizinhos-euclidianos-da-v1) | EASE em vez dos vizinhos euclidianos da v1 |
| [DA-08](#da-08--treinar-com-todas-as-interações) | Treinar com todas as interações |
| [DA-09](#da-09--filtro-de-qualidade-nota-média--5) | Filtro de qualidade (nota média < 5) |
| [DA-10](#da-10--lista-de-10-livros) | Lista de 10 livros |
| [DA-11](#da-11--explicação-de-cada-recomendação) | Explicação de cada recomendação |
| [DA-12](#da-12--modelo-de-produção-e-leitor-sem-histórico) | Modelo de produção e leitor sem histórico |
| [DA-13](#da-13--acerto-esperado-por-número-de-livros-informados) | Acerto esperado por número de livros informados |

---

## DA-01 — Nota 0 = interação sem nota

- **Contexto:** 62,3% das 1.149.780 interações têm nota 0. A v1 leu isso como nota ruim ("o site está muito ruim para vender livros") e descartou essas linhas. Pela documentação da base Book-Crossing, 0 é uma interação **sem nota**: o usuário registrou o livro, mas não avaliou.
- **Decisão:** tratar a nota 0 como sinal de leitura (coluna `explicita = False`). Só as notas de 1 a 10 dizem se a pessoa gostou.
- **Alternativas consideradas:** descartar (v1); tratar como nota baixa (inverteria o significado).
- **Consequência:** a H1 confirma que essas interações são a maioria (26,1% dos usuários só têm interações sem nota), e elas viram o maior ganho do modelo (DA-08).
- **Onde está:** Fase 02, itens 2.2, 2.5 e H1; `montar_interacoes`.

## DA-02 — Obra = título + autor normalizados

- **Contexto:** a v1 identificava o livro pelo título. Há 6.748 títulos com mais de um autor (*Selected Poems* tem 25), e cada edição tem um ISBN próprio. Além disso, 3 linhas do cadastro tinham título e autor juntos e as colunas deslocadas, e os títulos traziam entidades HTML (`&amp;`).
- **Decisão:** `limpar_livros` conserta as linhas e as entidades; `criar_obras` cria o identificador título + autor em minúsculas, sem pontuação (no autor, também sem espaços: "J.R.R." = "J. R. R."). Quando um usuário tem duas edições da mesma obra, fica a maior nota.
- **Alternativas consideradas:** só o título (v1); só o ISBN (separaria as edições de um mesmo livro).
- **Consequência:** 245.577 obras; 4.430 interações duplicadas por edição foram unidas.
- **Onde está:** Fase 02, itens 2.2 e 4; `limpar_livros`, `criar_obras`, `montar_interacoes`.

## DA-03 — Catálogo com 50 notas ou mais

- **Contexto:** a mediana é de 1 interação por usuário e a matriz é muito esparsa. Livros com poucos leitores não têm co-leitura suficiente para uma similaridade confiável.
- **Decisão:** recomendar só obras com pelo menos 50 notas explícitas (o mesmo corte da v1, escolhido pelo usuário para manter a comparação).
- **Alternativas consideradas:** 20 notas (2.309 obras, catálogo maior, mas com menos dados por livro).
- **Consequência:** 642 obras, 150.275 interações de 35.339 usuários (densidade de 0,662%).
- **Onde está:** Fase 02, item 4; `montar_catalogo`; `config.MIN_NOTAS_CATALOGO`.

## DA-04 — "Gostou" = nota 7 ou mais

- **Contexto:** recomendar um livro que a pessoa leu e detestou não deve contar como acerto.
- **Decisão:** acerto = um livro com nota ≥ 7, escondido do modelo, aparecer na lista (75,3% das notas explícitas). Escolha do usuário.
- **Alternativas consideradas:** qualquer nota explícita (contaria como acerto um livro com nota 2).
- **Consequência:** a nota só define o alvo da avaliação; o modelo aprende com as interações.
- **Onde está:** Fase 01 (formato da solução) e Fase 02, item 2.7; `config.NOTA_GOSTOU`.

## DA-05 — Separação 60/20/20 por usuário

- **Contexto:** a v1 não separava nada. A base não tem datas, então não dá para separar no tempo.
- **Decisão:** para os 2.311 usuários com 5 ou mais livros de que gostaram, esconder 20% desses livros para a validação e 20% para o teste (`separar_por_usuario`). Todas as outras interações ficam no treino, inclusive de usuários não avaliados. O teste é aberto uma única vez, e a validação é repetida com 5 sementes.
- **Alternativas consideradas:** separar usuários inteiros (o modelo não teria histórico para pontuar); deixar um livro de fora por usuário (validação mais ruidosa).
- **Consequência:** 5.037 livros escondidos na validação e 5.037 no teste. O teste anti-vazamento mostra que, sem essa proteção, o acerto subiria de 40,7% para 58,2%.
- **Onde está:** Fase 03, itens 4.1 e 9; `separar_por_usuario`, `montar_matrizes`.

## DA-06 — Acerto@10 contra popularidade e sorteio

- **Contexto:** a v1 mostrava um único exemplo (Harry Potter) e chamava as recomendações de "altamente relevantes".
- **Decisão:** métrica principal = **acerto@10** (% de usuários com pelo menos 1 livro escondido de que gostaram entre os 10 recomendados), com precisão, recall, NDCG, cobertura e popularidade média. A linha de base é a lista de populares (o "modelo que chuta"), junto com o sorteio.
- **Alternativas consideradas:** erro na previsão da nota (RMSE), que mede a nota, não a lista que o leitor vê.
- **Consequência:** a configuração da v1 acerta 3,8%, praticamente o sorteio (3,5%).
- **Onde está:** Fase 03, itens 5 e 6; `avaliar_recomendador`.

## DA-07 — EASE em vez dos vizinhos euclidianos da v1

- **Contexto:** na validação com notas explícitas, o acerto@10 foi de 3,5% (sorteio), 11,1% (popularidade), 3,8% (euclidiano da v1), 27,2% (cosseno), 20,2% (SVD) e 31,1% (EASE). Com 5 sementes, o EASE teve 31,3% ± 0,6%, e o cosseno, 27,8% ± 0,7%.
- **Decisão:** EASE, uma regressão linear item a item com penalização L2 e solução fechada.
- **Alternativas consideradas:** vizinhos por cosseno (mais cobertura, menos acerto); SVD (concentra as listas em menos livros).
- **Consequência:** melhor acerto, pontuação de leitores novos sem retreinar e explicação direta de cada recomendação (DA-11).
- **Onde está:** Fase 03, itens 5 e 6; `EASE`, `VizinhosItens`, `FatoracaoSVD`.

## DA-08 — Treinar com todas as interações

- **Contexto:** a busca em grade testou 3 sinais × 3 modelos × hiperparâmetros na validação.
- **Decisão:** sinal `todas` (incluindo as interações sem nota) e lambda = 200. O melhor EASE subiu de 31,5% (notas explícitas) para 36,5%.
- **Alternativas consideradas:** só "gostou" (o pior sinal nos três modelos); só notas explícitas (v1).
- **Consequência:** com 5 sementes, o acerto foi de 31,3% (EASE original) para 37,5% (ajustado). O efeito colateral levou ao filtro de qualidade (DA-09).
- **Onde está:** Fase 03, itens 7.1 e 7.2; `filtrar_sinal`.

## DA-09 — Filtro de qualidade (nota média < 5)

- **Contexto:** *Wild Animus* é a obra com mais leitores (2.502), mas tem nota média de 4,39, e 77% dos leitores não deram nota (H8). Com o sinal `todas`, o EASE o colocava em 35,8% das listas.
- **Decisão:** livros com nota média abaixo de 5 **no treino** nunca são recomendados (`livros_mal_avaliados`). O filtro bloqueia só *Wild Animus*.
- **Alternativas consideradas:** tirar o livro da base (perderia a co-leitura que ele revela); voltar ao sinal só com notas explícitas (acerto de 31,3% em vez de 37,5%).
- **Consequência:** *Wild Animus* aparece em 0% das listas, e o acerto vai de 37,5% para 37,9%.
- **Onde está:** Fase 03, item 7.2; `livros_mal_avaliados`; `config.NOTA_MINIMA_RECOMENDAR`.

## DA-10 — Lista de 10 livros

- **Contexto:** o modelo não dá probabilidades, então limiar e calibração não se aplicam.
- **Decisão:** medir o acerto para listas de 1 a 20 livros na validação e manter 10.
- **Alternativas consideradas:** 5 livros (27,6% de acerto); 20 livros (46,1%, mas com o dobro de espaço na tela).
- **Consequência:** com 10 livros, 36,7% de acerto na validação, contra 13,1% da popularidade. A vantagem relativa é maior nas listas curtas.
- **Onde está:** Fase 03, item 8; `config.TAMANHO_LISTA`.

## DA-11 — Explicação de cada recomendação

- **Contexto:** a pontuação do EASE é histórico × W. Cada livro do histórico soma W[h, j] à pontuação do livro j.
- **Decisão:** `explicar_recomendacao` mostra a contribuição de cada livro do histórico e a fração no total positivo. O app exibe "porque você gostou de X (%)".
- **Alternativas consideradas:** SHAP ou outro explicador externo (desnecessário num modelo linear).
- **Consequência:** *Violets Are Blue* é recomendado sobretudo por *Roses Are Red* (25,8%), o livro anterior da mesma série.
- **Onde está:** Fase 04, item 3; `ItemItem.contribuicoes`, `explicar_recomendacao`; `app.py`.

## DA-12 — Modelo de produção e leitor sem histórico

- **Contexto:** depois do teste, não há mais motivo para esconder interações do modelo.
- **Decisão:** treinar o modelo de produção com as 150.275 interações do catálogo, com o mesmo sinal, o mesmo lambda e o filtro de qualidade. O pickle guarda o modelo, a ordem dos livros, o catálogo e a lista do filtro, e a ficha JSON guarda as métricas do teste. Quem não escolhe nenhum livro recebe `populares_bem_avaliados`: os mais lidos com nota média ≥ 7.
- **Alternativas consideradas:** usar o modelo de treino + validação (perde os livros do teste); a lista de populares pura (traria *Wild Animus*).
- **Consequência:** o app recomenda para leitores novos sem retreinar, e a lista sem histórico começa por *The Lovely Bones* e *The Da Vinci Code*.
- **Onde está:** Fase 05; `recomendar_para_leitor`, `populares_bem_avaliados`; `Model/`.

## DA-13 — Acerto esperado por número de livros informados

- **Contexto:** os usuários do teste têm históricos longos (todos com 5 ou mais livros de que gostaram), mas no app o leitor escolhe só alguns livros. O acerto de 40,7% não vale para quem informa 1 livro.
- **Decisão:** simular no teste o uso do app (`acerto_por_livros_informados`): o modelo vê só k livros de que o usuário gostou, sorteados do histórico, e precisa achar os escondidos. O resultado vai para o modelo salvo e para a ficha, e o app mostra o acerto esperado para o número de livros escolhidos.
- **Alternativas consideradas:** acerto por tamanho do histórico completo (não corresponde ao que o leitor faz no app); não informar o grau de confiança.
- **Consequência:** 18,3% de acerto com 1 livro (popularidade: 9,5%), 27,6% com 3 e 43,5% com 10. Com 10 livros entram só 646 usuários, os mais ativos. O app avisa quanto o acerto sobe se o leitor escolher mais livros.
- **Onde está:** Fase 04, item 1 ("Acerto esperado por número de livros informados"); `acerto_por_livros_informados`; `app.py`.
