import streamlit as st
from datetime import datetime, UTC
from pymongo import MongoClient
import time
import os
from pydrive2.auth import GoogleAuth
from pydrive2.drive import GoogleDrive
import tempfile
import json
from zoneinfo import ZoneInfo
from pdf2image import convert_from_path
import re

from PIL import Image
# from pydrive.drive import GoogleDrive

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


# --------------------------------------------------------------
# Funções auxiliares
# --------------------------------------------------------------

@st.dialog("Cadastrar Organização")
def cadastrar_organizacao():
    with st.form("Cadastro de Organização"):
        nome_organizacao = st.text_input("Nome da Organização")
        sigla = st.text_input("Sigla da Organização")

        cadastrar = st.form_submit_button(":material/add: Cadastrar")

        if cadastrar:
            # Verificação dos campos obrigatórios
            if not nome_organizacao.strip() or not sigla.strip():
                st.error("Todos os campos são obrigatórios.")
            else:
                organizacoes.insert_one({
                    "nome_organizacao": nome_organizacao.strip(),
                    "email_organizacao": sigla.strip()
                })
                st.success("Organização cadastrada com sucesso!")
                time.sleep(2)
                st.rerun()


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

# Mapeia tipos exibidos para as chaves das pastas no secrets
TIPO_PASTA_MAP = {
    "Publicação": "publicacoes",
    "Imagem": "imagens",
    "Mapa": "mapas",
    "Relatório": "relatorios"
}





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

    # Cria subpasta no Drive
    subfolder = drive.CreateFile({
        'title': folder_name,
        'mimeType': 'application/vnd.google-apps.folder',
        'parents': [{'id': parent_folder_id}]
    })
    subfolder.Upload()
    subfolder_id = subfolder['id']

    # Salva arquivo temporariamente
    with open(filename, "wb") as f:
        f.write(file.getbuffer())

    # Upload do arquivo original
    gfile = drive.CreateFile({'title': filename, 'parents': [{'id': subfolder_id}]})
    gfile.SetContentFile(filename)
    gfile.Upload()
    file_link = f"https://drive.google.com/file/d/{gfile['id']}/view"

    # ------------------------
    # Miniatura (imagem ou PDF)
    # ------------------------
    thumb_link = None
    try:
        thumb_name = f"miniatura_{base_name}.png"
        thumb_path = os.path.join(tempfile.gettempdir(), thumb_name)

        # Se for imagem
        if ext.lower() in ['.png', '.jpg', '.jpeg', '.webp']:
            img = Image.open(filename)
            w, h = img.size
            new_height = int((280 / w) * h)  # mantém proporção
            img = img.resize((280, new_height), Image.Resampling.LANCZOS)
            img.save(thumb_path, "PNG")

        # Se for PDF → pega primeira página
        elif ext.lower() == '.pdf':
            pages = convert_from_path(filename, dpi=150, first_page=1, last_page=1)
            if pages:
                img = pages[0]
                w, h = img.size
                new_height = int((280 / w) * h)  # mantém proporção
                img = img.resize((280, new_height), Image.Resampling.LANCZOS)
                img.save(thumb_path, "PNG")


        # # ✅ Se for imagem
        # if ext.lower() in ['.png', '.jpg', '.jpeg', '.webp']:
        #     img = Image.open(filename)
        #     img.thumbnail((280, 280))
        #     img.save(thumb_path, "PNG")

        # # ✅ Se for PDF → pega primeira página
        # elif ext.lower() == '.pdf':
        #     pages = convert_from_path(filename, dpi=150, first_page=1, last_page=1)
        #     if pages:
        #         img = pages[0]
        #         img.thumbnail((280, 280))
        #         img.save(thumb_path, "PNG")

        # Se gerou thumb, faz upload no Drive
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

    # Remove arquivo local original
    os.remove(filename)

    return file_link, thumb_link
























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

#     # Cria subpasta no Google Drive
#     subfolder = drive.CreateFile({
#         'title': folder_name,
#         'mimeType': 'application/vnd.google-apps.folder',
#         'parents': [{'id': parent_folder_id}]
#     })
#     subfolder.Upload()
#     subfolder_id = subfolder['id']

#     # Salva arquivo original temporariamente
#     with open(filename, "wb") as f:
#         f.write(file.getbuffer())

#     # Upload do arquivo original
#     gfile = drive.CreateFile({
#         'title': filename,
#         'parents': [{'id': subfolder_id}]
#     })
#     gfile.SetContentFile(filename)
#     gfile.Upload()

#     file_link = f"https://drive.google.com/file/d/{gfile['id']}/view"

#     # ----------------------
#     # Tenta gerar miniatura
#     # ----------------------
#     thumb_link = None  # <- Garantido, sempre existe
#     try:
#         img = Image.open(filename)
#         img.thumbnail((280, 280))

#         thumb_name = f"miniatura_{base_name}.png"
#         thumb_path = os.path.join(tempfile.gettempdir(), thumb_name)
#         img.save(thumb_path, format="PNG")

#         thumb_file = drive.CreateFile({
#             'title': thumb_name,
#             'parents': [{'id': subfolder_id}]
#         })
#         thumb_file.SetContentFile(thumb_path)
#         thumb_file.Upload()

#         thumb_link = f"https://drive.google.com/file/d/{thumb_file['id']}/view"

#         os.remove(thumb_path)

#     except Exception as e:
#         st.warning(f"Miniatura não criada (imagem inválida ou outro erro): {e}")

#     # Remove arquivo local original
#     os.remove(filename)

#     return file_link, thumb_link








# def upload_to_drive(file, filename, tipo):
#     # Se for tipo não autorizado a salvar no Drive
#     if tipo not in TIPO_PASTA_MAP:
#         return None

#     tipo_key = TIPO_PASTA_MAP[tipo]
#     parent_folder_id = st.secrets["pastas"].get(tipo_key)

#     if not parent_folder_id:
#         st.error(f"Tipo de mídia permitido, mas pasta não configurada no secrets: {tipo_key}")
#         return None

#     # Autentica no Drive
#     drive = authenticate_drive()

#     # Gera nome da subpasta com timestamp
#     base_name, ext = os.path.splitext(filename)
#     timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
#     folder_name = f"{timestamp}_{base_name}"

#     # Cria nova subpasta no Drive
#     subfolder = drive.CreateFile({
#         'title': folder_name,
#         'mimeType': 'application/vnd.google-apps.folder',
#         'parents': [{'id': parent_folder_id}]
#     })
#     subfolder.Upload()
#     subfolder_id = subfolder['id']

#     # Salva o arquivo original localmente
#     with open(filename, "wb") as f:
#         f.write(file.getbuffer())

#     # Faz upload do arquivo original
#     gfile = drive.CreateFile({
#         'title': filename,
#         'parents': [{'id': subfolder_id}]
#     })
#     gfile.SetContentFile(filename)
#     gfile.Upload()

#     # -------------------------------
#     # SE FOR IMAGEM, GERAR MINIATURA
#     # -------------------------------
#     try:
#         img = Image.open(filename)
#         img.thumbnail((280, 280))   # Mantém proporção até caber em 280x280

#         # Nome da miniatura
#         thumb_name = f"miniatura_{base_name}.png"

#         # Salva miniatura temporária
#         thumb_path = os.path.join(tempfile.gettempdir(), thumb_name)
#         img.save(thumb_path, format="PNG")

#         # Faz upload da miniatura no Drive
#         thumb_file = drive.CreateFile({
#             'title': thumb_name,
#             'parents': [{'id': subfolder_id}]
#         })
#         thumb_file.SetContentFile(thumb_path)
#         thumb_file.Upload()

#         # Remove arquivo temporário da miniatura
#         os.remove(thumb_path)

#     except Exception as e:
#         st.warning(f"Não foi possível gerar miniatura: {e}")

#     # Remove arquivo local original
#     os.remove(filename)

#     # Retorna link público do arquivo original
#     file_id = gfile['id']
#     file_link = f"https://drive.google.com/file/d/{file_id}/view"

#     return file_link


















# def upload_to_drive(file, filename, tipo):
#     # Se for outros tipos que não precisam de armazenamento no Drive
#     if tipo not in TIPO_PASTA_MAP:
#         return None

#     tipo_key = TIPO_PASTA_MAP[tipo]
#     parent_folder_id = st.secrets["pastas"].get(tipo_key)

#     if not parent_folder_id:
#         st.error(f"Tipo de mídia permitido, mas pasta não configurada no secrets: {tipo_key}")
#         return None

#     drive = authenticate_drive()

#     # Gera nome da subpasta com timestamp
#     base_name = os.path.splitext(filename)[0]
#     timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
#     folder_name = f"{timestamp}_{base_name}"

#     # Cria nova subpasta
#     subfolder = drive.CreateFile({
#         'title': folder_name,
#         'mimeType': 'application/vnd.google-apps.folder',
#         'parents': [{'id': parent_folder_id}]
#     })
#     subfolder.Upload()
#     subfolder_id = subfolder['id']

#     # Salva o arquivo temporariamente
#     with open(filename, "wb") as f:
#         f.write(file.getbuffer())

#     # Cria e faz upload do arquivo dentro da subpasta
#     gfile = drive.CreateFile({
#         'title': filename,
#         'parents': [{'id': subfolder_id}]
#     })
#     gfile.SetContentFile(filename)
#     gfile.Upload()


#     # Remove o arquivo local
#     os.remove(filename)

#     # Retorna o link público do Google Drive
#     file_id = gfile['id']
#     file_link = f"https://drive.google.com/file/d/{file_id}/view"

#     return file_link








# --------------------------------------------------------------
# Transformação dos dados
# --------------------------------------------------------------


# Tipos de midia
TIPOS_MIDIA = [
    "Publicação",
    "Imagem",
    "Relatorio",
    "Vídeo",
    "Podcast",
    "Site",
    "Mapa",
    "Legislacao",
    "Ponto de interesse"
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

    # 1. Cadastro de publicação ---------------------------------------------------------------------------
    def enviar_publicacao():

        # ----- PREPARAÇÃO DO DROPDOWN DE TEMAS -----

        # Ordena alfabeticamente os temas do babacu (exceto "Outro", que fica no final)
        temas_ordenados = sorted([t for t in TEMAS_BABACU])
        temas_ordenados.append("Outro")

        # Adiciona uma opção vazia no início
        temas_ordenados = [""] + temas_ordenados

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
        organizacoes_disponiveis = sorted([doc.get("nome_organizacao") for doc in organizacoes.find()])

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

            else:
                try:
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
                            "data_upload": datetime.now(ZoneInfo("America/Sao_Paulo"))
                        }

                        # Insere o documento na coleção `publicacoes`
                        publicacoes.insert_one(data)

                        # Mostra mensagem de sucesso
                        st.success("Documento cadastrado com sucesso!")

                except Exception as e:
                    # Mensagem de erro em caso de falha no processo
                    st.error(f"Erro no upload: {e}")


    # 2. Cadastro de imagem ---------------------------------------------------------------------------
    def enviar_imagem():

        # ----- PREPARAÇÃO DO DROPDOWN DE TEMAS -----

        # Ordena alfabeticamente os temas do babacu (exceto "Outro", que fica no final)
        temas_ordenados = sorted([t for t in TEMAS_BABACU])
        temas_ordenados.append("Outro")

        # Adiciona uma opção vazia no início
        temas_ordenados = [""] + temas_ordenados

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
        organizacoes_disponiveis = sorted([doc.get("nome_organizacao") for doc in organizacoes.find()])

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
                            "data_upload": datetime.now(ZoneInfo("America/Sao_Paulo"))
                        }

                        # Insere o documento na coleção `publicacoes`
                        imagens.insert_one(data)

                        # Mostra mensagem de sucesso
                        st.success("Documento enviado com sucesso!")

                except Exception as e:
                    # Mensagem de erro em caso de falha no processo
                    st.error(f"Erro no upload: {e}")


    # 3. Cadastro de relatório ---------------------------------------------------------------------------
    def enviar_relatorio(): 

        # ----- PREPARAÇÃO DO DROPDOWN DE TEMAS -----

        # Ordena alfabeticamente os temas do babacu (exceto "Outro", que fica no final)
        temas_ordenados = sorted([t for t in TEMAS_BABACU])
        temas_ordenados.append("Outro")

        # Adiciona uma opção vazia no início
        temas_ordenados = [""] + temas_ordenados

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
        organizacoes_disponiveis = sorted([doc.get("nome_organizacao") for doc in organizacoes.find()])

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
                            "data_upload": datetime.now(ZoneInfo("America/Sao_Paulo"))
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

        # ----- PREPARAÇÃO DO DROPDOWN DE TEMAS -----

        # Ordena alfabeticamente os temas do babacu (exceto "Outro", que fica no final)
        temas_ordenados = sorted([t for t in TEMAS_BABACU])
        temas_ordenados.append("Outro")

        # Adiciona uma opção vazia no início
        temas_ordenados = [""] + temas_ordenados

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
        organizacoes_disponiveis = sorted([doc.get("nome_organizacao") for doc in organizacoes.find()])

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
                            "data_upload": datetime.now(ZoneInfo("America/Sao_Paulo"))
                        }

                        # Insere o documento na coleção
                        videos.insert_one(data)   #!!!!

                        # Mostra mensagem de sucesso
                        st.success("Documento enviado com sucesso!")

                except Exception as e:
                    # Mensagem de erro em caso de falha no processo
                    st.error(f"Erro no upload: {e}")


    # 5. Cadastro de podcast ---------------------------------------------------------------------------
    def enviar_podcast(): #!!!!

        # ----- PREPARAÇÃO DO DROPDOWN DE TEMAS -----

        # Ordena alfabeticamente os temas do babacu (exceto "Outro", que fica no final)
        temas_ordenados = sorted([t for t in TEMAS_BABACU])
        temas_ordenados.append("Outro")

        # Adiciona uma opção vazia no início
        temas_ordenados = [""] + temas_ordenados

        # Título da seção
        st.write('')
        st.subheader("Cadastrar podcast")    #!!!!

        # ----- CAMPOS DO FORMULÁRIO -----

        tipo_doc = "Podcast" #!!!!

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
        organizacoes_disponiveis = sorted([doc.get("nome_organizacao") for doc in organizacoes.find()])

        # Multiselect com opção de cadastrar nova organização
        organizacao = st.multiselect(
            "Organização responsável",
            ["+ Cadastrar nova organização", "Nenhuma organização"] + organizacoes_disponiveis)

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

            # Validação: todos os campos obrigatórios devem estar preenchidos
            if not titulo or not descricao or not anos or not tema or not autor or not organizacao or not link_podcast: #!!!!
                st.error("Todos os campos são obrigatórios.")

            else:
                try:
                    with st.spinner('Enviando documento...'):

                        # # Monta o nome do arquivo com a extensão original
                        # extensao = os.path.splitext(arquivo.name)[1]
                        # titulo_com_extensao = f"{titulo.strip()}{extensao}"

                        # # Envia o arquivo ao Google Drive e retorna o ID do arquivo
                        # file_id = upload_to_drive(arquivo, titulo_com_extensao, tipo_doc)

                        # Prepara o dicionário com os dados para salvar no MongoDB
                        data = {     #!!!!
                            "titulo": titulo,
                            "descricao": descricao,
                            "ano_publicacao": ano_publicacao,
                            "tema": tema,
                            "autor": autor,
                            "organizacao": organizacao,
                            "tipo": tipo_doc,
                            "link": link_podcast,
                            "enviado_por": st.session_state["nome"],
                            "data_upload": datetime.now(ZoneInfo("America/Sao_Paulo"))
                        }

                        # Insere o documento na coleção
                        podcasts.insert_one(data)   #!!!!

                        # Mostra mensagem de sucesso
                        st.success("Documento enviado com sucesso!")

                except Exception as e:
                    # Mensagem de erro em caso de falha no processo
                    st.error(f"Erro no upload: {e}")


    # 6. Cadastro de site ---------------------------------------------------------------------------
    def enviar_site(): #!!!!

        # ----- PREPARAÇÃO DO DROPDOWN DE TEMAS -----

        # Ordena alfabeticamente os temas do babacu (exceto "Outro", que fica no final)
        temas_ordenados = sorted([t for t in TEMAS_BABACU])
        temas_ordenados.append("Outro")

        # Adiciona uma opção vazia no início
        temas_ordenados = [""] + temas_ordenados

        # Título da seção
        st.write('')
        st.subheader("Cadastrar site")    #!!!!

        # ----- CAMPOS DO FORMULÁRIO -----

        tipo_doc = "Site" #!!!!

        # Campo de texto: título
        titulo = st.text_input("Título")

        # Campo de texto longo: descrição
        descricao = st.text_area("Descrição")

        # # Dropdown: ano (de hoje até 1950)
        # anos = list(range(datetime.now().year, 1949, -1))
        # ano_publicacao = st.selectbox("Ano de publicação", anos)

        # Campo multiselect para temas
        tema = st.multiselect("Tema", temas_ordenados)

        # Campo de texto: autor(es)
        autor = st.text_input("Autor(es) / Autora(s)")

        # Pega as organizações cadastradas no MongoDB
        organizacoes_disponiveis = sorted([doc.get("nome_organizacao") for doc in organizacoes.find()])

        # Multiselect com opção de cadastrar nova organização
        organizacao = st.multiselect(
            "Organização responsável",
            ["+ Cadastrar nova organização", "Nenhuma organização"] + organizacoes_disponiveis)

        # Campo de texto: título
        link_site = st.text_input("Link do site")   #!!!!

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
            if not titulo or not descricao or not tema or not autor or not organizacao or not link_site: #!!!!
                st.error("Todos os campos são obrigatórios.")

            else:
                try:
                    with st.spinner('Enviando documento...'):

                        # # Monta o nome do arquivo com a extensão original
                        # extensao = os.path.splitext(arquivo.name)[1]
                        # titulo_com_extensao = f"{titulo.strip()}{extensao}"

                        # # Envia o arquivo ao Google Drive e retorna o ID do arquivo
                        # file_id = upload_to_drive(arquivo, titulo_com_extensao, tipo_doc)

                        # Prepara o dicionário com os dados para salvar no MongoDB
                        data = {     #!!!!
                            "titulo": titulo,
                            "descricao": descricao,
                            # "ano_publicacao": ano_publicacao,
                            "tema": tema,
                            "autor": autor,
                            "organizacao": organizacao,
                            "tipo": tipo_doc,
                            "link": link_site,
                            "enviado_por": st.session_state["nome"],
                            "data_upload": datetime.now(ZoneInfo("America/Sao_Paulo"))
                        }

                        # Insere o documento na coleção
                        sites.insert_one(data)   #!!!!

                        # Mostra mensagem de sucesso
                        st.success("Documento enviado com sucesso!")

                except Exception as e:
                    # Mensagem de erro em caso de falha no processo
                    st.error(f"Erro no upload: {e}")


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
        organizacoes_disponiveis = sorted([doc.get("nome_organizacao") for doc in organizacoes.find()])

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
                            "data_upload": datetime.now(ZoneInfo("America/Sao_Paulo"))
                        }

                        # Insere o documento na coleção
                        mapas.insert_one(data)   #!!!!

                        # Mostra mensagem de sucesso
                        st.success("Documento enviado com sucesso!")

                except Exception as e:
                    # Mensagem de erro em caso de falha no processo
                    st.error(f"Erro no upload: {e}")


    # 8. Cadastro de legislacao ---------------------------------------------------------------------------
    def enviar_legislacao(): #!!!!

        # ----- PREPARAÇÃO DO DROPDOWN DE TEMAS -----

        # Ordena alfabeticamente os temas do babacu (exceto "Outro", que fica no final)
        temas_ordenados = sorted([t for t in TEMAS_BABACU])
        temas_ordenados.append("Outro")

        # Adiciona uma opção vazia no início
        temas_ordenados = [""] + temas_ordenados

        # Título da seção
        st.write('')
        st.subheader("Cadastrar legislação")    #!!!!

        # ----- CAMPOS DO FORMULÁRIO -----

        tipo_doc = "Legislação" #!!!!

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


        # # Pega as organizações cadastradas no MongoDB
        # organizacoes_disponiveis = sorted([doc.get("nome_organizacao") for doc in organizacoes.find()])

        # # Multiselect com opção de cadastrar nova organização
        # organizacao = st.multiselect(
        #     "Organização responsável",
        #     ["+ Cadastrar nova organização", "Nenhuma organização"] + organizacoes_disponiveis)

        # Campo de texto: título
        link_legislacao = st.text_input("Link da legislação")

        # # Se o usuário escolheu cadastrar nova organização
        # if "+ Cadastrar nova organização" in organizacao:
        #     cadastrar_organizacao()


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

                        # # Monta o nome do arquivo com a extensão original
                        # extensao = os.path.splitext(arquivo.name)[1]
                        # titulo_com_extensao = f"{titulo.strip()}{extensao}"

                        # # Envia o arquivo ao Google Drive e retorna o ID do arquivo
                        # file_id = upload_to_drive(arquivo, titulo_com_extensao, tipo_doc)

                        # Prepara o dicionário com os dados para salvar no MongoDB
                        data = {     #!!!!
                            "titulo": titulo,
                            "descricao": descricao,
                            "ano_publicacao": ano_publicacao,
                            "tema": tema,
                            "autor": autor,
                            "casa_legislativa": casa_legislativa,
                            "tipo": tipo_doc,
                            "link": link_legislacao,
                            "enviado_por": st.session_state["nome"],
                            "data_upload": datetime.now(ZoneInfo("America/Sao_Paulo"))
                        }

                        # Insere o documento na coleção
                        legislacao.insert_one(data)   #!!!!

                        # Mostra mensagem de sucesso
                        st.success("Documento enviado com sucesso!")

                except Exception as e:
                    # Mensagem de erro em caso de falha no processo
                    st.error(f"Erro no upload: {e}")



    # 9. Cadastro de ponto de interesse ---------------------------------------------------------------------------
    def enviar_ponto(): #!!!!

        # ----- PREPARAÇÃO DO DROPDOWN DE TEMAS -----

        # Ordena alfabeticamente os temas do babacu (exceto "Outro", que fica no final)
        temas_ordenados = sorted([t for t in TEMAS_BABACU])
        temas_ordenados.append("Outro")

        # Adiciona uma opção vazia no início
        temas_ordenados = [""] + temas_ordenados

        # Título da seção
        st.write('')
        st.subheader("Cadastrar ponto de interesse")    #!!!!

        # ----- CAMPOS DO FORMULÁRIO -----

        tipo_doc = "Ponto de interesse" #!!!!

        # Campo de texto: título
        titulo = st.text_input("Título")

        # Campo de texto longo: descrição
        descricao = st.text_area("Descrição")

        # # Dropdown: ano (de hoje até 1950)
        # anos = list(range(datetime.now().year, 1949, -1))
        # ano_publicacao = st.selectbox("Ano de publicação", anos)

        # Campo multiselect para temas
        tema = st.multiselect("Tema", temas_ordenados)

        # # Campo de texto: autor(es)
        # autor = st.text_input("Autor(es) / Autora(s)")

        # # Campo de texto: casa legislativa
        # casa_legislativa = st.text_input("Casa legislativa")


        # Pega as organizações cadastradas no MongoDB
        organizacoes_disponiveis = sorted([doc.get("nome_organizacao") for doc in organizacoes.find()])

        # Multiselect com opção de cadastrar nova organização
        organizacao = st.multiselect(
            "O ponto está relacionado à atuação de alguma organização?",
            ["+ Cadastrar nova organização", "Nenhuma organização"] + organizacoes_disponiveis)

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
            if not titulo or not descricao or not tema or not organizacao or not link_google_maps: #!!!!
                st.error("Todos os campos são obrigatórios.")

            else:
                try:
                    with st.spinner('Enviando documento...'):

                        # # Monta o nome do arquivo com a extensão original
                        # extensao = os.path.splitext(arquivo.name)[1]
                        # titulo_com_extensao = f"{titulo.strip()}{extensao}"

                        # # Envia o arquivo ao Google Drive e retorna o ID do arquivo
                        # file_id = upload_to_drive(arquivo, titulo_com_extensao, tipo_doc)

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



                        # Prepara o dicionário com os dados para salvar no MongoDB
                        data = {     #!!!!
                            "titulo": titulo,
                            "descricao": descricao,
                            # "ano_publicacao": ano_publicacao,
                            "tema": tema,
                            "latitude": latitude,
                            "longitude": longitude,
                            "tipo": tipo_doc,
                            "link": link_google_maps,
                            "enviado_por": st.session_state["nome"],
                            "data_upload": datetime.now(ZoneInfo("America/Sao_Paulo"))
                        }

                        # Insere o documento na coleção
                        pontos.insert_one(data)   #!!!!

                        # Mostra mensagem de sucesso
                        st.success("Documento enviado com sucesso!")

                except Exception as e:
                    # Mensagem de erro em caso de falha no processo
                    st.error(f"Erro no upload: {e}")




    if acao == "Cadastrar documento":
        # Escolha do tipo de mídia


        # 1. Dicionário: valor real -> rótulo com ícone
        TIPOS_MIDIA = {
            "Publicação": ":material/menu_book: Publicação",
            "Imagem": ":material/add_a_photo: Imagem",
            "Relatório": ":material/assignment: Relatório",
            "Vídeo": ":material/videocam: Vídeo",
            "Podcast": ":material/podcasts: Podcast",
            "Site": ":material/language: Site",
            "Mapa": ":material/map: Mapa",
            "Legislação": ":material/balance: Legislação",
            "Ponto de interesse": ":material/location_on: Ponto de interesse"
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






        # midia_selecionada = st.pills(label="Qual tipo de Mídia", options=["Publicação", "Imagem", "Relatório", "Vídeo", "Podcast", "Site", "Mapa", "Legislação", "Ponto de interesse"])
    

        if midia_selecionada == "Publicação":
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


    elif acao == "Editar um documento":
        st.write('')
        st.write('')
        st.write("Em construção")

    elif acao == "Excluir um documento":
        st.write('')
        st.write('')
        st.write("Em construção")

# PESSOAS
with tab_pessoas:
    st.write("Em construção")