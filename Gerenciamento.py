# ------------------ Bibliotecas padrão (Python) ------------------ #
import os
import re
import time
import json
import tempfile
from datetime import datetime, UTC
from zoneinfo import ZoneInfo
from io import BytesIO
import pandas as pd
from bson import ObjectId


import pypdfium2 as pdfium


# ------------------ Bibliotecas de terceiros ------------------ #
import streamlit as st
from pymongo import MongoClient
from PIL import Image
from pdf2image import convert_from_path
from email.mime.text import MIMEText  
import smtplib  

# Google Drive API
from pydrive2.auth import GoogleAuth
from pydrive2.drive import GoogleDrive




# --------------------------------------------------------------
# Configurações do MongoDB
# --------------------------------------------------------------

client = MongoClient(st.secrets.mongo.string_conexao_mongo)
db = client[st.secrets.mongo.bd_dialogos]

# Carregando cada coleção
publicacoes = db["publicacoes"]
imagens = db["imagens"]
videos = db["videos"]
podcasts = db["podcasts"]
sites = db["sites"]
mapas = db["mapas"]
legislacao = db["legislacao"]
pontos_interesse= db["pontos_interesse"]
relatorios = db["relatorios"]
pessoas = db["pessoas"]
organizacoes = db["organizacoes"]
projetos = db["projetos"]
pesquisas = db["pesquisas"]










# --------------------------------------------------------------
# Funções auxiliares
# --------------------------------------------------------------
def buscar_arquivos(query={}):
    docs_publicacoes = list(publicacoes.find(query))
    docs_imagens = list(imagens.find(query))
    docs_videos = list(videos.find(query))
    docs_podcasts = list(podcasts.find(query))
    docs_sites = list(sites.find(query))
    docs_mapas = list(mapas.find(query))
    docs_legislacao = list(legislacao.find(query))
    docs_pontos = list(pontos_interesse.find(query))
    docs_relatorios = list(relatorios.find(query))
    docs_organizacoes = list(organizacoes.find(query))
    docs_projetos = list(projetos.find(query))
    docs_pesquisas = list(pesquisas.find(query))

    for doc in docs_publicacoes: doc["_colecao"] = "publicacoes"
    for doc in docs_imagens: doc["_colecao"] = "imagens"
    for doc in docs_videos: doc["_colecao"] = "videos"
    for doc in docs_podcasts: doc["_colecao"] = "podcasts"
    for doc in docs_sites: doc["_colecao"] = "sites"
    for doc in docs_mapas: doc["_colecao"] = "mapas"
    for doc in docs_legislacao: doc["_colecao"] = "legislacao"
    for doc in docs_pontos: doc["_colecao"] = "pontos_interesse"
    for doc in docs_relatorios: doc["_colecao"] = "relatorios"
    for doc in docs_organizacoes: doc["_colecao"] = "organizacoes"
    for doc in docs_projetos: doc["_colecao"] = "projetos"
    for doc in docs_pesquisas: doc["_colecao"] = "pesquisas"

    arquivos_resultado = (
        docs_publicacoes + docs_imagens + docs_videos + docs_podcasts +
        docs_sites + docs_mapas + docs_legislacao + docs_pontos + docs_relatorios + 
        docs_organizacoes + docs_projetos + docs_pesquisas
    )

    return arquivos_resultado

# Todos os arquivos
arquivos = buscar_arquivos()

# Mapeia tipos exibidos para as chaves das pastas no secrets
TIPO_PASTA_MAP = {
    "Publicação": "publicacoes",
    "Imagem": "imagens",
    "Mapa": "mapas",
    "Relatório": "relatorios",
    "Podcast": "podcasts",
    "Site": "sites",
    "Ponto de interesse": "pontos_interesse",
    "Organização": "organizacoes",
    "Projeto": "projetos",
    "Pesquisa": "pesquisas",
    "Legislação": "legislacao",
    "Vídeo": "videos"
}



@st.dialog("Cadastrar Organização")
def cadastrar_organizacao():
    with st.form("Cadastro de Organização"):
        # Campos básicos
        nome_organizacao = st.text_input("Nome da Organização")
        sigla = st.text_input("Sigla da Organização")
        
        # Campos complementares
        descricao = st.text_area("Descrição")
        tema = st.multiselect("Tema", temas_ordenados)
        CNPJ = st.text_input("CNPJ")
        websites = st.text_input("Websites (separados por vírgula)")
        logotipo = st.file_uploader("Logotipo", type=["png", "jpg", "jpeg"])
        documentos = st.file_uploader(
            "Documentos da organização (Estatuto, CNPJ, etc)", 
            accept_multiple_files=True, 
            type=["pdf"]
        )

        # Botão de envio
        cadastrar = st.form_submit_button(":material/add: Cadastrar")

        if cadastrar:
            # Validação mínima
            if not nome_organizacao.strip() or not sigla.strip():
                st.error("Todos os campos obrigatórios devem ser preenchidos.")
                return

            with st.spinner("Enviando..."):
                try:
                    # Autenticação do Google Drive
                    drive = authenticate_drive()
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

                    # Criar subpasta da organização
                    parent_folder_id = st.secrets["pastas"].get("organizacoes")  # Ajuste conforme sua pasta
                    subfolder_name = f"{timestamp}_{nome_organizacao.replace(' ', '_')}"
                    subfolder = drive.CreateFile({
                        "title": subfolder_name,
                        "mimeType": "application/vnd.google-apps.folder",
                        "parents": [{"id": parent_folder_id}]
                    })
                    subfolder.Upload()
                    subfolder_id = subfolder["id"]

                    # Upload do logotipo
                    logotipo_link = None
                    if logotipo:
                        logotipo_path = os.path.join(tempfile.gettempdir(), logotipo.name)
                        with open(logotipo_path, "wb") as f:
                            f.write(logotipo.getbuffer())
                        gfile_logo = drive.CreateFile({
                            "title": logotipo.name,
                            "parents": [{"id": subfolder_id}]
                        })
                        gfile_logo.SetContentFile(logotipo_path)
                        gfile_logo.Upload()
                        logotipo_link = f"https://drive.google.com/file/d/{gfile_logo['id']}/view"
                        os.remove(logotipo_path)

                    # Upload dos documentos
                    documentos_links = []
                    for doc in documentos or []:
                        doc_path = os.path.join(tempfile.gettempdir(), doc.name)
                        with open(doc_path, "wb") as f:
                            f.write(doc.getbuffer())
                        gfile_doc = drive.CreateFile({
                            "title": doc.name,
                            "parents": [{"id": subfolder_id}]
                        })
                        gfile_doc.SetContentFile(doc_path)
                        gfile_doc.Upload()
                        documentos_links.append(f"https://drive.google.com/file/d/{gfile_doc['id']}/view")
                        os.remove(doc_path)

                    # Salvar no MongoDB
                    data = {
                        "titulo": nome_organizacao.strip(),
                        "sigla": sigla.strip(),
                        "descricao": descricao,
                        "tema": tema,
                        "cnpj": CNPJ,
                        "websites": websites,
                        "logotipo": logotipo_link,
                        "documentos": documentos_links,
                        "subfolder_id": subfolder_id,
                        "tipo": "Organização",
                        "enviado_por": st.session_state.get("nome", "desconhecido"),
                        "data_upload": datetime.now()
                    }

                    organizacoes.insert_one(data)
                    st.success("Organização cadastrada com sucesso!")
                    time.sleep(2)
                    st.rerun()

                except Exception as e:
                    st.error(f"Erro ao cadastrar organização: {e}")


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


# Envia só a thumbnail / miniatura para o drive
def upload_thumbnail_to_drive(local_path, nome_base, tipo):
    """
    Recebe um UploadedFile (Streamlit), cria thumbnail de 280px de largura 
    com altura proporcional, salva temporariamente e envia ao Google Drive.
    Retorna o link da miniatura enviada.
    """
    try:
        drive = authenticate_drive()

        # 1. Salva o arquivo enviado (UploadedFile) em um arquivo temporário
        ext = os.path.splitext(local_path.name)[1].lower()
        temp_input_path = os.path.join(tempfile.gettempdir(), f"orig_{nome_base}{ext}")

        with open(temp_input_path, "wb") as f:
            f.write(local_path.getbuffer())

        # 2. Pega a pasta correta no Drive
        tipo_key = TIPO_PASTA_MAP.get(tipo)
        parent_folder_id = st.secrets["pastas"].get(tipo_key)

        if not parent_folder_id:
            st.error(f"Pasta do tipo {tipo} não configurada no secrets.")
            return None

        # 3. Cria subpasta com timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        folder_name = f"{timestamp}_{nome_base}"

        subfolder = drive.CreateFile({
            'title': folder_name,
            'mimeType': 'application/vnd.google-apps.folder',
            'parents': [{'id': parent_folder_id}]
        })
        subfolder.Upload()
        subfolder_id = subfolder['id']

        # 4. Geração da miniatura (thumb)
        thumb_name = f"miniatura_{nome_base}.png"
        thumb_path = os.path.join(tempfile.gettempdir(), thumb_name)

        # Se for imagem
        if ext in ['.png', '.jpg', '.jpeg', '.webp']:
            img = Image.open(temp_input_path)
            w, h = img.size
            new_height = int((280 / w) * h)
            img = img.resize((280, new_height), Image.Resampling.LANCZOS)
            img.save(thumb_path, "PNG")

        # Se for PDF
        elif ext == '.pdf':
            pages = convert_from_path(temp_input_path, dpi=150, first_page=1, last_page=1)
            if pages:
                img = pages[0]
                w, h = img.size
                new_height = int((280 / w) * h)
                img = img.resize((280, new_height), Image.Resampling.LANCZOS)
                img.save(thumb_path, "PNG")
        else:
            st.error("Formato não suportado para miniatura.")
            return None

        # 5. Upload da thumbnail para o Drive
        thumb_file = drive.CreateFile({
            'title': thumb_name,
            'parents': [{'id': subfolder_id}]
        })
        thumb_file.SetContentFile(thumb_path)
        thumb_file.Upload()

        thumb_link = f"https://drive.google.com/file/d/{thumb_file['id']}/view"

        # 6. Limpeza de arquivos temporários
        if os.path.exists(thumb_path):
            os.remove(thumb_path)
        if os.path.exists(temp_input_path):
            os.remove(temp_input_path)

        return thumb_link

    except Exception as e:
        st.error(f"Erro ao enviar miniatura: {e}")
        return None



def upload_to_drive(file, filename, tipo):
    if tipo not in TIPO_PASTA_MAP:
        return None, None

    tipo_key = TIPO_PASTA_MAP[tipo]
    parent_folder_id = st.secrets["pastas"].get(tipo_key)

    if not parent_folder_id:
        st.error(f"Pasta não configurada no secrets: {tipo_key}")
        return None, None

    drive = authenticate_drive()

    base_name, ext = os.path.splitext(filename)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    folder_name = f"{timestamp}_{base_name}"

    # ------------------------
    # Cria subpasta no Drive
    # ------------------------
    subfolder = drive.CreateFile({
        'title': folder_name,
        'mimeType': 'application/vnd.google-apps.folder',
        'parents': [{'id': parent_folder_id}]
    })
    subfolder.Upload()
    subfolder_id = subfolder['id']

    # ------------------------
    # Salva arquivo local temporário
    # ------------------------
    temp_path = os.path.join(tempfile.gettempdir(), filename)
    with open(temp_path, "wb") as f:
        f.write(file.getbuffer())

    # ------------------------
    # Upload do arquivo original
    # ------------------------
    gfile = drive.CreateFile({
        'title': filename,
        'parents': [{'id': subfolder_id}]
    })
    gfile.SetContentFile(temp_path)
    gfile.Upload()
    file_link = f"https://drive.google.com/file/d/{gfile['id']}/view"

    # ------------------------
    # Geração da miniatura
    # ------------------------
    thumb_link = None

    try:
        thumb_name = f"miniatura_{base_name}.png"
        thumb_path = os.path.join(tempfile.gettempdir(), thumb_name)

        # 📸 IMAGEM
        if ext.lower() in [".png", ".jpg", ".jpeg", ".webp"]:
            img = Image.open(temp_path)
            img = img.convert("RGB")
            w, h = img.size
            new_height = int((280 / w) * h)
            img = img.resize((280, new_height), Image.Resampling.LANCZOS)
            img.save(thumb_path, "PNG")

        # 📄 PDF (pypdfium2)
        elif ext.lower() == ".pdf":
            pdf = pdfium.PdfDocument(temp_path)
            if len(pdf) == 0:
                raise Exception("PDF sem páginas")

            page = pdf[0]
            bitmap = page.render(scale=1.2, rotation=0)
            img = bitmap.to_pil()
            img = img.convert("RGB")

            w, h = img.size
            new_height = int((280 / w) * h)
            img = img.resize((280, new_height), Image.Resampling.LANCZOS)
            img.save(thumb_path, "PNG")

        # ------------------------
        # Upload da miniatura
        # ------------------------
        if os.path.exists(thumb_path):
            thumb_file = drive.CreateFile({
                'title': thumb_name,
                'parents': [{'id': subfolder_id}]
            })
            thumb_file.SetContentFile(thumb_path)
            thumb_file.Upload()
            thumb_link = f"https://drive.google.com/file/d/{thumb_file['id']}/view"
            os.remove(thumb_path)

    except Exception as e:
        st.warning(f"Miniatura não criada: {e}")

    # ------------------------
    # Cleanup
    # ------------------------
    os.remove(temp_path)

    return file_link, thumb_link













# # Envia o arquivo e a miniatura para o drive
# def upload_to_drive(file, filename, tipo):
#     if tipo not in TIPO_PASTA_MAP:
#         return None, None

#     tipo_key = TIPO_PASTA_MAP[tipo]
#     parent_folder_id = st.secrets["pastas"].get(tipo_key)

#     if not parent_folder_id:
#         st.error(f"Pasta não configurada no secrets: {tipo_key}")
#         return None, None

#     drive = authenticate_drive()

#     base_name, ext = os.path.splitext(filename)
#     timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
#     folder_name = f"{timestamp}_{base_name}"

#     # Cria subpasta no Drive
#     subfolder = drive.CreateFile({
#         'title': folder_name,
#         'mimeType': 'application/vnd.google-apps.folder',
#         'parents': [{'id': parent_folder_id}]
#     })
#     subfolder.Upload()
#     subfolder_id = subfolder['id']

#     # Salva arquivo temporariamente
#     with open(filename, "wb") as f:
#         f.write(file.getbuffer())

#     # Upload do arquivo original
#     gfile = drive.CreateFile({'title': filename, 'parents': [{'id': subfolder_id}]})
#     gfile.SetContentFile(filename)
#     gfile.Upload()
#     file_link = f"https://drive.google.com/file/d/{gfile['id']}/view"

#     # ------------------------
#     # Miniatura (imagem ou PDF)
#     # ------------------------
#     thumb_link = None
#     try:
#         thumb_name = f"miniatura_{base_name}.png"
#         thumb_path = os.path.join(tempfile.gettempdir(), thumb_name)

#         # Se for imagem
#         if ext.lower() in ['.png', '.jpg', '.jpeg', '.webp']:
#             img = Image.open(filename)
#             w, h = img.size
#             new_height = int((280 / w) * h)  # mantém proporção
#             img = img.resize((280, new_height), Image.Resampling.LANCZOS)
#             img.save(thumb_path, "PNG")

#         # Se for PDF → pega primeira página
#         elif ext.lower() == '.pdf':
#             pages = convert_from_path(filename, dpi=150, first_page=1, last_page=1)
#             if pages:
#                 img = pages[0]
#                 w, h = img.size
#                 new_height = int((280 / w) * h)  # mantém proporção
#                 img = img.resize((280, new_height), Image.Resampling.LANCZOS)
#                 img.save(thumb_path, "PNG")

#         # Se gerou thumb, faz upload no Drive
#         if os.path.exists(thumb_path):
#             thumb_file = drive.CreateFile({
#                 'title': thumb_name,
#                 'parents': [{'id': subfolder_id}]
#             })
#             thumb_file.SetContentFile(thumb_path)
#             thumb_file.Upload()
#             thumb_link = f"https://drive.google.com/file/d/{thumb_file['id']}/view"
#             os.remove(thumb_path)

#     except Exception as e:
#         st.warning(f"Miniatura não criada: {e}")

#     # Remove arquivo local original
#     os.remove(filename)

#     return file_link, thumb_link




# --------------------------------------------------------------
# Transformação dos dados
# --------------------------------------------------------------


# Tipos de midia
TIPOS_MIDIA = [
    "Publicação",
    "Imagem",
    "Relatório",
    "Vídeo",
    "Podcast",
    "Site",
    "Mapa",
    "Legislação",
    "Ponto de interesse",
    "Organização",
    "Projeto",
    "Pesquisa"
]
# Temas
TEMAS_BABACU = [
    "Meio Ambiente",
    "Educação",
    "Saúde",
    "Produção e Agricultura",
    "Economia e Comercialização",
    "Cultura e Tradição",
    "Tecnologia e Inovação",
    "Legislação e Políticas Públicas",
    "Sustentabilidade",
    "Comunidades e Povos Tradicionais",
    "Gastronomia"
]




# --------------------------------------------------------------
# Interface
# --------------------------------------------------------------

# Logo
st.logo("images/logo dialogos do babacu.png", size="large")


st.header("Gerenciamento")


tab_acervo, tab_pessoas = st.tabs(["Acervo", "Pessoas"])


# ACERVO
with tab_acervo:

    # Escolha da ação
    st.write('')
    acao = st.radio(
        "O que deseja fazer?",
        ["Cadastrar documento", "Editar um documento", "Excluir um documento"],
        horizontal=True
    )

    # ENVIAR ARQUIVO

    # FUNÇÕES PARA CADA TIPO DE ARQUIVO

    # ----- PREPARAÇÃO DO DROPDOWN DE TEMAS -----

    # Ordena alfabeticamente os temas do babacu (exceto "Outro", que fica no final)
    temas_ordenados = sorted([t for t in TEMAS_BABACU])
    temas_ordenados.append("Outro")

    # Adiciona uma opção vazia no início
    temas_ordenados = [""] + temas_ordenados


    # 0. Cadastro de organização ---------------------------------------------------------------------------
    def enviar_organizacao(): 
        st.write('')
        st.subheader("Cadastrar organização")    

        tipo_doc = "Organização" 

        # Campos do formulário
        nome_organizacao = st.text_input("Nome da organização")
        sigla = st.text_input("Sigla da organização")
        descricao = st.text_area("Descrição")
        tema = st.multiselect("Tema", temas_ordenados)
        CNPJ = st.text_input("CNPJ")
        websites = st.text_input("Websites (separados por vírgula)")
        logotipo = st.file_uploader("Logotipo", type=["png", "jpg", "jpeg"])
        documentos = st.file_uploader(
            "Documentos da organização (Estatuto, CNPJ, etc)", 
            accept_multiple_files=True, 
            type=["pdf"]
        )

        # Botão de envio
        col1, col2 = st.columns([1, 6])
        col1.write('')
        submitted = col1.button(":material/check: Enviar", type="primary", use_container_width=True)

        if submitted:
            if not nome_organizacao:
                st.error("Insira o nome da organização.")
                return

            with st.spinner('Enviando ...'):
                try:
                    drive = authenticate_drive()
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

                    # pegar a correspondência de tipo_doc em TIPO_PASTA_MAP
                    tipo_key = TIPO_PASTA_MAP.get(tipo_doc)
                    


                    parent_folder_id = st.secrets["pastas"].get(tipo_key)
                    if not parent_folder_id:
                        st.error(f"Pasta para tipo '{tipo_doc}' não configurada no secrets.")
                        return

                    # Criar subpasta da organização
                    subfolder_name = f"{timestamp}_{nome_organizacao.replace(' ', '_')}"
                    subfolder = drive.CreateFile({
                        "title": subfolder_name,
                        "mimeType": "application/vnd.google-apps.folder",
                        "parents": [{"id": parent_folder_id}]
                    })
                    subfolder.Upload()
                    subfolder_id = subfolder["id"]

                    # --- Upload do logotipo ---
                    logotipo_link = None
                    if logotipo:
                        logotipo_name = logotipo.name
                        logotipo_path = os.path.join(tempfile.gettempdir(), logotipo_name)
                        with open(logotipo_path, "wb") as f:
                            f.write(logotipo.getbuffer())
                        
                        gfile_logo = drive.CreateFile({
                            "title": logotipo_name,
                            "parents": [{"id": subfolder_id}]
                        })
                        gfile_logo.SetContentFile(logotipo_path)
                        gfile_logo.Upload()
                        logotipo_link = f"https://drive.google.com/file/d/{gfile_logo['id']}/view"
                        os.remove(logotipo_path)

                    # --- Upload dos documentos ---
                    documentos_links = []
                    for doc in documentos or []:
                        doc_name = doc.name
                        doc_path = os.path.join(tempfile.gettempdir(), doc_name)
                        with open(doc_path, "wb") as f:
                            f.write(doc.getbuffer())
                        
                        gfile_doc = drive.CreateFile({
                            "title": doc_name,
                            "parents": [{"id": subfolder_id}]
                        })
                        gfile_doc.SetContentFile(doc_path)
                        gfile_doc.Upload()
                        documentos_links.append(f"https://drive.google.com/file/d/{gfile_doc['id']}/view")
                        os.remove(doc_path)

                    # --- Salvar no MongoDB ---
                    data = {    
                        "titulo": nome_organizacao,
                        "descricao": descricao,
                        "tema": tema,
                        "cnpj": CNPJ,
                        "sigla": sigla,
                        "logotipo": logotipo_link,
                        "documentos": documentos_links,
                        "tipo": tipo_doc,
                        "websites": websites,
                        "subfolder_id": subfolder_id,
                        "enviado_por": st.session_state["nome"],
                        "data_upload": datetime.now()
                    }

                    organizacoes.insert_one(data)
                    st.success("Organização cadastrada com sucesso!")

                except Exception as e:
                    st.error(f"Erro no upload: {e}")


    # 1. Cadastro de publicação ---------------------------------------------------------------------------
    def enviar_publicacao():

      
        # Título da seção
        st.write('')
        st.subheader("Cadastrar publicação")

        # ----- CAMPOS DO FORMULÁRIO -----

        tipo = "Publicação"

        # Campo de texto: título da publicação
        titulo = st.text_input("Título")

        # Campo de texto longo: descrição da publicação
        descricao = st.text_area("Descrição")

        # Dropdown: ano de publicação (de hoje até 1950)
        anos = list(range(datetime.now().year, 1949, -1))
        ano_publicacao = st.selectbox("Ano de publicação", anos)

        # Campo multiselect para temas
        tema = st.multiselect("Tema", temas_ordenados)

        # Campo de texto: autor(es)
        autor = st.text_input("Autor(es) / Autora(s)")

        # Pega as organizações cadastradas no MongoDB
        organizacoes_disponiveis = sorted([doc.get("titulo") for doc in organizacoes.find()])

        # Multiselect com opção de cadastrar nova organização
        organizacao = st.multiselect(
            "Organização responsável",
            ["+ Cadastrar nova organização"] + organizacoes_disponiveis)

        # Upload do arquivo (apenas tipos permitidos)
        arquivo = st.file_uploader("Selecione o arquivo", type=["pdf", "doc", "docx"])

        # Se o usuário escolheu cadastrar nova organização
        if "+ Cadastrar nova organização" in organizacao:
            cadastrar_organizacao()

        # ----- BOTÃO DE ENVIO E COLUNAS -----

        # Layout: duas colunas para botão e feedback
        col1, col2 = st.columns([1, 6])
        col1.write('')  # espaçamento

        # Botão de envio
        submitted = col1.button(":material/check: Enviar", type="primary", use_container_width=True)

        # ----- LÓGICA DE SUBMISSÃO -----
        if submitted:

            # Validação: todos os campos obrigatórios devem estar preenchidos
            if not titulo or not descricao or not anos or not tema or not autor or not organizacao or not arquivo:
                st.error("Todos os campos são obrigatórios.")

      
            with st.spinner('Enviando documento...'):

                # Monta o nome do arquivo com a extensão original
                extensao = os.path.splitext(arquivo.name)[1]
                titulo_com_extensao = f"{titulo.strip()}{extensao}"

                # Envia o arquivo ao Google Drive e retorna o ID do arquivo
                file_link, thumb_link = upload_to_drive(arquivo, titulo_com_extensao, tipo)

                # Prepara o dicionário com os dados para salvar no MongoDB
                data = {
                    "titulo": titulo,
                    "descricao": descricao,
                    "ano_publicacao": ano_publicacao,
                    "tema": tema,
                    "autor": autor,
                    "organizacao": organizacao,
                    "tipo": tipo,
                    "enviado_por": st.session_state["nome"],
                    "link": file_link,
                    "thumb_link": thumb_link,
                    "data_upload": datetime.now()

                }

                # Insere o documento na coleção `publicacoes`
                publicacoes.insert_one(data)

                # Mostra mensagem de sucesso
                st.success("Documento cadastrado com sucesso!")



    # 2. Cadastro de imagem ---------------------------------------------------------------------------
    def enviar_imagem():

        # Título da seção
        st.write('')
        st.subheader("Cadastrar imagem")

        # ----- CAMPOS DO FORMULÁRIO -----

        tipo_doc = "Imagem"

        # Campo de texto: título
        titulo = st.text_input("Título")

        # Campo de texto longo: descrição
        descricao = st.text_area("Descrição")

        # Dropdown: ano (de hoje até 1950)
        anos = list(range(datetime.now().year, 1949, -1))
        ano_publicacao = st.selectbox("Ano de referência", anos)

        # Campo multiselect para temas
        tema = st.multiselect("Tema", temas_ordenados)

        # Campo de texto: autor(es)
        autor = st.text_input("Autor(es) / Autora(s)")

        # Pega as organizações cadastradas no MongoDB
        organizacoes_disponiveis = sorted([doc.get("titulo") for doc in organizacoes.find()])

        # Multiselect com opção de cadastrar nova organização
        organizacao = st.multiselect(
            "A imagem está relacionada à atuação de alguma organização?",
            ["+ Cadastrar nova organização", "Nenhuma organização"] + organizacoes_disponiveis)

        # Tipo de licença da imagem
        licenca = st.selectbox(
            "Qual é a licença de uso da imagem?",
            ["Protegida por direitos autorais", "Creative Commons", "Liberada para usos não-comerciais"]
        )

        # Contato para direitos autorais
        cols = st.columns(3)

        nome_contato = cols[0].text_input("Contato para tratar sobre direitos de uso da imagem")
        telefone_contato = cols[1].text_input("Telefone")
        email_contato = cols[2].text_input("E-mail")

        # Upload do arquivo (apenas tipos permitidos)
        arquivo = st.file_uploader("Selecione o arquivo", type=["png", "jpg", "jpeg"])

        # Se o usuário escolheu cadastrar nova organização
        if "+ Cadastrar nova organização" in organizacao:
            cadastrar_organizacao()


        # ----- BOTÃO DE ENVIO E COLUNAS -----

        # Layout: duas colunas para botão e feedback
        col1, col2 = st.columns([1, 6])
        col1.write('')  # espaçamento

        # Botão de envio
        submitted = col1.button(":material/check: Enviar", type="primary", use_container_width=True)


        # ----- LÓGICA DE SUBMISSÃO -----
        if submitted:

            # Validação: todos os campos obrigatórios devem estar preenchidos
            if not titulo or not descricao or not anos or not tema or not autor or not organizacao or not arquivo:
                st.error("Todos os campos são obrigatórios.")

            else:
                try:
                    with st.spinner('Enviando documento...'):

                        # Monta o nome do arquivo com a extensão original
                        extensao = os.path.splitext(arquivo.name)[1]
                        titulo_com_extensao = f"{titulo.strip()}{extensao}"

                        # Envia o arquivo ao Google Drive e retorna o ID do arquivo
                        file_link, thumb_link = upload_to_drive(arquivo, titulo_com_extensao, tipo_doc)

                        # Prepara o dicionário com os dados para salvar no MongoDB
                        data = {
                            "titulo": titulo,
                            "descricao": descricao,
                            "ano_publicacao": ano_publicacao,
                            "tema": tema,
                            "autor": autor,
                            "organizacao": organizacao,
                            "licenca": licenca,
                            "nome_contato": nome_contato,
                            "telefone_contato": telefone_contato,
                            "email_contato": email_contato,
                            "tipo": tipo_doc,
                            "enviado_por": st.session_state["nome"],
                            "link": file_link,
                            "thumb_link": thumb_link,
                            "data_upload": datetime.now()

                        }

                        # Insere o documento na coleção `imagens`
                        imagens.insert_one(data)

                        # Mostra mensagem de sucesso
                        st.success("Documento enviado com sucesso!")

                except Exception as e:
                    # Mensagem de erro em caso de falha no processo
                    st.error(f"Erro no upload: {e}")


    # 3. Cadastro de relatório ---------------------------------------------------------------------------
    def enviar_relatorio(): 

        # # ----- PREPARAÇÃO DO DROPDOWN DE TEMAS -----

        # # Ordena alfabeticamente os temas do babacu (exceto "Outro", que fica no final)
        # temas_ordenados = sorted([t for t in TEMAS_BABACU])
        # temas_ordenados.append("Outro")

        # # Adiciona uma opção vazia no início
        # temas_ordenados = [""] + temas_ordenados

        # Título da seção
        st.write('')
        st.subheader("Cadastrar relatório")    

        # ----- CAMPOS DO FORMULÁRIO -----

        tipo_doc = "Relatório" 

        # Campo de texto: título
        titulo = st.text_input("Título")

        # Campo de texto longo: descrição
        descricao = st.text_area("Descrição")

        # Dropdown: ano (de hoje até 1950)
        anos = list(range(datetime.now().year, 1949, -1))
        ano_publicacao = st.selectbox("Ano de publicação", anos)

        # Campo multiselect para temas
        tema = st.multiselect("Tema", temas_ordenados)

        # Campo de texto: autor(es)
        autor = st.text_input("Autor(es) / Autora(s)")

        # Pega as organizações cadastradas no MongoDB
        organizacoes_disponiveis = sorted([doc.get("titulo") for doc in organizacoes.find()])

        # Multiselect com opção de cadastrar nova organização
        organizacao = st.multiselect(
            "Organização responsável",
            ["+ Cadastrar nova organização", "Nenhuma organização"] + organizacoes_disponiveis)

        # Upload do arquivo (apenas tipos permitidos)
        arquivo = st.file_uploader("Selecione o arquivo", type=["pdf", "doc", "docx"])    #!!!!

        # Se o usuário escolheu cadastrar nova organização
        if "+ Cadastrar nova organização" in organizacao:
            cadastrar_organizacao()


        # ----- BOTÃO DE ENVIO E COLUNAS -----

        # Layout: duas colunas para botão e feedback
        col1, col2 = st.columns([1, 6])
        col1.write('')  # espaçamento

        # Botão de envio
        submitted = col1.button(":material/check: Enviar", type="primary", use_container_width=True)


        # ----- LÓGICA DE SUBMISSÃO -----
        if submitted:

            # Validação: todos os campos obrigatórios devem estar preenchidos
            if not titulo or not descricao or not anos or not tema or not autor or not organizacao or not arquivo:
                st.error("Todos os campos são obrigatórios.")

            else:
                try:
                    with st.spinner('Enviando documento...'):

                        # Monta o nome do arquivo com a extensão original
                        extensao = os.path.splitext(arquivo.name)[1]
                        titulo_com_extensao = f"{titulo.strip()}{extensao}"

                        # Envia o arquivo ao Google Drive e retorna o ID do arquivo
                        file_link, thumb_link = upload_to_drive(arquivo, titulo_com_extensao, tipo_doc)

                        # Prepara o dicionário com os dados para salvar no MongoDB
                        data = {     
                            "titulo": titulo,
                            "descricao": descricao,
                            "ano_publicacao": ano_publicacao,
                            "tema": tema,
                            "autor": autor,
                            "organizacao": organizacao,
                            "tipo": tipo_doc,
                            "link": file_link,
                            "thumb_link": thumb_link,
                            "enviado_por": st.session_state["nome"],
                            "data_upload": datetime.now()

                        }

                        # Insere o documento na coleção
                        relatorios.insert_one(data)   

                        # Mostra mensagem de sucesso
                        st.success("Documento enviado com sucesso!")

                except Exception as e:
                    # Mensagem de erro em caso de falha no processo
                    st.error(f"Erro no upload: {e}")


    # 4. Cadastro de vídeo ---------------------------------------------------------------------------
    def enviar_video(): #!!!!

        # # ----- PREPARAÇÃO DO DROPDOWN DE TEMAS -----

        # # Ordena alfabeticamente os temas do babacu (exceto "Outro", que fica no final)
        # temas_ordenados = sorted([t for t in TEMAS_BABACU])
        # temas_ordenados.append("Outro")

        # # Adiciona uma opção vazia no início
        # temas_ordenados = [""] + temas_ordenados

        # Título da seção
        st.write('')
        st.subheader("Cadastrar vídeo")    #!!!!

        # ----- CAMPOS DO FORMULÁRIO -----

        tipo_doc = "Vídeo" #!!!!

        # Campo de texto: título
        titulo = st.text_input("Título")

        # Campo de texto longo: descrição
        descricao = st.text_area("Descrição")

        # Dropdown: ano (de hoje até 1950)
        anos = list(range(datetime.now().year, 1949, -1))
        ano_publicacao = st.selectbox("Ano de publicação", anos)

        # Campo multiselect para temas
        tema = st.multiselect("Tema", temas_ordenados)

        # Campo de texto: autor(es)
        autor = st.text_input("Autor(es) / Autora(s)")

        # Pega as organizações cadastradas no MongoDB
        organizacoes_disponiveis = sorted([doc.get("titulo") for doc in organizacoes.find()])

        # Multiselect com opção de cadastrar nova organização
        organizacao = st.multiselect(
            "Organização responsável",
            ["+ Cadastrar nova organização", "Nenhuma organização"] + organizacoes_disponiveis)

        # Campo de texto: título
        link_video = st.text_input("Link do vídeo")


        # Obtendo a thumb do vídeo do youtube ------------------
        def get_youtube_thumb(link: str, resolution="mqdefault"):
            """
            Retorna URL da miniatura do YouTube
            resolution: default, mqdefault, mqdefault, sddefault, maxresdefault
            """
            if not link:
                return None

            # Extrai o ID do vídeo
            video_id = None
            # YouTube normal
            m = re.search(r"v=([a-zA-Z0-9_-]{11})", link)
            if m:
                video_id = m.group(1)
            # YouTube curto youtu.be
            m = re.search(r"youtu\.be/([a-zA-Z0-9_-]{11})", link)
            if m:
                video_id = m.group(1)

            if not video_id:
                return None

            # Monta link da thumbnail
            return f"https://img.youtube.com/vi/{video_id}/{resolution}.jpg"

        # Obtém URL da miniatura
        thumb_link = get_youtube_thumb(link_video)

        # --------------------------




        # Se o usuário escolheu cadastrar nova organização
        if "+ Cadastrar nova organização" in organizacao:
            cadastrar_organizacao()


        # ----- BOTÃO DE ENVIO E COLUNAS -----

        # Layout: duas colunas para botão e feedback
        col1, col2 = st.columns([1, 6])
        col1.write('')  # espaçamento

        # Botão de envio
        submitted = col1.button(":material/check: Enviar", type="primary", use_container_width=True)


        # ----- LÓGICA DE SUBMISSÃO -----
        if submitted:

            # Validação: todos os campos obrigatórios devem estar preenchidos
            if not titulo or not descricao or not anos or not tema or not autor or not organizacao or not link_video:
                st.error("Todos os campos são obrigatórios.")

            else:
                try:
                    with st.spinner('Enviando documento...'):


                        # Prepara o dicionário com os dados para salvar no MongoDB
                        data = {     #!!!!
                            "titulo": titulo,
                            "descricao": descricao,
                            "ano_publicacao": ano_publicacao,
                            "tema": tema,
                            "autor": autor,
                            "organizacao": organizacao,
                            "tipo": tipo_doc,
                            "link": link_video,
                            "thumb_link": thumb_link,
                            "enviado_por": st.session_state["nome"],
                            "data_upload": datetime.now()

                        }

                        # Insere o documento na coleção
                        videos.insert_one(data)

                        # Mostra mensagem de sucesso
                        st.success("Documento enviado com sucesso!")

                except Exception as e:
                    # Mensagem de erro em caso de falha no processo
                    st.error(f"Erro no upload: {e}")


    # 5. Cadastro de podcast ---------------------------------------------------------------------------
    def enviar_podcast(): 

        # Título da seção
        st.write('')
        st.subheader("Cadastrar podcast")    

        # ----- CAMPOS DO FORMULÁRIO -----

        tipo_doc = "Podcast" 

        # Campo de texto: título
        titulo = st.text_input("Título")

        # Campo de texto longo: descrição
        descricao = st.text_area("Descrição")

        # Dropdown: ano (de hoje até 1950)
        anos = list(range(datetime.now().year, 1949, -1))
        ano_publicacao = st.selectbox("Ano de publicação", anos)

        # Campo multiselect para temas
        tema = st.multiselect("Tema", temas_ordenados)

        # Campo de texto: autor(es)
        autor = st.text_input("Autor(es) / Autora(s)")

        # Pega as organizações cadastradas no MongoDB
        organizacoes_disponiveis = sorted([doc.get("titulo") for doc in organizacoes.find()])

        # Multiselect com opção de cadastrar nova organização
        organizacao = st.multiselect(
            "Organização responsável",
            ["+ Cadastrar nova organização", "Nenhuma organização"] + organizacoes_disponiveis)

        # Upload da imagem para thumb
        thumb = st.file_uploader("Insira uma imagem do podcast (pode ser um print da tela)", type=["png", "jpg", "jpeg"])


        # Campo de texto: título
        link_podcast = st.text_input("Link do podcast")

        # Se o usuário escolheu cadastrar nova organização
        if "+ Cadastrar nova organização" in organizacao:
            cadastrar_organizacao()


        # ----- BOTÃO DE ENVIO E COLUNAS -----

        # Layout: duas colunas para botão e feedback
        col1, col2 = st.columns([1, 6])
        col1.write('')  # espaçamento

        # Botão de envio
        submitted = col1.button(":material/check: Enviar", type="primary", use_container_width=True)


        # ----- LÓGICA DE SUBMISSÃO -----


        if submitted:

            # Verifica campos obrigatórios
            if not titulo or not link_podcast:
                st.error("Preencha título e link.")
                return

            with st.spinner("Enviando ..."):
                
                # Envia screenshot ao Google Drive
                thumb_link = None
                if thumb:
                    thumb_link = upload_thumbnail_to_drive(
                        local_path=thumb,
                        nome_base=titulo,
                        tipo=tipo_doc
                    )

                # Salva no MongoDB
                data = {
                    "titulo": titulo,
                    "descricao": descricao,
                    "tema": tema,
                    "autor": autor,
                    "organizacao": organizacao,
                    "link": link_podcast,
                    "thumb_link": thumb_link,
                    "tipo": tipo_doc,
                    "enviado_por": st.session_state["nome"],
                    "ano_publicacao": ano_publicacao,
                    "data_upload": datetime.now()
                }
                podcasts.insert_one(data)
                st.success("Podcast cadastrado com sucesso!")



    # 6. Cadastro de site ---------------------------------------------------------------------------

    def enviar_site(): 

        # Título da seção
        st.write('')
        st.subheader("Cadastrar site")    

        tipo_doc = "Site" 

        # ----- CAMPOS DO FORMULÁRIO -----
        titulo = st.text_input("Título")
        descricao = st.text_area("Descrição")
        tema = st.multiselect("Tema", temas_ordenados)
        autor = st.text_input("Autor(es) / Autora(s)")

        organizacoes_disponiveis = sorted([doc.get("titulo") for doc in organizacoes.find()])
        organizacao = st.multiselect(
            "Organização responsável",
            ["+ Cadastrar nova organização", "Nenhuma organização"] + organizacoes_disponiveis
        )

        # Upload da imagem para thumb
        thumb_local = st.file_uploader("Insira uma imagem do site (pode ser um print da tela)", type=["png", "jpg", "jpeg"])

        link_site = st.text_input("Link do site")

        # Se o usuário escolheu cadastrar nova organização
        if "+ Cadastrar nova organização" in organizacao:
            cadastrar_organizacao()

        # ----- BOTÃO DE ENVIO E COLUNAS -----
        col1, col2 = st.columns([1, 6])
        col1.write('')  # espaçamento

        # Botão de envio
        submitted = col1.button(":material/check: Enviar", type="primary", use_container_width=True)

        # ----- LÓGICA DE SUBMISSÃO -----
        if submitted:

            # Verifica campos obrigatórios
            if not titulo or not descricao or not tema or not autor or not organizacao or not link_site:
                st.error("Todos os campos são obrigatórios.")
                return

            with st.spinner("Enviando ..."):


                # # Gerar miniatura local
                # thumb_local = gerar_thumbnail_pagina(link_site, titulo)

                # Envia screenshot ao Google Drive
                thumb_link = None
                if thumb_local:
                    thumb_link = upload_thumbnail_to_drive(
                        local_path=thumb_local,
                        nome_base=titulo,
                        tipo=tipo_doc
                    )


                # Salva no MongoDB
                data = {
                    "titulo": titulo,
                    "descricao": descricao,
                    "tema": tema,
                    "autor": autor,
                    "organizacao": organizacao,
                    "tipo": tipo_doc,
                    "link": link_site,
                    "thumb_link": thumb_link,
                    "enviado_por": st.session_state["nome"],
                    "data_upload": datetime.now()
                }

                sites.insert_one(data)
                st.success("Site cadastrado com sucesso!")



    # 7. Cadastro de mapa ---------------------------------------------------------------------------
    def enviar_mapa(): 

        # ----- PREPARAÇÃO DO DROPDOWN DE TEMAS -----

        # Ordena alfabeticamente os temas do babacu (exceto "Outro", que fica no final)
        temas_ordenados = sorted([t for t in TEMAS_BABACU])
        temas_ordenados.append("Outro")

        # Adiciona uma opção vazia no início
        temas_ordenados = [""] + temas_ordenados

        # Título da seção
        st.write('')
        st.subheader("Cadastrar mapa")    

        # ----- CAMPOS DO FORMULÁRIO -----

        tipo_doc = "Mapa" 

        # Campo de texto: título
        titulo = st.text_input("Título")

        # Campo de texto longo: descrição
        descricao = st.text_area("Descrição")

        # Dropdown: ano (de hoje até 1950)
        anos = list(range(datetime.now().year, 1949, -1))
        ano_publicacao = st.selectbox("Ano de publicação", anos)

        # Campo multiselect para temas
        tema = st.multiselect("Tema", temas_ordenados)

        # Campo de texto: autor(es)
        autor = st.text_input("Autor(es) / Autora(s)")

        # Pega as organizações cadastradas no MongoDB
        organizacoes_disponiveis = sorted([doc.get("titulo") for doc in organizacoes.find()])

        # Multiselect com opção de cadastrar nova organização
        organizacao = st.multiselect(
            "Organização responsável",
            ["+ Cadastrar nova organização", "Nenhuma organização"] + organizacoes_disponiveis)

        # Upload do arquivo (apenas tipos permitidos)
        arquivo = st.file_uploader("Selecione o arquivo", type=["pdf", "png", "jpg", "jpeg"])

        # Se o usuário escolheu cadastrar nova organização
        if "+ Cadastrar nova organização" in organizacao:
            cadastrar_organizacao()


        # ----- BOTÃO DE ENVIO E COLUNAS -----

        # Layout: duas colunas para botão e feedback
        col1, col2 = st.columns([1, 6])
        col1.write('')  # espaçamento

        # Botão de envio
        submitted = col1.button(":material/check: Enviar", type="primary", use_container_width=True)


        # ----- LÓGICA DE SUBMISSÃO -----
        if submitted:

            # Validação: todos os campos obrigatórios devem estar preenchidos
            if not titulo or not descricao or not tema or not ano_publicacao or not autor or not organizacao or not arquivo: #!!!!
                st.error("Todos os campos são obrigatórios.")

            else:
                try:
                    with st.spinner('Enviando documento...'):

                        # Monta o nome do arquivo com a extensão original
                        extensao = os.path.splitext(arquivo.name)[1]
                        titulo_com_extensao = f"{titulo.strip()}{extensao}"

                        # Envia o arquivo ao Google Drive e retorna o ID do arquivo
                        file_link, thumb_link = upload_to_drive(arquivo, titulo_com_extensao, tipo_doc)

                        # Prepara o dicionário com os dados para salvar no MongoDB
                        data = {     #!!!!
                            "titulo": titulo,
                            "descricao": descricao,
                            "ano_publicacao": ano_publicacao,
                            "tema": tema,
                            "autor": autor,
                            "organizacao": organizacao,
                            "tipo": tipo_doc,
                            "thumb_link": thumb_link,
                            "link": file_link,
                            "enviado_por": st.session_state["nome"],
                            "data_upload": datetime.now()

                        }

                        # Insere o documento na coleção
                        mapas.insert_one(data)   #!!!!

                        # Mostra mensagem de sucesso
                        st.success("Documento enviado com sucesso!")

                except Exception as e:
                    # Mensagem de erro em caso de falha no processo
                    st.error(f"Erro no upload: {e}")


    # 8. Cadastro de legislacao ---------------------------------------------------------------------------
    def enviar_legislacao(): 


        # Título da seção
        st.write('')
        st.subheader("Cadastrar legislação")    

        # ----- CAMPOS DO FORMULÁRIO -----

        tipo_doc = "Legislação" 

        # Campo de texto: título
        titulo = st.text_input("Título")

        # Campo de texto longo: descrição
        descricao = st.text_area("Descrição")

        # Dropdown: ano (de hoje até 1950)
        anos = list(range(datetime.now().year, 1949, -1))
        ano_publicacao = st.selectbox("Ano de publicação", anos)

        # Campo multiselect para temas
        tema = st.multiselect("Tema", temas_ordenados)

        # Campo de texto: autor(es)
        autor = st.text_input("Autor(es) / Autora(s)")

        # Campo de texto: casa legislativa
        casa_legislativa = st.text_input("Casa legislativa")



        # Campo de texto: título
        link_legislacao = st.text_input("Link da legislação")



        # ----- BOTÃO DE ENVIO E COLUNAS -----

        # Layout: duas colunas para botão e feedback
        col1, col2 = st.columns([1, 6])
        col1.write('')  # espaçamento

        # Botão de envio
        submitted = col1.button(":material/check: Enviar", type="primary", use_container_width=True)


        # ----- LÓGICA DE SUBMISSÃO -----
        if submitted:

            # Validação: todos os campos obrigatórios devem estar preenchidos
            if not titulo or not descricao or not anos or not tema or not autor or not casa_legislativa or not link_legislacao: #!!!!
                st.error("Todos os campos são obrigatórios.")

            else:
                try:
                    with st.spinner('Enviando documento...'):


                        # Prepara o dicionário com os dados para salvar no MongoDB
                        data = {    
                            "titulo": titulo,
                            "descricao": descricao,
                            "ano_publicacao": ano_publicacao,
                            "tema": tema,
                            "autor": autor,
                            "casa_legislativa": casa_legislativa,
                            "tipo": tipo_doc,
                            "link": link_legislacao,
                            "enviado_por": st.session_state["nome"],
                            "data_upload": datetime.now()

                        }

                        # Insere o documento na coleção
                        legislacao.insert_one(data) 

                        # Mostra mensagem de sucesso
                        st.success("Documento enviado com sucesso!")

                except Exception as e:
                    # Mensagem de erro em caso de falha no processo
                    st.error(f"Erro no upload: {e}")



    # 9. Cadastro de ponto de interesse ---------------------------------------------------------------------------
    def enviar_ponto(): 


        # Título da seção
        st.write('')
        st.subheader("Cadastrar ponto de interesse")    

        # ----- CAMPOS DO FORMULÁRIO -----

        tipo_doc = "Ponto de interesse" 

        # Campo de texto: título
        titulo = st.text_input("Título")

        # Campo de texto longo: descrição
        descricao = st.text_area("Descrição")


        # Campo multiselect para temas
        tema = st.multiselect("Tema", temas_ordenados)

        # Pega as organizações cadastradas no MongoDB
        organizacoes_disponiveis = sorted([doc.get("titulo") for doc in organizacoes.find()])

        # Multiselect com opção de cadastrar nova organização
        organizacao = st.multiselect(
            "O ponto está relacionado à atuação de alguma organização?",
            ["+ Cadastrar nova organização", "Nenhuma organização"] + organizacoes_disponiveis)

        # Upload da imagem para thumb
        thumb_local = st.file_uploader("Insira uma imagem do local ou um print da tela do mapa", type=["png", "jpg", "jpeg"])

        # Campo de texto: título
        link_google_maps = st.text_input("Link do Google Maps")

        # Se o usuário escolheu cadastrar nova organização
        if "+ Cadastrar nova organização" in organizacao:
            cadastrar_organizacao()


        # ----- BOTÃO DE ENVIO E COLUNAS -----

        # Layout: duas colunas para botão e feedback
        col1, col2 = st.columns([1, 6])
        col1.write('')  # espaçamento

        # Botão de envio
        submitted = col1.button(":material/check: Enviar", type="primary", use_container_width=True)


        # ----- LÓGICA DE SUBMISSÃO -----
        if submitted:

            # Validação: todos os campos obrigatórios devem estar preenchidos
            if not titulo or not descricao or not tema or not organizacao or not link_google_maps: 
                st.error("Todos os campos são obrigatórios.")


            with st.spinner("Enviando ..."):

                def extrair_lat_long_google_maps(link):
                    try:
                        # Extrai a parte após o "@"
                        coordenadas = link.split("@")[1].split(",")
                        latitude = coordenadas[0]
                        longitude = coordenadas[1]
                        return latitude, longitude
                    except (IndexError, AttributeError):
                        return None, None


                # Extrai a latitude e longitude do link do google maps
                latitude, longitude = extrair_lat_long_google_maps(link_google_maps)

                # Envia screenshot ao Google Drive
                thumb_link = None
                if thumb_local:
                    thumb_link = upload_thumbnail_to_drive(
                        local_path=thumb_local,
                        nome_base=titulo,
                        tipo=tipo_doc
                    )



                # Prepara o dicionário com os dados para salvar no MongoDB
                data = {     
                    "titulo": titulo,
                    "descricao": descricao,
                    "tema": tema,
                    "latitude": latitude,
                    "longitude": longitude,
                    "tipo": tipo_doc,
                    "link": link_google_maps,
                    "thumb_link": thumb_link,
                    "enviado_por": st.session_state["nome"],
                    "data_upload": datetime.now()
                }

                # Insere o documento na coleção
                pontos_interesse.insert_one(data)   

                # Mostra mensagem de sucesso
                st.success("Ponto de interesse enviado com sucesso!")


    # 10. Cadastro de projeto ---------------------------------------------------------------------------
    def enviar_projeto(): 
        st.write('')
        st.subheader("Cadastrar projeto")    

        tipo_doc = "Projeto" 

        # Campos do formulário
        
        nome_projeto = st.text_input("Nome do projeto")
        

        # Pega as organizações cadastradas no MongoDB
        organizacoes_disponiveis = sorted([doc.get("titulo") for doc in organizacoes.find()])

        # Multiselect com opção de cadastrar nova organização
        organizacao = st.multiselect(
            "Organização responsável",
            ["+ Cadastrar nova organização"] + organizacoes_disponiveis)
        
        # Se o usuário escolheu cadastrar nova organização
        if "+ Cadastrar nova organização" in organizacao:
            cadastrar_organizacao()

        fonte_recursos = st.text_input("Fonte de recursos")
        
        # Datas
        col1, col2 = st.columns(2)
        data_inicio = col1.date_input("Data de inicio", min_value=datetime(1900, 1, 1))
        data_fim = col2.date_input("Data de fim")
        # Converter para datetime
        data_inicio = datetime(data_inicio.year, data_inicio.month, data_inicio.day)
        data_fim = datetime(data_fim.year, data_fim.month, data_fim.day)
       
        objetivo = st.text_area("Objetivo Geral do projeto")
        
        descricao = st.text_area("Descrição")
        tema = st.multiselect("Tema", temas_ordenados)
        
        website = st.text_input("Websites (separados por vírgula)")
        
        documentos = st.file_uploader(
            "Documentos do projeto", 
            accept_multiple_files=True, 
            type=["pdf", "png", "jpg"]
        )

        # Botão de envio
        col1, col2 = st.columns([1, 6])
        col1.write('')
        submitted = col1.button(":material/check: Enviar", type="primary", use_container_width=True)

        if submitted:
            if not nome_projeto:
                st.error("Insira o nome do projeto.")
                return

            with st.spinner('Enviando ...'):
                try:
                    drive = authenticate_drive()
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

                    # pegar a correspondência de tipo_doc em TIPO_PASTA_MAP
                    tipo_key = TIPO_PASTA_MAP.get(tipo_doc)
                    


                    parent_folder_id = st.secrets["pastas"].get(tipo_key)
                    if not parent_folder_id:
                        st.error(f"Pasta para tipo '{tipo_doc}' não configurada no secrets.")
                        return

                    # Criar subpasta do projeto
                    subfolder_name = f"{timestamp}_{nome_projeto.replace(' ', '_')}"
                    subfolder = drive.CreateFile({
                        "title": subfolder_name,
                        "mimeType": "application/vnd.google-apps.folder",
                        "parents": [{"id": parent_folder_id}]
                    })
                    subfolder.Upload()
                    subfolder_id = subfolder["id"]

                    # --- Upload dos documentos ---
                    documentos_links = []
                    for doc in documentos or []:
                        doc_name = doc.name
                        doc_path = os.path.join(tempfile.gettempdir(), doc_name)
                        with open(doc_path, "wb") as f:
                            f.write(doc.getbuffer())
                        
                        gfile_doc = drive.CreateFile({
                            "title": doc_name,
                            "parents": [{"id": subfolder_id}]
                        })
                        gfile_doc.SetContentFile(doc_path)
                        gfile_doc.Upload()
                        documentos_links.append(f"https://drive.google.com/file/d/{gfile_doc['id']}/view")
                        os.remove(doc_path)

                    # --- Salvar no MongoDB ---
                    data = {    
                        "titulo": nome_projeto,
                        "descricao": descricao,
                        "tema": tema,
                        "objetivo": objetivo,
                        "documentos": documentos_links,
                        "tipo": tipo_doc,
                        "organizacao": organizacao,
                        "fonte_recursos": fonte_recursos,
                        "data_inicio": data_inicio,
                        "data_fim": data_fim,
                        "website": website,
                        "subfolder_id": subfolder_id,
                        "enviado_por": st.session_state["nome"],
                        "data_upload": datetime.now()
                    }

                    projetos.insert_one(data)
                    st.success("Projeto cadastrado com sucesso!")

                except Exception as e:
                    st.error(f"Erro no upload: {e}")

        
    # 10. Cadastro de projeto ---------------------------------------------------------------------------
    def enviar_pesquisa(): 
        st.write('')
        st.subheader("Cadastrar pesquisa")    

        tipo_doc = "Pesquisa" 

        # Campos do formulário
        
        nome_pesquisa = st.text_input("Nome da pesquisa")
        

        # Pega as organizações cadastradas no MongoDB
        organizacoes_disponiveis = sorted([doc.get("titulo") for doc in organizacoes.find()])

        # Multiselect com opção de cadastrar nova organização
        organizacao = st.multiselect(
            "Organização responsável",
            ["+ Cadastrar nova organização"] + organizacoes_disponiveis)
        
        # Se o usuário escolheu cadastrar nova organização
        if "+ Cadastrar nova organização" in organizacao:
            cadastrar_organizacao()

        ano_publicacao = st.text_input("Ano de publicação")
        
        autor = st.text_input("Autor(es/as)")

        descricao = st.text_area("Resumo executivo da pesquisa")
        
        tema = st.multiselect("Tema", temas_ordenados)
        
        
        documentos = st.file_uploader(
            "Documentos da pesquisa", 
            accept_multiple_files=True, 
            type=["pdf", "png", "jpg"]
        )

        # Botão de envio
        col1, col2 = st.columns([1, 6])
        col1.write('')
        submitted = col1.button(":material/check: Enviar", type="primary", use_container_width=True)

        if submitted:
            if not nome_pesquisa:
                st.error("Insira o nome da pesquisa.")
                return

            with st.spinner('Enviando ...'):
                try:
                    drive = authenticate_drive()
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

                    # pegar a correspondência de tipo_doc em TIPO_PASTA_MAP
                    tipo_key = TIPO_PASTA_MAP.get(tipo_doc)
                    


                    parent_folder_id = st.secrets["pastas"].get(tipo_key)
                    if not parent_folder_id:
                        st.error(f"Pasta para tipo '{tipo_doc}' não configurada no secrets.")
                        return

                    # Criar subpasta do projeto
                    subfolder_name = f"{timestamp}_{nome_pesquisa.replace(' ', '_')}"
                    subfolder = drive.CreateFile({
                        "title": subfolder_name,
                        "mimeType": "application/vnd.google-apps.folder",
                        "parents": [{"id": parent_folder_id}]
                    })
                    subfolder.Upload()
                    subfolder_id = subfolder["id"]


                    # --- Upload dos documentos ---
                    documentos_links = []
                    for doc in documentos or []:
                        doc_name = doc.name
                        doc_path = os.path.join(tempfile.gettempdir(), doc_name)
                        with open(doc_path, "wb") as f:
                            f.write(doc.getbuffer())
                        
                        gfile_doc = drive.CreateFile({
                            "title": doc_name,
                            "parents": [{"id": subfolder_id}]
                        })
                        gfile_doc.SetContentFile(doc_path)
                        gfile_doc.Upload()
                        documentos_links.append(f"https://drive.google.com/file/d/{gfile_doc['id']}/view")
                        os.remove(doc_path)

                    # --- Salvar no MongoDB ---
                    data = {    
                        "titulo": nome_pesquisa,
                        "ano_publicacao": ano_publicacao,
                        "autor": autor,
                        "descricao": descricao,
                        "tema": tema,
                        "documentos": documentos_links,
                        "tipo": tipo_doc,
                        "organizacao": organizacao,
                        "subfolder_id": subfolder_id,
                        "enviado_por": st.session_state["nome"],
                        "data_upload": datetime.now()
                    }

                    pesquisas.insert_one(data)
                    st.success("Pesquisa cadastrada com sucesso!")

                except Exception as e:
                    st.error(f"Erro no upload: {e}")




    if acao == "Cadastrar documento":
        # Escolha do tipo de mídia


        # 1. Dicionário: valor real -> rótulo com ícone
        TIPOS_MIDIA = {
            "Organização": ":material/things_to_do: Organização",
            "Publicação": ":material/menu_book: Publicação",
            "Imagem": ":material/add_a_photo: Imagem",
            "Relatório": ":material/assignment: Relatório",
            "Vídeo": ":material/videocam: Vídeo",
            "Podcast": ":material/podcasts: Podcast",
            "Site": ":material/language: Site",
            "Mapa": ":material/map: Mapa",
            "Legislação": ":material/balance: Legislação",
            "Ponto de interesse": ":material/location_on: Ponto de interesse",
            "Projeto": ":material/assignment: Projeto",
            "Pesquisa": ":material/query_stats: Pesquisa",
        }

        # 2. Lista de rótulos com ícones
        rotulos_com_icone = list(TIPOS_MIDIA.values())

        # 3. Mostra os pills com ícone (seleção única)
        rotulo_selecionado = st.pills(
            label="Qual tipo de Mídia",
            options=rotulos_com_icone,
            selection_mode="single"
        )

        # 4. Converte de volta para o valor real
        midia_selecionada = next(
            (tipo for tipo, rotulo in TIPOS_MIDIA.items() if rotulo == rotulo_selecionado),
            None
        )

  
        if midia_selecionada == "Organização":
            enviar_organizacao()
        elif midia_selecionada == "Publicação":
            enviar_publicacao()
        elif midia_selecionada == "Imagem":
            enviar_imagem()
        elif midia_selecionada == "Relatório":
            enviar_relatorio()
        elif midia_selecionada == "Vídeo":
            enviar_video()
        elif midia_selecionada == "Podcast":
            enviar_podcast()
        elif midia_selecionada == "Site":
            enviar_site()
        elif midia_selecionada == "Mapa":
            enviar_mapa()
        elif midia_selecionada == "Legislação":
            enviar_legislacao()
        elif midia_selecionada == "Ponto de interesse":
            enviar_ponto()
        elif midia_selecionada == "Projeto":
            enviar_projeto()
        elif midia_selecionada == "Pesquisa":
            enviar_pesquisa()



    elif acao == "Editar um documento":
        
        st.write('')

        # Selectbox para tipo de documento
        tipo_escolhido = st.selectbox(
            "Tipo de documento",
            sorted(TIPOS_MIDIA),
            width=300
        )

        # Filtrar apenas os documentos com o tipo selecionado
        arquivos_filtrados = [doc for doc in arquivos if doc.get("tipo") == tipo_escolhido]

        # Extrair apenas os títulos dos documentos filtrados
        lista_titulos = [doc.get("titulo", "") for doc in arquivos_filtrados]

        # Selectbox com os títulos filtrados
        titulo_escolhido = st.selectbox("Escolha o documento para editar", lista_titulos)

        # Encontra o documento com o título escolhido
        documento_escolhido = next((doc for doc in arquivos if doc.get("tipo") == tipo_escolhido and doc.get("titulo") == titulo_escolhido), None)


        # EDITAR ORGANIZAÇÃO

        if tipo_escolhido == "Organização":
            
            with st.form("Editar Organização"):

                # Preenche automaticamente se existir no documento, senão deixa vazio
                nome_organizacao = st.text_input(
                    "Nome da organização",
                    value=documento_escolhido.get("titulo", "")
                )

                sigla = st.text_input(
                    "Sigla da organização",
                    value=documento_escolhido.get("sigla", "")
                )

                descricao = st.text_area(
                    "Descrição",
                    value=documento_escolhido.get("descricao", "")
                )

                # Tema (multiselect)
                temas_documento = documento_escolhido.get("tema", [])
                if not isinstance(temas_documento, list):
                    temas_documento = [temas_documento] if temas_documento else []

                tema = st.multiselect(
                    "Tema",
                    temas_ordenados,
                    default=temas_documento  # respeita os já salvos
                )

                CNPJ = st.text_input(
                    "CNPJ",
                    value=documento_escolhido.get("cnpj", "")
                )

                websites = st.text_input(
                    "Websites (separados por vírgula)",
                    value=", ".join(documento_escolhido.get("websites", [])) 
                    if isinstance(documento_escolhido.get("websites"), list) 
                    else documento_escolhido.get("websites", "")
                )


                # Botão de Salvar
                submitted = st.form_submit_button("Salvar", icon=":material/save:")

                if submitted:
   
                    # Converter websites de string para lista
                    if isinstance(websites, str):
                        websites_lista = [w.strip() for w in websites.split(",") if w.strip()]
                    else:
                        websites_lista = websites

                    # Criar dicionário de dados para atualizar
                    data_atualizada = {
                        "titulo": nome_organizacao,
                        "descricao": descricao,
                        "tema": tema,
                        "cnpj": CNPJ,
                        "sigla": sigla,
                        # "documentos": documentos_links,
                        "tipo": documento_escolhido.get("tipo", "Organização"),
                        "websites": websites_lista,
                        "subfolder_id": documento_escolhido.get("subfolder_id"),
                        "enviado_por": st.session_state.get("nome"),
                        "data_upload": datetime.now()
                    }

                    # Atualiza o documento no MongoDB usando _id
                    resultado = organizacoes.update_one(
                        {"_id": ObjectId(documento_escolhido["_id"])},  # filtro pelo ID original
                        {"$set": data_atualizada},
                        upsert=False  # não cria novo documento, apenas atualiza
                    )

                    if resultado.modified_count > 0:
                        st.success("Documento atualizado com sucesso!")
                        time.sleep(3)
                        st.rerun()
                    else:
                        st.warning("Nenhuma alteração foi detectada ou o documento não foi atualizado.")                


        elif tipo_escolhido == "Publicação":

            with st.form("Editar Publicação"):

                # Preencher automaticamente com os valores existentes
                titulo = st.text_input(
                    "Título",
                    value=documento_escolhido.get("titulo", "")
                )

                descricao = st.text_area(
                    "Descrição",
                    value=documento_escolhido.get("descricao", "")
                )

                # Dropdown: ano de publicação
                anos = list(range(datetime.now().year, 1949, -1))
                ano_publicacao_atual = documento_escolhido.get("ano_publicacao", datetime.now().year)
                if ano_publicacao_atual not in anos:
                    ano_publicacao_atual = anos[0]  # fallback
                ano_publicacao = st.selectbox("Ano de publicação", anos, index=anos.index(ano_publicacao_atual))

                # Multiselect: tema
                temas_documento = documento_escolhido.get("tema", [])
                if not isinstance(temas_documento, list):
                    temas_documento = [temas_documento] if temas_documento else []
                tema = st.multiselect(
                    "Tema",
                    temas_ordenados,
                    default=temas_documento
                )

                # Autor(es)
                autor = st.text_input(
                    "Autor(es) / Autora(s)",
                    value=documento_escolhido.get("autor", "")
                )

                # Organizações
                organizacoes_disponiveis = sorted([doc.get("titulo") for doc in organizacoes.find()])
                organizacao_atual = documento_escolhido.get("organizacao", [])
                if not isinstance(organizacao_atual, list):
                    organizacao_atual = [organizacao_atual] if organizacao_atual else []


                organizacao = st.multiselect(
                    "Organização responsável",
                    ["+ Cadastrar nova organização"] + organizacoes_disponiveis,
                    default=organizacao_atual
                )

                # Botão de Salvar
                submitted = st.form_submit_button("Salvar", icon=":material/save:")

                if submitted:

                    # Validar campos obrigatórios
                    if not titulo or not descricao or not ano_publicacao or not tema or not autor or not organizacao:
                        st.error("Todos os campos obrigatórios devem ser preenchidos.")
                    else:
                        # Se tiver "+ Cadastrar nova organização", chamar função de cadastro
                        if "+ Cadastrar nova organização" in organizacao:
                            cadastrar_organizacao()

                        # Preparar dicionário para update
                        data_atualizada = {
                            "titulo": titulo,
                            "descricao": descricao,
                            "ano_publicacao": ano_publicacao,
                            "tema": tema,
                            "autor": autor,
                            "organizacao": organizacao,
                            "tipo": documento_escolhido.get("tipo", "Publicação"),
                            "enviado_por": st.session_state.get("nome"),
                            "data_upload": datetime.now()
                        }

                        # Atualiza o documento no MongoDB usando _id
                        resultado = publicacoes.update_one(
                            {"_id": ObjectId(documento_escolhido["_id"])},
                            {"$set": data_atualizada},
                            upsert=False
                        )

                        if resultado.modified_count > 0:
                            st.success("Publicação atualizada com sucesso!")
                            time.sleep(3)
                            st.rerun()
                        else:
                            st.warning("Nenhuma alteração foi detectada ou o documento não foi atualizado.")


        # elif tipo_escolhido == "Imagem":
        #     editar_imagem(titulo_escolhido)
        # elif tipo_escolhido == "Relatório":
        #     editar_relatorio(titulo_escolhido)
        # elif tipo_escolhido == "Vídeo":
        #     editar_video(titulo_escolhido)
        # elif tipo_escolhido == "Podcast":
        #     editar_podcast(titulo_escolhido)
        # elif tipo_escolhido == "Site":
        #     editar_site(titulo_escolhido)
        # elif tipo_escolhido == "Mapa":
        #     editar_mapa(titulo_escolhido)
        # elif tipo_escolhido == "Legislação":
        #     editar_legislacao(titulo_escolhido)
        # elif tipo_escolhido == "Ponto de interesse":
        #     editar_ponto(titulo_escolhido)































    elif acao == "Excluir um documento":
        st.write('')

        TIPOS_MIDIA_DEL = [tipo for tipo in TIPOS_MIDIA if tipo != "Organização"]

        # Selectbox para tipo de documento com valor vazio por padrão
        tipo_escolhido = st.selectbox(
            "Tipo de documento",
            [""] + sorted(TIPOS_MIDIA_DEL),  # adiciona opção vazia
            index=0,  # seleciona a primeira opção (vazio) por padrão
            width=300
        )

        # ???????
        # st.write(tipo_escolhido)

        if tipo_escolhido:
            # Filtrar apenas os documentos com o tipo selecionado
            arquivos_filtrados = [doc for doc in arquivos if doc.get("tipo") == tipo_escolhido]

            if arquivos_filtrados:
                # Extrair títulos dos documentos filtrados
                lista_titulos = [""] + [doc.get("titulo", "") for doc in arquivos_filtrados]

                # Selectbox com os títulos filtrados
                titulo_escolhido = st.selectbox("Escolha o documento para excluir", lista_titulos, index=0)

                # Encontra o documento com o título escolhido
                documento_escolhido = next(
                    (doc for doc in arquivos_filtrados if doc.get("titulo") == titulo_escolhido),
                    None
                )

                if documento_escolhido:
                    st.warning(f"Você está prestes a excluir: **{titulo_escolhido}**. Essa operação é irreversível. Você tem certeza?")
                    

                    if st.button("Confirmar exclusão", type="primary", icon=":material/delete:"):


                        # Determinar a coleção correta a partir do mapa
                        nome_colecao = TIPO_PASTA_MAP.get(tipo_escolhido)

                        # ??????????????????
                        # st.write(f"Nome da coleção: {nome_colecao}")

                        if nome_colecao:
                            colecao = globals().get(nome_colecao)  # pega a variável da coleção pelo nome

                            # ??????????????
                            # st.write(f"Nome da coleção: {nome_colecao}")


                            if colecao is not None:
                                resultado = colecao.delete_one({"_id": ObjectId(documento_escolhido["_id"])})
                                if resultado.deleted_count > 0:
                                    st.success(f"Documento '{titulo_escolhido}' excluído com sucesso!")
                                    time.sleep(2)
                                    st.rerun()
                                else:
                                    st.error("Não foi possível excluir o documento.")
                            else:
                                st.error(f"Coleção '{nome_colecao}' não encontrada no código.")
                        else:
                            st.error("Tipo de documento não mapeado para uma coleção.")


            else:
                st.info("Não há documentos cadastrados para este tipo.")





# #####################################################################################
# PESSOAS
# #####################################################################################


# FUNÇÕES AUXILIARES -----------------------------

# Diálogo para convidar pessoa
@st.dialog("Enviar um convite")
def convidar_pessoa():

    with st.form("Convidar pessoa"):

        nome_completo = st.text_input("Nome completo")
        email_invite = st.text_input("Email")
        permissao = st.selectbox(
            "Tipo de usuário",
            ["Visitante", "Editor", "Administrador"]
        )
        status = "ativo"

        if st.form_submit_button("Enviar convite", type="primary", icon=":material/mail:"):

            pessoas.insert_one({"e_mail": email_invite,
                                "nome_completo": nome_completo,
                                "permissao": permissao,
                                "status": status})
            
            # Enviar o email
            enviar_convite(email_invite)

            st.success("Convite enviado com sucesso!")
            time.sleep(3)
            st.rerun()


# Função para enviar um e_mail com convite
def enviar_convite(destinatario):
    # Dados de autenticação, retirados do arquivo secrets.toml
    remetente = st.secrets["senhas_email"]["endereco_email"]
    senha = st.secrets["senhas_email"]["senha_email"]

    # Conteúdo do e_mail
    assunto = "Convite para a Biblioteca Diálogos do Babaçu"
    corpo = f"""
    <html>
        <body>
            <p style='font-size: 1.5em;'>
                Olá. Você recebeu um convite para acessar a Biblioteca Diálogos do Babaçu.
            </p>

            <p style='font-size: 1.5em;'>
                Acesse o link abaixo:
            </p>

            <p style='font-size: 1.5em;'>
                <strong><a href="https://bibliotecababacu.streamlit.app/">Biblioteca Diálogos do Babaçu</a></strong> e clique em <strong>esqueci a senha</strong>.
            </p>
        </body>
    </html>
    """

    # Cria o e_mail formatado com HTML
    msg = MIMEText(corpo, "html", "utf-8")
    msg["Subject"] = assunto
    msg["From"] = remetente
    msg["To"] = destinatario
    
    # Tenta enviar o e_mail via SMTP seguro (SSL)
    with st.spinner("Enviando e-mail..."):
        try:
            with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
                server.login(remetente, senha)
                server.sendmail(remetente, destinatario, msg.as_string())
            return True
        except Exception as e:
            st.error(f"Erro ao enviar e-mail: {e}")
            return False


# Função para editar pessoa
@st.dialog("Editar pessoa")
def editar_pessoa():

    # Lista de nomes disponíveis
    lista_nomes = sorted(df_pessoas["Nome"].dropna().tolist())
    nome = st.selectbox("Escolha a pessoa", lista_nomes)

    # Tenta achar a pessoa no DataFrame
    pessoa_sel = df_pessoas[df_pessoas["Nome"] == nome]

    if not pessoa_sel.empty:
        # Se achar
        pessoa_sel = pessoa_sel.iloc[0]  # acessa linha encontrada

        # ??????
        # st.write(pessoa_sel)

        # Usa valores do DataFrame se existirem, senão coloca padrão
        nome_atual = pessoa_sel.get("Nome")
        email_atual = pessoa_sel.get("E-mail") or ""
        status_atual = pessoa_sel.get("Status") or ""
        permissao_atual = pessoa_sel.get("Permissão") or ""
    else:
        # Se não achar no DataFrame
        email_atual = ""
        status_atual = "ativo"
        permissao_atual = "Visitante"

    # Formulário com preenchimento automático (ou vazio se não existir)
    with st.form("Editar pessoa"):
        nome = st.text_input("Nome", value=nome_atual)
        email = st.text_input("E-mail", value=email_atual)

        status = st.selectbox(
            "Status",
            ["ativo", "inativo"],
            index=["ativo", "inativo"].index(status_atual) if status_atual in ["ativo", "inativo"] else 0
        )

        permissao = st.selectbox(
            "Permissão",
            ["Visitante", "Editor", "Administrador"],
            index=["Visitante", "Editor", "Administrador"].index(permissao_atual) if permissao_atual in ["Visitante", "Editor", "Administrador"] else 0
        )

        if st.form_submit_button("Salvar", type="primary", icon=":material/save:"):
            pessoas.update_one(
                {"e_mail": email_atual},  # filtro com e-mail original
                {"$set": {
                    "nome_completo": nome,
                    "e_mail": email,
                    "status": status,
                    "permissao": permissao
                }},
                upsert=True
            )
            st.success("Dados atualizados com sucesso!")
            time.sleep(3)
            st.rerun()




        st.write('')

    st.write("**Visitante** consegue consultar a biblioteca e o mapa")
    st.write("**Editor** consegue adicionar, editar e excluir documentos")
    st.write("**Administrador** consegue convidar novas pessoas")


with tab_pessoas:
    st.write('')

    # TELA SOMENTE PARA ADMINISTRADOR
    if st.session_state.permissao == "Administrador":
   
    
        # TRATAMENTO DOS DADOS ###############
        
        # Criar dataframe da coleção pessoas
        df_pessoas = pd.DataFrame(list(pessoas.find()))

        # Renomar as colunas do dataframe
        df_pessoas = df_pessoas.rename(columns={
            "nome_completo": "Nome",
            "e_mail": "E-mail",
            "status": "Status",
            "permissao": "Permissão"
        })

    
        # BOTÕES #############
        with st.container(horizontal=True, horizontal_alignment="left"):
            st.button("Convidar", on_click=convidar_pessoa, icon=":material/person_add:", width=250)
            st.button("Editar", on_click=editar_pessoa, icon=":material/person_edit:", width=250)

        st.write('')


        # Filtra usuários ativos ------------------------------
        st.write("**Pessoas com acesso ao site**")

        df_pessoas_ativas = df_pessoas[
            (df_pessoas["senha"].notna()) & 
            (df_pessoas["Status"] == "ativo")
        ]


        # Mostrar dataframe
        st.dataframe(
            df_pessoas_ativas[["Nome", "E-mail", "Status", "Permissão"]],
            hide_index=True
        )


        # Filtra usuários com convite pendente ------------------------------
        df_pessoas_pendentes = df_pessoas[df_pessoas["senha"].isna()]

        if len(df_pessoas_pendentes) > 0:
            st.write("**Convites pendentes**")

            # Mostrar dataframe
            st.dataframe(df_pessoas_pendentes.drop(columns=["senha", "_id", "Nome", "Status"]), hide_index=True)


        # Filtra usuários com convite pendente ------------------------------
        df_pessoas_inativas = df_pessoas[df_pessoas["Status"] == "inativo"]

        if len(df_pessoas_inativas) > 0:

            st.write("**Inativos(as)**")

            # Mostrar dataframe
            st.dataframe(df_pessoas_inativas.drop(columns=["senha", "_id"]), hide_index=True)


    elif st.session_state.permissao == "Visitante" or st.session_state.permissao == "Editor":
        st.write("Gerenciamento de pessoas disponível apenas para administradores.")