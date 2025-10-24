
import streamlit as st
from pymongo import MongoClient
import pandas as pd


from pydrive2.auth import GoogleAuth
from pydrive2.drive import GoogleDrive
from datetime import datetime, UTC
import tempfile
import json
import os



# --------------------------------------------------------------
# Configurações do MongoDB
# --------------------------------------------------------------

client = MongoClient(st.secrets.mongo.string_conexao_mongo)
db = client[st.secrets.mongo.bd_dialogos]

# Carregando cada coleção

pontos = db["pontos_interesse"]

df_pontos = pd.DataFrame(list(pontos.find()))


# --------------------------------------------------------------
# CONFIGURAÇÃO DA INTERFACE
# --------------------------------------------------------------

st.set_page_config(page_title="Mapa dos Pontos de Interesse", layout="wide")
st.logo("images/logo dialogos do babacu.png", size="large")



# --------------------------------------------------------------
# TRANSFORMAÇÃO DOS DADOS
# --------------------------------------------------------------

# Converter as colunas latitude e longitude para str
df_pontos['latitude'] = df_pontos['latitude'].astype(float)
df_pontos['longitude'] = df_pontos['longitude'].astype(float)




# --------------------------------------------------------------
# INTERFACE
# --------------------------------------------------------------



st.header("Mapa dos Pontos de Interesse")
st.write('')
st.map(df_pontos, latitude="latitude", longitude="longitude", size=200)
