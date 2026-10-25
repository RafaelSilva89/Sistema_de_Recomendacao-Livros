import pickle
from pathlib import Path

import streamlit as st

from src.dados import populares_bem_avaliados
from src.recomendacao import explicar_recomendacao, recomendar_para_leitor

st.set_page_config(page_title="Recomendação de Livros", page_icon="📚", layout="wide")
st.title("📚 Recomendação de Livros")
st.markdown("Escolha na barra lateral os livros de que você gostou e receba **10 recomendações** a partir do que "
            "leitores com gosto parecido leram e gostaram.")

CAMINHO_MODELO = Path(__file__).parent / "Model" / "recomendador_livros.pkl"


### Carregamento do modelo
@st.cache_resource
def carregar_modelo(caminho):
    with open(caminho, "rb") as arquivo:
        return pickle.load(arquivo)


if not CAMINHO_MODELO.exists():
    st.error("Modelo não encontrado. Execute o notebook até a Fase 05 para gerar a pasta `Model/`.")
    st.stop()

salvo = carregar_modelo(CAMINHO_MODELO)
modelo, itens, catalogo = salvo["modelo"], salvo["itens"], salvo["catalogo"]
excluir = salvo["excluir"]  # filtro de qualidade: livros com nota média abaixo de 5 (ex.: Wild Animus)
acerto_por_livros = salvo["acerto_por_livros"]  # acerto@10 no teste por nº de livros informados (Fase 04)
titulos = catalogo["titulo"].to_numpy()
rotulos = (catalogo["titulo"] + " — " + catalogo["autor"].fillna("?")).to_numpy()


def mostrar_livros(indices, motivos=None):
    """Capas em 5 colunas, com título, autor, nota média, nº de leitores e (opcional) o motivo da recomendação."""
    colunas = st.columns(5)
    for posicao, item in enumerate(indices):
        livro = catalogo.iloc[item]
        with colunas[posicao % 5]:
            if isinstance(livro["capa_m"], str):
                st.image(livro["capa_m"], width=110)
            st.markdown(f"**{posicao + 1}. {livro['titulo']}**  \n{livro['autor']}  \n"
                        f"⭐ {livro['nota_media']:.1f} · {livro['n_leitores']:,} leitores".replace(",", "."))
            if motivos is not None:
                st.caption(motivos[posicao])


### Livros escolhidos pelo leitor
with st.sidebar:
    st.header("📖 Livros de que você gostou")
    escolhidos = st.multiselect("Busque pelo título", options=list(range(len(itens))), format_func=lambda i: rotulos[i],
                                placeholder="Ex.: Harry Potter")
    st.caption(f"Catálogo: {len(itens)} livros com pelo menos 50 notas na base Book-Crossing (2004).")

aba_voce, aba_parecidos = st.tabs(["🎯 Para você", "🔎 Livros parecidos"])

### Recomendações (EASE: cada livro escolhido soma pontos para os livros lidos junto com ele)
with aba_voce:
    if escolhidos:
        recomendados = recomendar_para_leitor(modelo, escolhidos, len(itens), excluir=excluir)
        motivos = []
        for item in recomendados:
            explicacao = explicar_recomendacao(modelo, escolhidos, item, titulos)
            principais = explicacao[explicacao["fração"] > 0].head(2)
            if principais.empty:
                motivos.append("Lido por leitores com gosto parecido com o seu.")
            else:
                motivos.append("Porque você gostou de " + " e ".join(f"*{titulo}* ({fracao:.0%})"
                                                                     for titulo, fracao in principais["fração"].items()))
        st.subheader(f"Recomendações a partir de {len(escolhidos)} livro(s)")
        # Acerto medido no teste para quem informou até esse número de livros (a faixa mais próxima abaixo)
        faixa = max(k for k in acerto_por_livros if k <= len(escolhidos))
        mensagem = (f"📈 Para leitores que informaram {faixa} livro(s), pelo menos 1 destes 10 foi um livro de que "
                    f"gostaram em **{acerto_por_livros[faixa]:.0%}** dos casos (teste).")
        if faixa < max(acerto_por_livros):
            proxima = min(k for k in acerto_por_livros if k > faixa)
            mensagem += f" Com {proxima} livros, sobe para {acerto_por_livros[proxima]:.0%}: escolha mais livros."
        st.info(mensagem)
        mostrar_livros(recomendados, motivos)
        st.caption("A porcentagem é a parte da pontuação do livro que veio de cada livro que você escolheu.")
        with st.expander("📊 Acerto esperado por número de livros informados"):
            st.dataframe({"livros informados": list(acerto_por_livros),
                          "acerto@10 no teste": [f"{v:.0%}" for v in acerto_por_livros.values()]}, hide_index=True)
    else:
        st.subheader("Mais lidos entre os bem avaliados")
        st.caption("Sem livros escolhidos, mostramos os livros com mais leitores entre os de nota média 7 ou mais.")
        populares = populares_bem_avaliados(catalogo, n=10)
        mostrar_livros([catalogo.index.get_loc(obra) for obra in populares.index])

### Livros parecidos com um livro
with aba_parecidos:
    livro = st.selectbox("Escolha um livro", options=list(range(len(itens))), format_func=lambda i: rotulos[i])
    st.subheader(f"Quem gostou de {titulos[livro]} também leu")
    mostrar_livros(recomendar_para_leitor(modelo, [livro], len(itens), excluir=excluir))
