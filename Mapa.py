import streamlit as st
from pymongo import MongoClient
import pandas as pd
from funcoes_auxiliares import conectar_mongo_dialogos_babacu, barra_de_logos
import folium
from streamlit_folium import st_folium
from folium import IFrame


# --------------------------------------------------------------
# Configurações do MongoDB
# --------------------------------------------------------------

db = conectar_mongo_dialogos_babacu()


# Carregando cada coleção

pontos = db["pontos_interesse"]
df_pontos = pd.DataFrame(list(pontos.find()))


# --------------------------------------------------------------
# CONFIGURAÇÃO DA INTERFACE
# --------------------------------------------------------------

st.set_page_config(page_title="Mapa dos Pontos de Interesse", layout="wide")
st.header("Mapa dos Pontos de Interesse")
st.write("")


# --------------------------------------------------------------
# TRATAMENTO DOS DADOS
# --------------------------------------------------------------

if "_id" in df_pontos.columns:
    df_pontos = df_pontos.drop(columns=["_id"])

df_pontos["latitude"] = df_pontos["latitude"].astype(float)
df_pontos["longitude"] = df_pontos["longitude"].astype(float)
df_pontos = df_pontos.fillna("")


# --------------------------------------------------------------
# CRIANDO O MAPA
# --------------------------------------------------------------

# Centro do mapa
centro = [
    df_pontos["latitude"].mean(),
    df_pontos["longitude"].mean()
]

m = folium.Map(
    location=centro,
    zoom_start=4,
    tiles="OpenStreetMap"  # estilo simples
)


# --------------------------------------------------------------
# ADICIONANDO MARCADORES
# --------------------------------------------------------------

for _, row in df_pontos.iterrows():

    html = f"""
    <b>{row.get('titulo','')}</b><br><br>

    {row.get('descricao','')}<br><br>

    <a href="{row.get('link','')}" target="_blank">
        Ver localização
    </a>
    """

    iframe = IFrame(html=html, width=250, height=150)

    popup = folium.Popup(iframe, max_width=300)

    folium.Marker(
        location=[row["latitude"], row["longitude"]],
        popup=popup,
        tooltip=row.get("titulo", ""),
        icon=folium.Icon(color="blue", icon="info-sign")
    ).add_to(m)


# --------------------------------------------------------------
# EXIBIÇÃO NO STREAMLIT
# --------------------------------------------------------------

st_folium(m, use_container_width=True, height=600)