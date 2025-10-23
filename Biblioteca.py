import streamlit as st
from pymongo import MongoClient
from pydrive2.auth import GoogleAuth
from pydrive2.drive import GoogleDrive
from datetime import datetime, UTC
import tempfile
import json
# import os
import re


# --------------------------------------------------------------
# Configurações do MongoDB
# --------------------------------------------------------------

client = MongoClient(st.secrets.mongo.string_conexao_mongo)
db = client[st.secrets.mongo.bd_dialogos]

# Carragando cada coleção
publicacoes = db["publicacoes"]
imagens = db["imagens"]
videos = db["videos"]
podcasts = db["podcasts"]
sites = db["sites"]
mapas = db["mapas"]
legislacao = db["legislacao"]
pontos = db["pontos_de_interesse"]
relatorios = db["relatorios"]
pessoas = db["pessoas"]
organizacoes = db["organizacoes"]

# -------------------------------

# ID da pasta no Google Drive onde os arquivos serão salvos
FOLDER_ID = st.secrets["drive_folder"]["id"]

# -------------------------------
# Função para autenticar Google Drive usando st.secrets
def authenticate_drive():
    service_account_info = dict(st.secrets["drive_api"])

    # Garante que a chave client_user_email existe
    client_user_email = service_account_info.get("client_user_email")
    if not client_user_email:
        raise ValueError("client_user_email está ausente em st.secrets['drive_api'].")

    # Cria arquivo temporário
    with tempfile.NamedTemporaryFile(mode="w+", delete=False, suffix=".json") as tmp:
        json.dump(service_account_info, tmp)

        tmp.flush()

        gauth = GoogleAuth()
        gauth.settings['client_config_backend'] = 'service'
        gauth.settings['service_config'] = {
            'client_json_file_path': tmp.name,
            'client_user_email': client_user_email  # <--- ESSENCIAL
        }

        gauth.ServiceAuth()
        drive = GoogleDrive(gauth)
        return drive



# -------------------------------




# --------------------------------------------------------------
# INTERFACE
# --------------------------------------------------------------

st.set_page_config(page_title="Biblioteca Diálogos do Babaçu", layout="wide")


st.logo("images/logo dialogos do babacu.png", size="large")
st.header("Biblioteca Diálogos do Babaçu")
st.write('')






# --------------------------------------------------------------
# Listagem dos arquivos


# FILTROS




# # ------------------ Função utilitária para imagem do Google Drive ------------------ #
# def link_drive_para_embed(link):
#     match = re.search(r"/d/([a-zA-Z0-9_-]+)", link)
#     if match:
#         file_id = match.group(1)
#         return f"https://drive.google.com/uc?export=view&id={file_id}"
#     return link

# ------------------ Dicionários de tipo e ícones ------------------ #
TIPOS_MIDIA = {
    "Publicação": ":material/menu_book: Publicação",
    "Imagem": ":material/add_a_photo: Imagem",
    "Relatório": ":material/assignment: Relatório",
    "Vídeo": ":material/videocam: Vídeo",
    "Podcast": ":material/podcasts: Podcast",
    "Site": ":material/language: Site",
    "Mapa": ":material/map: Mapa",
    "Legislação": ":material/balance: Legislação",
    "Ponto de interesse": ":material/location_on: Ponto de interesse",
    "Organização": ":material/things_to_do: Organização"
}

TIPOS_MIDIA_ICONE = {
    "Publicação": "menu_book",
    "Imagem": "add_a_photo",
    "Relatório": "assignment",
    "Vídeo": "videocam",
    "Podcast": "podcasts",
    "Site": "language",
    "Mapa": "map",
    "Legislação": "balance",
    "Ponto de interesse": "location_on",
    "Organização": "things_to_do"
}


# ------------------ 1. FORMULÁRIO DE FILTROS ------------------ #
with st.expander("Filtros"):
    with st.form("form_filtros", border=False):

        # Lista com ícones para exibir nas pills
        rotulos_com_icone = list(TIPOS_MIDIA.values())

        pills_selecionadas = st.pills(
            label="Tipo de Mídia",
            options=rotulos_com_icone,
            selection_mode="multi"
        )

        # Converter de volta para o valor real (sem ícone)
        tipo_midia_selecionada = [
            tipo for tipo, rotulo in TIPOS_MIDIA.items() if rotulo in pills_selecionadas
        ]

        # Buscar temas distintos em cada coleção
        temas_publicacoes = publicacoes.distinct("tema")
        temas_imagens = imagens.distinct("tema")
        temas_videos = videos.distinct("tema")
        temas_podcasts = podcasts.distinct("tema")
        temas_sites = sites.distinct("tema")
        temas_mapas = mapas.distinct("tema")
        temas_legislacao = legislacao.distinct("tema")
        temas_pontos = pontos.distinct("tema")
        temas_relatorios = relatorios.distinct("tema")
        temas_organizacoes = organizacoes.distinct("tema")

        todos_os_temas = set(
            temas_publicacoes + temas_imagens + temas_videos + temas_podcasts +
            temas_sites + temas_mapas + temas_legislacao + temas_pontos + temas_relatorios + temas_organizacoes
        )
        temas_disponiveis = sorted(todos_os_temas)

        temas_selecionados = st.pills(
            label="Tema",
            options=temas_disponiveis,
            selection_mode="multi"
        )

        col1, col2, col3 = st.columns(3)
        busca_texto = col1.text_input("Buscar palavra chave")

        filtrar = st.form_submit_button("Filtrar", icon=":material/filter_list:", type="primary")




# ------------------ 2. CONSULTA INICIAL (sem filtros = mostra tudo) ------------------ #
def buscar_arquivos(query={}):
    docs_publicacoes = list(publicacoes.find(query))
    docs_imagens = list(imagens.find(query))
    docs_videos = list(videos.find(query))
    docs_podcasts = list(podcasts.find(query))
    docs_sites = list(sites.find(query))
    docs_mapas = list(mapas.find(query))
    docs_legislacao = list(legislacao.find(query))
    docs_pontos = list(pontos.find(query))
    docs_relatorios = list(relatorios.find(query))
    docs_organizacoes = list(organizacoes.find(query))

    for doc in docs_publicacoes: doc["_colecao"] = "publicacoes"
    for doc in docs_imagens: doc["_colecao"] = "imagens"
    for doc in docs_videos: doc["_colecao"] = "videos"
    for doc in docs_podcasts: doc["_colecao"] = "podcasts"
    for doc in docs_sites: doc["_colecao"] = "sites"
    for doc in docs_mapas: doc["_colecao"] = "mapas"
    for doc in docs_legislacao: doc["_colecao"] = "legislacao"
    for doc in docs_pontos: doc["_colecao"] = "pontos_de_interesse"
    for doc in docs_relatorios: doc["_colecao"] = "relatorios"
    for doc in docs_organizacoes: doc["_colecao"] = "organizacoes"

    arquivos_resultado = (
        docs_publicacoes + docs_imagens + docs_videos + docs_podcasts +
        docs_sites + docs_mapas + docs_legislacao + docs_pontos + docs_relatorios + docs_organizacoes
    )

# ??????????????????????????
    # st.write('docs_relatorios', docs_relatorios)
    # st.write('docs_organizacoes', docs_organizacoes)

    return arquivos_resultado




# Consulta inicial (sem filtros)
arquivos = buscar_arquivos()

# ------------------ 3. SE CLICAR EM FILTRAR → APLICA FILTROS ------------------ #
if filtrar:
    query = {}

    if tipo_midia_selecionada:
        query["tipo"] = {"$in": tipo_midia_selecionada}

    if temas_selecionados:
        query["tema"] = {"$in": temas_selecionados}

    if busca_texto.strip():
        texto = busca_texto.strip()
        query["$or"] = [
            {"titulo": {"$regex": texto, "$options": "i"}},
            {"descricao": {"$regex": texto, "$options": "i"}},
            {"tema": {"$regex": texto, "$options": "i"}},
            {"autor": {"$regex": texto, "$options": "i"}},
            {"organizacao": {"$regex": texto, "$options": "i"}}
        ]

    arquivos = buscar_arquivos(query)


# ------------------ 4. TRATAR RESULTADOS ------------------ #




if arquivos:
    # Ordenação e limpeza de campos
    arquivos.sort(key=lambda x: x.get("data_upload", None), reverse=True)


    for item in arquivos:  # Para cada dicionário (item) dentro da lista 'arquivos'
        if isinstance(item.get("tema"), list):  # Verifica se o valor da chave "tema" é uma lista
            item["tema"] = ", ".join(item["tema"])  # Concatena os elementos da lista em uma string separada por vírgulas
        if isinstance(item.get("organizacao"), list):  # Verifica se o valor da chave "organizacao" é uma lista
            item["organizacao"] = ", ".join(item["organizacao"])  # Concatena os elementos da lista em uma string separada por vírgulas


    # Contagem de documentos
    st.subheader(f"{len(arquivos)} documento" if len(arquivos) == 1 else f"{len(arquivos)} documentos")
    st.write("")

    # Container horizontal para os cards
    with st.container(border=False, horizontal=True, width='stretch'):
        for arq in arquivos:


            with st.container(border=True, width=280, height=500, key=arq.get("_id", None)):

                tipo = arq.get("tipo", "Tipo não informado")
                icon = TIPOS_MIDIA_ICONE.get(tipo, "things_to_do")
                titulo = arq.get("titulo", "Sem título")
                descricao = arq.get("descricao", "Sem descrição")
                autor = arq.get("autor", "Autor desconhecido")
                tema = arq.get("tema", "")
                organizacao = arq.get("organizacao", "")
                link = arq.get("link", "#")
                thumb_link = arq.get("thumb_link", None)

                st.write(f":material/{icon}: {tipo}")

                # Mostrar miniatura -------------------------

                # Renderiza icone balance
                if tipo == "Legislação":
                    st.markdown("""
                        <link href="https://fonts.googleapis.com/icon?family=Material+Icons" rel="stylesheet">
                        <div style="text-align:center; margin: 40px 0;">
                            <span class="material-icons" style="font-size: 100px; color: #777;">
                                balance
                            </span>
                        </div>
                        """, unsafe_allow_html=True)


                # Renderiza logotipo
                if tipo == "Organização":
                    logotipo_link = arq.get("logotipo", None)

                    if logotipo_link and "drive.google.com" in logotipo_link:
                                file_id = None
                                if "/d/" in logotipo_link:
                                    file_id = logotipo_link.split("/d/")[1].split("/")[0]
                                elif "id=" in logotipo_link:
                                    import re
                                    m = re.search(r"id=([a-zA-Z0-9_-]+)", logotipo_link)
                                    if m:
                                        file_id = m.group(1)

                                if file_id:
                                    direct_url = f"https://drive.google.com/thumbnail?sz=w280&id={file_id}"
                                    st.image(direct_url, width=280)
                                else:
                                    st.warning("Não foi possível extrair o ID do logotipo.")


                # Renderiza miniatura
                if thumb_link:
                
                    try:
                        # --- Caso seja Google Drive ---
                        if "drive.google.com" in thumb_link:
                            file_id = None
                            # extrair ID de /d/ID/
                            if "/d/" in thumb_link:
                                file_id = thumb_link.split("/d/")[1].split("/")[0]
                            # extrair ID de ?id=ID
                            elif "id=" in thumb_link:
                                import re
                                m = re.search(r"id=([a-zA-Z0-9_-]+)", thumb_link)
                                if m:
                                    file_id = m.group(1)

                            if file_id:
                                direct_url = f"https://drive.google.com/thumbnail?sz=w280&id={file_id}"
                                st.image(direct_url, width=280)
                            else:
                                st.warning("ID do arquivo Drive não pôde ser extraído")

                        # --- Caso seja YouTube ---
                        elif "img.youtube.com" in thumb_link:
                            st.image(thumb_link, width=280)

                        # --- Outros links (opcional) ---
                        else:
                            st.image(thumb_link, width=280)

                    except Exception as e:
                        st.warning(f"Erro ao exibir miniatura: {e}")


                # ---------------------------------------------


                # texto
                st.markdown(f"<h5 style='margin-bottom: 0.5rem'>{titulo}</h5>", unsafe_allow_html=True)
                st.write(descricao)
                st.write(f"**Autor:** {autor}")
                st.write(f"**Organização:** {organizacao}")
                st.write(f"**Descrição:** {descricao}")
                st.write(f"**Tema:** {tema}")
                
                if tipo == "Organização":
                    
                    # Websites
                    st.write(f"**Websites:** {arq.get('websites', 'N/A')}")

                    # Link para a pasta com vários arquivos
                    subfolder_id = arq.get("subfolder_id", "")
                    link = f"https://drive.google.com/drive/folders/{subfolder_id}"
                    st.link_button("Ver detalhes", url=link, type="primary")

                else:
                    st.link_button("Ver detalhes", url=link, type="primary")





else:
    st.info("Nenhum arquivo encontrado para os filtros aplicados.")







