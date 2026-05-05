import streamlit as st
from pymongo import MongoClient

@st.cache_resource
def conectar_mongo_dialogos_babacu():
    cliente = MongoClient(
    st.secrets["mongo"]["string_conexao_mongo"])
    db_biblioteca = cliente[st.secrets["mongo"]["bd_dialogos"]]                   
    return db_biblioteca





# Barra de logos
def barra_de_logos():
    
    col1, col2 = st.columns([1, 3])