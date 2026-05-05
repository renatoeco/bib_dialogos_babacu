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

    st.write('')
    st.write('')
    st.write('')
    st.write('')
    st.write('')

    col1, espaco, col2 = st.columns([2, 1, 6])

    with col1:
        st.write('**Instituição facilitadora**')
        st.write('')
        st.image("images/logo_ISPN_horizontal.png", width=250)

    with col2:
        st.write('**Realização**')
        st.image("images/logos_bateria.png", width=600)