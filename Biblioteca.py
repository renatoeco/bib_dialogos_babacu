import streamlit as st
from pymongo import MongoClient
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

# # Mapeia tipos exibidos para as chaves das pastas no secrets
# TIPO_PASTA_MAP = {
#     "Publicação": "publicacoes",
#     "Imagem": "imagens",
#     "Mapa": "mapas",
#     "Relatorio": "relatorios"
# }

# def upload_to_drive(file, filename, tipo):
#     # Verifica se o tipo está entre os que devem ser enviados ao Drive
#     if tipo not in TIPO_PASTA_MAP:
#         return None  # Não faz upload ao Drive para outros tipos

#     tipo_key = TIPO_PASTA_MAP[tipo]
#     folder_id = st.secrets["pastas"].get(tipo_key)

#     if not folder_id:
#         st.error(f"Tipo de mídia permitido, mas pasta não configurada no secrets: {tipo_key}")
#         return None

#     drive = authenticate_drive()

#     # Salva o arquivo temporariamente
#     with open(filename, "wb") as f:
#         f.write(file.getbuffer())

#     # Cria e envia o arquivo ao Google Drive
#     gfile = drive.CreateFile({
#         'title': filename,
#         'parents': [{'id': folder_id}]
#     })
#     gfile.SetContentFile(filename)
#     gfile.Upload()

#     # Remove o arquivo local
#     os.remove(filename)

#     return gfile['id']




# --------------------------------------------------------------
# INTERFACE
# --------------------------------------------------------------

st.set_page_config(page_title="Biblioteca Diálogos do Babaçu", layout="wide")


st.logo("aux/logo dialogos do babacu.png", size="large")
st.header("Biblioteca Diálogos do Babaçu")
st.write('')








# --------------------------------------------------------------
# Listagem dos arquivos

# st.markdown("---")
# st.write('**Filtros**')

# FILTROS

with st.expander("Filtros"):
    
    # Tipos de mídia como pills
    tipos_de_midia = ["Publicação", "Imagem", "Relatório", "Vídeo", "Podcast", "Site", "Mapa", "Legislação", "Ponto de interesse"]
    tipo_midia_selecionada = st.pills(label="Tipo de Mídia", 
                                      options=tipos_de_midia,
                                      selection_mode="multi"
                                      )
    
    

    # Temas como pills
    # Pega os temas distintos de cada coleção
    temas_publicacoes = publicacoes.distinct("tema")
    temas_imagens = imagens.distinct("tema")
    temas_videos = videos.distinct("tema")
    temas_podcasts = podcasts.distinct("tema")
    temas_sites = sites.distinct("tema")
    temas_mapas = mapas.distinct("tema")
    temas_legislacao = legislacao.distinct("tema")
    temas_pontos = pontos.distinct("tema")
    temas_relatorios = relatorios.distinct("tema")

    # Une todos os temas e remove duplicatas com set
    todos_os_temas = set(
        temas_publicacoes + temas_imagens + temas_videos + temas_podcasts +
        temas_sites + temas_mapas + temas_legislacao + temas_pontos + temas_relatorios
    )

    # Ordena a lista
    temas_disponiveis = sorted(todos_os_temas)

    temas_selecionados = st.pills(
        label="Tema",
        options=temas_disponiveis,
        # default=temas_disponiveis,  # todos selecionados por padrão
        selection_mode="multi"
    )


    # Campo de busca textual
    col1, col2, col3 = st.columns(3)
    busca_texto = col1.text_input(
        "Buscar palavra chave"
    )



# st.write('---')

# Montagem da query Mongo
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



# Consulta no MongoDB

# Busca em todas as coleções
docs_publicacoes = list(publicacoes.find(query))
docs_imagens = list(imagens.find(query))
docs_videos = list(videos.find(query))
docs_podcasts = list(podcasts.find(query))
docs_sites = list(sites.find(query))
docs_mapas = list(mapas.find(query))
docs_legislacao = list(legislacao.find(query))
docs_pontos = list(pontos.find(query))
docs_relatorios = list(relatorios.find(query))

# Adiciona campo de coleção em cada documento
for doc in docs_publicacoes:
    doc["_colecao"] = "publicacoes"
for doc in docs_imagens:
    doc["_colecao"] = "imagens"
for doc in docs_videos:
    doc["_colecao"] = "videos"
for doc in docs_podcasts:
    doc["_colecao"] = "podcasts"
for doc in docs_sites:
    doc["_colecao"] = "sites"
for doc in docs_mapas:
    doc["_colecao"] = "mapas"
for doc in docs_legislacao:
    doc["_colecao"] = "legislacao"
for doc in docs_pontos:
    doc["_colecao"] = "pontos_de_interesse"
for doc in docs_relatorios:
    doc["_colecao"] = "relatorios"

# Junta tudo
arquivos = (
    docs_publicacoes + docs_imagens + docs_videos + docs_podcasts +
    docs_sites + docs_mapas + docs_legislacao + docs_pontos + docs_relatorios
)

# Ordena por data_upload descendente
arquivos.sort(key=lambda x: x.get("data_upload", None), reverse=True)

# Transformando tema e organização de lista para string separada por vírgula
for item in arquivos:
    if isinstance(item.get("tema"), list):
        item["tema"] = ", ".join(item["tema"])
    if isinstance(item.get("organizacao"), list):
        item["organizacao"] = ", ".join(item["organizacao"])



# arquivos = list(publicacoes.find(query).sort("data_upload", -1))

# Exibição dos arquivos
if arquivos:

    if len(arquivos) == 1:
        st.subheader(f"{len(arquivos)} documento")
    else:
        st.subheader(f"{len(arquivos)} documentos")

    st.write('')
    cols_per_row = 4
    for i in range(0, len(arquivos), cols_per_row):
        cols = st.columns(cols_per_row)
        for idx, arq in enumerate(arquivos[i:i+cols_per_row]):
            with cols[idx]:
                # Container para o card com borda e sombra leve via CSS inline
                st.markdown(
                    f"""
                    <div style="
                        border: 1px solid #ddd; 
                        border-radius: 8px; 
                        padding: 16px; 
                        box-shadow: 2px 2px 8px rgba(0,0,0,0.1);
                        margin-bottom: 16px;
                        background-color: #fff;
                        height: 100%;
                        display: flex;
                        flex-direction: column;
                        justify-content: space-between;
                    ">
                        <p>{arq.get('tipo')}</p>
                        <h5 style="margin-bottom: 8px;">{arq.get('titulo', 'Sem Título')}</h5>
                        <p style="flex-grow: 1; margin-bottom: 8px;"><em>{arq.get('descricao', 'Sem descrição')}</em></p>
                        <p><strong>Autor:</strong> {arq.get('autor')}</p>
                        <p><strong>Organização:</strong> {arq.get('organizacao')}</p>
                        <p><strong>Tema:</strong> {arq.get('tema')}</p>
                        <a href="{arq.get('link')}" target="_blank" style="text-decoration:none;">
                            <button style="
                                background-color: #7f3e21;
                                color: white;
                                padding: 8px 12px;
                                border: none;
                                border-radius: 5px;
                                cursor: pointer;
                            ">Acessar</button>
                        </a>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
else:
    st.info("Nenhum arquivo encontrado para os filtros aplicados.")


