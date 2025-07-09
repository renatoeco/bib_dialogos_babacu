import streamlit as st
from pymongo import MongoClient

@st.cache_resource
def conectar_mongo_dialogos_babacu():
    cliente = MongoClient(
    st.secrets["mongo"]["string_conexao_mongo"])
    db_biblioteca = cliente[st.secrets["mongo"]["bd_dialogos"]]                   
    return db_biblioteca


# @st.cache_resource
# def conectar_mongo_pls():
#     cliente_2 = MongoClient(
#     st.secrets["senhas"]["senha_mongo_pls"])
#     db_pls = cliente_2["db_pls"]
#     return db_pls