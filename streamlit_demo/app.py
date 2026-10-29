"""Démo web de Jarvis pour Streamlit Cloud.

Version texte uniquement : pas de micro, pas de wake word, pas d'outils ni
d'actions réelles (N1/N2/N3 désactivés). N'importe rien du dépôt, donc pas de
sounddevice. La clé vit dans les secrets Streamlit, jamais dans le code.
"""
import streamlit as st
from openai import OpenAI

MODELE = st.secrets.get("OPENAI_MODEL", "gpt-4o-mini")
SYSTEME = (
    "Tu es Jarvis, un assistant vocal francophone. Réponds en français, de "
    "façon brève et naturelle. Tu es en mode démonstration web : tu n'as "
    "accès à aucun outil ni action réelle."
)

st.set_page_config(page_title="Jarvis", page_icon="🤖")
st.title("Jarvis — démo web")
st.caption("Mode texte, sans outils. La version complète tourne en local sur Windows.")

cle = st.secrets.get("OPENAI_API_KEY")
if not cle:
    st.error("Secret `OPENAI_API_KEY` manquant : ajoutez-le dans Settings > Secrets.")
    st.stop()

client = OpenAI(api_key=cle)
if "messages" not in st.session_state:
    st.session_state.messages = []

for m in st.session_state.messages:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])

if question := st.chat_input("Parle à Jarvis…"):
    st.session_state.messages.append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.markdown(question)
    with st.chat_message("assistant"):
        try:
            flux = client.chat.completions.create(
                model=MODELE,
                messages=[{"role": "system", "content": SYSTEME}, *st.session_state.messages[-20:]],
                stream=True,
            )
            reponse = st.write_stream(
                c.choices[0].delta.content or "" for c in flux if c.choices
            )
        except Exception as e:
            reponse = f"Erreur du fournisseur : {type(e).__name__}"
            st.error(reponse)
    st.session_state.messages.append({"role": "assistant", "content": reponse})
