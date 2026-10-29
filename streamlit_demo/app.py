"""Jarvis web (Streamlit Cloud) : texte + voix navigateur + outils N1 en lecture seule.

Aucune action sensible (N2/N3), aucun accès matériel, micro serveur, domotique,
finances ou mémoire. N'importe rien du dépôt. Les clés vivent dans les secrets
Streamlit, jamais dans le code.
"""
import ast
import io
import json
import operator
from datetime import datetime
from zoneinfo import ZoneInfo

import requests
import streamlit as st
from openai import OpenAI

SYSTEME = (
    "Tu es Jarvis, un assistant vocal francophone. Réponds en français, de "
    "façon brève et naturelle. Tu es en version web : tu disposes seulement "
    "des outils de lecture fournis (heure, météo, calcul). Tu ne peux piloter "
    "ni maison, ni PC, ni envoyer de messages."
)

# ---------- Outils N1 (lecture seule) ----------
_OPS = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
        ast.Div: operator.truediv, ast.Pow: operator.pow, ast.USub: operator.neg,
        ast.Mod: operator.mod}


def _eval(n):
    if isinstance(n, ast.Constant) and isinstance(n.value, (int, float)):
        return n.value
    if isinstance(n, ast.BinOp) and type(n.op) in _OPS:
        if isinstance(n.op, ast.Pow) and abs(_eval(n.right)) > 100:
            raise ValueError("exposant trop grand")
        return _OPS[type(n.op)](_eval(n.left), _eval(n.right))
    if isinstance(n, ast.UnaryOp) and type(n.op) in _OPS:
        return _OPS[type(n.op)](_eval(n.operand))
    raise ValueError("expression non supportée")


def calculer(expression: str) -> str:
    return str(_eval(ast.parse(expression, mode="eval").body))


def heure(fuseau: str = "Europe/Paris") -> str:
    try:
        return datetime.now(ZoneInfo(fuseau)).strftime("%A %d %B %Y, %H:%M")
    except Exception:
        return "Fuseau horaire inconnu."


def meteo(ville: str) -> str:
    g = requests.get("https://geocoding-api.open-meteo.com/v1/search",
                     params={"name": ville, "count": 1, "language": "fr"}, timeout=8).json()
    if not g.get("results"):
        return "Ville introuvable."
    r = g["results"][0]
    w = requests.get("https://api.open-meteo.com/v1/forecast", params={
        "latitude": r["latitude"], "longitude": r["longitude"],
        "current": "temperature_2m,wind_speed_10m,precipitation"}, timeout=8).json()["current"]
    return (f"{r['name']} : {w['temperature_2m']} °C, vent {w['wind_speed_10m']} km/h, "
            f"précipitations {w['precipitation']} mm.")


OUTILS = {"calculer": calculer, "heure": heure, "meteo": meteo}
SCHEMAS = [
    {"type": "function", "function": {
        "name": "calculer", "description": "Calcule une expression arithmétique.",
        "parameters": {"type": "object", "properties": {"expression": {"type": "string"}},
                       "required": ["expression"]}}},
    {"type": "function", "function": {
        "name": "heure", "description": "Donne la date et l'heure actuelles.",
        "parameters": {"type": "object", "properties": {"fuseau": {"type": "string"}}}}},
    {"type": "function", "function": {
        "name": "meteo", "description": "Météo actuelle d'une ville.",
        "parameters": {"type": "object", "properties": {"ville": {"type": "string"}},
                       "required": ["ville"]}}},
]

# ---------- Client ----------
st.set_page_config(page_title="Jarvis", page_icon="🤖")
st.title("Jarvis — version web")
st.caption("Texte + voix, outils en lecture seule. La version complète (domotique, PC, actions) tourne en local.")

if st.secrets.get("GROQ_API_KEY"):
    client = OpenAI(api_key=st.secrets["GROQ_API_KEY"], base_url="https://api.groq.com/openai/v1")
    MODELE = st.secrets.get("MODELE", "llama-3.3-70b-versatile")
    STT = "whisper-large-v3-turbo"
elif st.secrets.get("OPENAI_API_KEY"):
    client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
    MODELE = st.secrets.get("MODELE", "gpt-4o-mini")
    STT = "whisper-1"
else:
    st.error("Secret `GROQ_API_KEY` manquant : ajoutez-le dans Settings > Secrets.")
    st.stop()

with st.sidebar:
    parler = st.toggle("Réponse vocale", value=True)
    if st.button("Nouvelle conversation"):
        st.session_state.clear()
        st.rerun()

st.session_state.setdefault("messages", [])
st.session_state.setdefault("audio_vu", None)


def repondre(question: str):
    st.session_state.messages.append({"role": "user", "content": question})
    msgs = [{"role": "system", "content": SYSTEME}, *st.session_state.messages[-20:]]
    for _ in range(4):
        rep = client.chat.completions.create(model=MODELE, messages=msgs, tools=SCHEMAS)
        m = rep.choices[0].message
        if not m.tool_calls:
            return m.content or ""
        msgs.append(m)
        for tc in m.tool_calls:
            try:
                fn = OUTILS[tc.function.name]
                res = fn(**json.loads(tc.function.arguments or "{}"))
            except Exception as e:
                res = f"Erreur outil : {type(e).__name__}"
            msgs.append({"role": "tool", "tool_call_id": tc.id, "content": str(res)})
    return "Je n'ai pas pu terminer cette demande."


def voix(texte: str):
    try:
        from gtts import gTTS
        buf = io.BytesIO()
        gTTS(texte, lang="fr").write_to_fp(buf)
        st.audio(buf.getvalue(), format="audio/mp3", autoplay=True)
    except Exception:
        st.caption("(synthèse vocale indisponible)")


for m in st.session_state.messages:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])

question = st.chat_input("Parle à Jarvis…")
audio = st.audio_input("Ou parle au micro")
if audio is not None and audio.file_id != st.session_state.audio_vu:
    st.session_state.audio_vu = audio.file_id
    try:
        question = client.audio.transcriptions.create(
            model=STT, file=("voix.wav", audio.getvalue()), language="fr").text.strip() or question
    except Exception as e:
        st.error(f"Transcription impossible : {type(e).__name__}")

if question:
    with st.chat_message("user"):
        st.markdown(question)
    with st.chat_message("assistant"):
        try:
            texte = repondre(question)
        except Exception as e:
            texte = f"Erreur du fournisseur : {type(e).__name__}"
        st.markdown(texte)
        if parler and not texte.startswith("Erreur"):
            voix(texte)
    st.session_state.messages.append({"role": "assistant", "content": texte})
