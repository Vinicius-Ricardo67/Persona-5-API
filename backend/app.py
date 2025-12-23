import streamlit as st
import requests

st.set_page_config(
    page_title="Busca Persona 5 Básica",
    layout="centered",
    initial_sidebar_state="collapsed"
)

API_URL = "http://127.0.0.1:8000"

st.markdown("""
<style>
.stTextInput > div > div > input {
    font-size: 1.4rem;
    padding: 10px;
}
</style>
""", unsafe_allow_html=True)


def fetch_persona_basic(persona_name):
    try:
        response = requests.get(f"{API_URL}/persona/basic/{persona_name}")
        response.raise_for_status()
        return response.json()
    except requests.exceptions.HTTPError:
        st.warning("Persona não encontrada.")
    except Exception as e:
        st.error(f"Erro ao conectar com a API: {e}")
    return None


st.title("🔎 Busca Rápida de Persona")

with st.form(key="search_form"):
    search_query = st.text_input(
        "Digite o nome da Persona",
        placeholder="Ex: Arsene, Pixie, Jack Frost",
        label_visibility="collapsed"
    )
    submit = st.form_submit_button("Buscar")

if submit and search_query:
    st.markdown("---")

    with st.spinner(f"Buscando {search_query}..."):
        persona = fetch_persona_basic(search_query)

    if persona:
        col1, col2 = st.columns([1, 2])

        with col1:
            if persona.get("image"):
                st.image(persona["image"], use_container_width=True)
            else:
                st.info("Imagem não encontrada")

        with col2:
            st.header(persona["name"])
            st.write(f"Fonte na Wiki: **{persona['source']}**")
