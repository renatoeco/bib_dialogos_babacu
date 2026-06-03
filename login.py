import streamlit as st

if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False

if "permissao" not in st.session_state:
    st.session_state["permissao"] = ""

if not st.session_state["logged_in"]:

    pg = st.navigation([
        st.Page("Biblioteca.py", title="Biblioteca", icon=":material/menu_book:"),
        st.Page("Mapa.py", title="Mapa", icon=":material/map:")
    ])

else:

    if st.session_state["permissao"] == "Visitante":

        pg = st.navigation([
            st.Page("Biblioteca.py", title="Biblioteca", icon=":material/menu_book:"),
            st.Page("Mapa.py", title="Mapa", icon=":material/map:")
        ])

    else:

        pg = st.navigation([
            st.Page("Biblioteca.py", title="Biblioteca", icon=":material/menu_book:"),
            st.Page("Mapa.py", title="Mapa", icon=":material/map:"),
            st.Page("Gerenciamento.py", title="Gerenciamento", icon=":material/settings:")
        ])

pg.run()