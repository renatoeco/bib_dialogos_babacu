import streamlit as st
from pymongo import MongoClient
from pydrive2.auth import GoogleAuth
from pydrive2.drive import GoogleDrive
from datetime import datetime, UTC
import tempfile
import json
from funcoes_auxiliares import conectar_mongo_dialogos_babacu, barra_de_logos  
import re
import bcrypt
import time
import random
import smtplib
from email.mime.text import MIMEText


# --------------------------------------------------------------
# Configurações do MongoDB
# --------------------------------------------------------------

db = conectar_mongo_dialogos_babacu()

# client = MongoClient(st.secrets.mongo.string_conexao_mongo)
# db = client[st.secrets.mongo.bd_dialogos]

# Carragando cada coleção
publicacoes = db["publicacoes"]
imagens = db["imagens"]
videos = db["videos"]
podcasts = db["podcasts"]
sites = db["sites"]
mapas = db["mapas"]
legislacao = db["legislacao"]
pontos_interesse = db["pontos_interesse"]
relatorios = db["relatorios"]
pessoas = db["pessoas"]
organizacoes = db["organizacoes"]
projetos = db["projetos"]
pesquisas = db["pesquisas"]
colaboradores = db["pessoas"]

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



def encontrar_usuario_por_email(email_busca):
    usuario = colaboradores.find_one({"e_mail": email_busca})

    if usuario:
        return usuario.get("nome_completo"), usuario

    return None, None


def enviar_email(destinatario, codigo):

    remetente = st.secrets["senhas_email"]["endereco_email"]
    senha = st.secrets["senhas_email"]["senha_email"]

    assunto = "Código Para Redefinição de Senha - Biblioteca Diálogos do Babaçu"

    corpo = f"""
    <html>
        <body>
            <p style='font-size: 1.5em;'>
                Seu código para redefinição é:
                <strong>{codigo}</strong>
            </p>
        </body>
    </html>
    """

    msg = MIMEText(corpo, "html", "utf-8")

    msg["Subject"] = assunto
    msg["From"] = remetente
    msg["To"] = destinatario

    try:

        with smtplib.SMTP_SSL(
            "smtp.gmail.com",
            465
        ) as server:

            server.login(remetente, senha)

            server.sendmail(
                remetente,
                destinatario,
                msg.as_string()
            )

        return True

    except Exception as e:

        st.error(f"Erro ao enviar e-mail: {e}")

        return False

@st.dialog("Recuperação de Senha")
def recuperar_senha_dialog():
    st.session_state.setdefault("codigo_enviado", False)
    st.session_state.setdefault("codigo_verificacao", "")
    st.session_state.setdefault("email_verificado", "")
    st.session_state.setdefault("codigo_validado", False)

    conteudo_dialogo = st.empty()

    # Etapa 1: Entrada do e-mail
    if not st.session_state.codigo_enviado:
        with conteudo_dialogo.form(key="recover_password_form", border=False):
            # Preenche automaticamente com email da sessão (se houver)
            email_default = st.session_state.get("email_para_recuperar", "")
            email = st.text_input("Digite seu e-mail:", value=email_default)

            if st.form_submit_button("Enviar código de verificação"):
                if email:
                    nome, verificar_colaboradores = encontrar_usuario_por_email(email)
                    if verificar_colaboradores:

                        if verificar_colaboradores.get("status", "").lower() != "ativo":
                            st.error("Usuário inativo. Entre em contato com o renato@ispn.org.br.")
                            return
                        
                        codigo = str(random.randint(100, 999))  # Gera um código aleatório
                        with st.spinner("Enviando código de verificação..."):
                            if enviar_email(email, codigo):  # Envia o código por e-mail
                                st.session_state.codigo_verificacao = codigo
                                st.session_state.codigo_enviado = True
                                st.session_state.email_verificado = email
                                st.session_state["nome"] = nome
                                st.session_state["permissao"] = verificar_colaboradores["permissao"]
                                
                                st.success(f"Código enviado para {email}.")
                            else:
                                st.error("Erro ao enviar o e-mail. Tente novamente.")
                    else:
                        st.error("E-mail não encontrado. Tente novamente.")
                else:
                    st.error("Por favor, insira um e-mail.")

    # --- Etapa 2: Verificação do código recebido ---
    if st.session_state.codigo_enviado and not st.session_state.codigo_validado:
        with conteudo_dialogo.form(key="codigo_verificacao_form", border=False):
            st.subheader("Código de verificação")
            email_mask = st.session_state.email_verificado.replace("@", "​@")  # Máscara leve no e-mail
            st.info(f"Um código foi enviado para: **{email_mask}**")

            codigo_input = st.text_input("Informe o código recebido por e-mail", placeholder="000")
            if st.form_submit_button("Verificar"):
                if codigo_input == st.session_state.codigo_verificacao:
                    sucesso = st.success("Código verificado com sucesso!")
                    time.sleep(2)
                    sucesso.empty()
                    st.session_state.codigo_validado = True
                else:
                    st.error("Código inválido. Tente novamente.")

    # --- Etapa 3: Definição da nova senha ---

    if st.session_state.codigo_validado:
        with conteudo_dialogo.form("nova_senha_form", border=True):
            st.markdown("### Defina sua nova senha")
            nova_senha = st.text_input("Nova senha", type="password")
            confirmar_senha = st.text_input("Confirme a senha", type="password")
            enviar_nova_senha = st.form_submit_button("Salvar")

            if enviar_nova_senha:
                if nova_senha == confirmar_senha and nova_senha.strip():
                    email = st.session_state.email_verificado

                    usuario = colaboradores.find_one({"e_mail": email})

                    if usuario:
                        try:

                            hash_senha = bcrypt.hashpw(
                                nova_senha.encode("utf-8"),
                                bcrypt.gensalt()
                            )

                            result = colaboradores.update_one(
                                {"e_mail": email},
                                {"$set": {"senha": hash_senha}}
                            )

                            if result.matched_count > 0:

                                st.success("Senha redefinida com sucesso!")

                                for key in [
                                    "codigo_enviado",
                                    "codigo_verificacao",
                                    "email_verificado",
                                    "codigo_validado"
                                ]:
                                    st.session_state.pop(key, None)

                                st.session_state.logged_in = True

                                time.sleep(2)

                                st.rerun()

                            else:
                                st.error(
                                    "Erro ao redefinir a senha. Tente novamente."
                                )

                        except Exception as e:
                            st.error(f"Erro ao atualizar a senha: {e}")

                    else:
                        st.error(
                            "Nenhum usuário encontrado com esse e-mail."
                        )

                else:
                    st.error(
                        "As senhas não coincidem ou estão vazias."
                    )
 
                
def login_sidebar():

    with st.expander("Área administrativa", expanded=False):

        with st.form("login_sidebar_form", border=False):

            email_input = st.text_input("E-mail")

            password = st.text_input(
                "Senha",
                type="password"
            )

            entrar = st.form_submit_button("Entrar")

            if entrar:

                usuario_encontrado = colaboradores.find_one(
                    {
                        "e_mail": {
                            "$regex": f"^{email_input.strip()}$",
                            "$options": "i"
                        }
                    }
                )

                st.session_state[
                    "email_para_recuperar"
                ] = email_input.strip()

                if not usuario_encontrado:
                    st.error("E-mail ou senha inválidos.")
                    return

                if (
                    usuario_encontrado
                    .get("status", "")
                    .lower()
                    != "ativo"
                ):
                    st.error(
                        "Usuário inativo. "
                        "Entre em contato com "
                        "renato@ispn.org.br."
                    )
                    return

                senha_hash = usuario_encontrado.get(
                    "senha",
                    ""
                )

                if isinstance(senha_hash, str):
                    senha_hash = senha_hash.encode("utf-8")

                if bcrypt.checkpw(
                    password.encode("utf-8"),
                    senha_hash
                ):

                    st.session_state["logged_in"] = True

                    st.session_state["nome"] = (
                        usuario_encontrado.get(
                            "nome_completo"
                        )
                    )

                    st.session_state["permissao"] = (
                        usuario_encontrado.get(
                            "permissao"
                        )
                    )
                    
                    st.success("Login efetuado com sucesso", icon=":material/check:")
                    time.sleep(2)
                    st.rerun()

                else:

                    st.error(
                        "E-mail ou senha inválidos."
                    )

        st.button(
            "Esqueci a senha",
            key="forgot_password_sidebar",
            type="tertiary",
            on_click=recuperar_senha_dialog
        )

        st.caption(
            'Primeiro acesso? Clique em "Esqueci a senha".'
        )
        
                        
# --------------------------------------------------------------
# INTERFACE
# --------------------------------------------------------------

st.set_page_config(page_title="Biblioteca Diálogos do Babaçu", layout="wide")


st.logo("images/logo dialogos do babacu.png", size="large")
st.header("Biblioteca Diálogos do Babaçu")
st.write('')

if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False

if "permissao" not in st.session_state:
    st.session_state["permissao"] = ""

with st.sidebar:

    if not st.session_state["logged_in"]:
        login_sidebar()

    else:
        st.caption(
            f"Logado como: {st.session_state.get('nome', '')}"
        )
        

# --------------------------------------------------------------
# Listagem dos arquivos


# FILTROS



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
    "Organização": ":material/things_to_do: Organização",
    "Projeto": ":material/assignment: Projeto",
    "Pesquisa": ":material/query_stats: Pesquisa"
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
    "Organização": "things_to_do",
    "Projeto": "assignment",
    "Pesquisa": "query_stats"
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
        temas_pontos = pontos_interesse.distinct("tema")
        temas_relatorios = relatorios.distinct("tema")
        temas_organizacoes = organizacoes.distinct("tema")
        temas_projetos = projetos.distinct("tema")
        temas_pesquisas = pesquisas.distinct("tema")

        todos_os_temas = set(
            temas_publicacoes + temas_imagens + temas_videos + temas_podcasts +
            temas_sites + temas_mapas + temas_legislacao + temas_pontos + temas_relatorios + 
            temas_organizacoes + temas_projetos + temas_pesquisas
        )
        temas_disponiveis = sorted(todos_os_temas)

        temas_selecionados = st.pills(
            label="Tema",
            options=temas_disponiveis,
            selection_mode="multi"
        )

        col1, col2, col3 = st.columns([6, 4, 2])
        busca_texto = col1.text_input("Buscar palavra chave")

        # col3.write('')
        # col3.write('')

        filtrar = st.form_submit_button("Filtrar", icon=":material/filter_list:", type="primary", width=200)



# ------------------ 2. CONSULTA INICIAL (sem filtros = mostra tudo) ------------------ #
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
    for doc in docs_pontos: doc["_colecao"] = "pontos_de_interesse"
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
    
    # ------------------ PAGINAÇÃO ------------------ #

    ITENS_POR_PAGINA = 25

    # Inicializa página no session_state
    if "pagina_atual" not in st.session_state:
        st.session_state.pagina_atual = 1

    total_itens = len(arquivos)
    total_paginas = max(1, (total_itens + ITENS_POR_PAGINA - 1) // ITENS_POR_PAGINA)

    # Sidebar - controle de página
    with st.sidebar:

        pagina = st.number_input(
            "Página",
            min_value=1,
            max_value=total_paginas,
            step=1,
            width=130,
        )

        st.session_state.pagina_atual = pagina

        st.caption(f"Total de páginas: {total_paginas}")
        
    inicio = (st.session_state.pagina_atual - 1) * ITENS_POR_PAGINA
    fim = inicio + ITENS_POR_PAGINA

    arquivos_paginados = arquivos[inicio:fim]


    for item in arquivos:  # Para cada dicionário (item) dentro da lista 'arquivos'
        if isinstance(item.get("tema"), list):  # Verifica se o valor da chave "tema" é uma lista
            item["tema"] = ", ".join(item["tema"])  # Concatena os elementos da lista em uma string separada por vírgulas
        if isinstance(item.get("organizacao"), list):  # Verifica se o valor da chave "organizacao" é uma lista
            item["organizacao"] = ", ".join(item["organizacao"])  # Concatena os elementos da lista em uma string separada por vírgulas


    # Contagem de documentos
    st.subheader(f"{len(arquivos)} documento" if len(arquivos) == 1 else f"{len(arquivos)} documentos")
    
    st.write("")
    
    # Índices da paginação atual
    inicio_contagem = inicio + 1 if total_itens > 0 else 0
    fim_contagem = min(fim, total_itens)

    texto_contagem = f"Listando de {inicio_contagem} a {fim_contagem} documentos"
    st.markdown(
        f"""
        <p style="
            color: #4F4F4F;
            font-size: 0.95rem;
            margin-top: -10px;
            margin-bottom: 10px;
        ">
            {texto_contagem}
        </p>
        """,
        unsafe_allow_html=True
    )
    st.write("")

    # Container horizontal para os cards
    with st.container(border=False, horizontal=True, width='stretch'):
        for arq in arquivos_paginados:


            with st.container(border=True, width=280, height=500, key=arq.get("_id", None)):

                # ??????????????????????
                # st.write(arq)

                tipo = arq.get("tipo", "Tipo não informado")
                icon = TIPOS_MIDIA_ICONE.get(tipo, "")
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

                # Renderiza icone assignment
                if tipo == "Projeto":
                    st.markdown("""
                        <link href="https://fonts.googleapis.com/icon?family=Material+Icons" rel="stylesheet">
                        <div style="text-align:center; margin: 40px 0;">
                            <span class="material-icons" style="font-size: 100px; color: #777;">
                                assignment
                            </span>
                        </div>
                        """, unsafe_allow_html=True)

                # Renderiza icone assignment
                if tipo == "Pesquisa":
                    st.markdown("""
                        <link href="https://fonts.googleapis.com/icon?family=Material+Icons" rel="stylesheet">
                        <div style="text-align:center; margin: 40px 0;">
                            <span class="material-icons" style="font-size: 100px; color: #777;">
                                query_stats
                            </span>
                        </div>
                        """, unsafe_allow_html=True)

                if tipo == "Organização":

                    # Renderiza logotipo
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

                    # ?????????????????????/
                    # st.write(thumb_link)
                
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
                sigla_container = st.container()
                st.write(descricao)
                autor_container = st.container()
                
                if organizacao and organizacao.strip():
                    st.write(f"**Organização:** {organizacao}")
                
                if tema and tema.strip():
                    st.write(f"**Tema:** {tema}")
                
                # Se for organização ou projeto, não tem autor
                if tipo != "Organização" and tipo != "Projeto":
                    autor_container.write(f"**Autor:** {autor}")

                if tipo == "Organização":
                    # Mostra a sigla
                    sigla = arq.get("sigla", None)
                    sigla_container.write(f"**Sigla:** {sigla}")
                    
                    # -------------------------------
                    # Websites (string separada por vírgula)
                    # -------------------------------
                    websites = arq.get("websites", None)

                    if websites:
                        st.write("**Websites:**")

                        # Caso venha como string (seu caso atual)
                        if isinstance(websites, str):

                            # Divide pelos separadores de vírgula
                            lista_sites = websites.split(",")

                            for site in lista_sites:
                                # Remove espaços extras antes/depois
                                site = site.strip()

                                if site:
                                    # Garante que tem http/https
                                    url = site if site.startswith("http") else f"https://{site}"

                                    # Mostra um por linha como link clicável
                                    st.markdown(f"[{url}]({url})")

                        # Caso futuramente vire lista (já deixa preparado)
                        elif isinstance(websites, list):
                            for site in websites:
                                if site:
                                    site = site.strip()
                                    url = site if site.startswith("http") else f"https://{site}"
                                    st.markdown(f"[{url}]({url})")

                    else:
                        st.write("**Websites:** N/A")

                    # Link para a pasta com vários arquivos
                    subfolder_id = arq.get("subfolder_id", "")
                    link = f"https://drive.google.com/drive/folders/{subfolder_id}"

                if tipo == "Pesquisa":

                    # Link para a pasta com vários arquivos
                    subfolder_id = arq.get("subfolder_id", "")
                    link = f"https://drive.google.com/drive/folders/{subfolder_id}"
                    st.link_button("Ver detalhes", url=link, type="primary")


                else:
                    st.link_button("Ver detalhes", url=link, type="primary")





else:
    st.info("Nenhum arquivo encontrado para os filtros aplicados.")




# Barra de logos
barra_de_logos()


