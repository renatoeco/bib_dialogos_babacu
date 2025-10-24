import streamlit as st  
from pymongo import MongoClient  
import time 
import random  
import smtplib  
from email.mime.text import MIMEText  
from funcoes_auxiliares import conectar_mongo_dialogos_babacu  # Função personalizada para conectar ao MongoDB
import bcrypt


##############################################################################################################
# CONEXÃO COM O BANCO DE DADOS (MONGODB)
###############################################################################################################


# Conecta ao banco de dados MongoDB usando função importada (com cache para otimizar desempenho)
db = conectar_mongo_dialogos_babacu()

# Define a coleção a ser utilizada, neste caso chamada "teste"
colaboradores = db["pessoas"]


##############################################################################################################
# FUNÇÕES AUXILIARES
##############################################################################################################


def encontrar_usuario_por_email(colaboradores, email_busca):
    usuario = colaboradores.find_one({"e_mail": email_busca})
    if usuario:
        return usuario.get("nome_completo"), usuario  # Retorna o nome e os dados do usuário
    return None, None  # Caso não encontre



# Função para enviar um e_mail com código de verificação
def enviar_email(destinatario, codigo):
    # Dados de autenticação, retirados do arquivo secrets.toml
    remetente = st.secrets["senhas_email"]["endereco_email"]
    senha = st.secrets["senhas_email"]["senha_email"]

    # Conteúdo do e_mail
    assunto = "Código Para Redefinição de Senha - Biblioteca Diálogos do Babaçu"
    corpo = f"""
    <html>
        <body>
            <p style='font-size: 1.5em;'>
                Seu código para redefinição é: <strong>{codigo}</strong>
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
    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(remetente, senha)
            server.sendmail(remetente, destinatario, msg.as_string())
        return True
    except Exception as e:
        st.error(f"Erro ao enviar e-mail: {e}")
        return False


##############################################################################################################
# CAIXA DE DIÁLOGO PARA RECUPERAÇÃO DE SENHA
##############################################################################################################


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
                    nome, verificar_colaboradores = encontrar_usuario_por_email(colaboradores, email)
                    if verificar_colaboradores:

                        if verificar_colaboradores.get("status", "").lower() != "ativo":
                            st.error("Usuário inativo. Entre em contato com o renato@ispn.org.br.")
                            return
                        
                        codigo = str(random.randint(100, 999))  # Gera um código aleatório
                        if enviar_email(email, codigo):  # Envia o código por e-mail
                            st.session_state.codigo_verificacao = codigo
                            st.session_state.codigo_enviado = True
                            st.session_state.email_verificado = email
                            st.session_state["nome"] = nome
                            
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

                    # Localiza o usuário pelo e_mail
                    usuario = colaboradores.find_one({"e_mail": email})

                    if usuario:
                        try:

                            # Gera hash seguro da senha
                            hash_senha = bcrypt.hashpw(nova_senha.encode("utf-8"), bcrypt.gensalt())

                            # Atualiza no banco o hash, não a senha em texto puro
                            result = colaboradores.update_one(
                                {"e_mail": email},
                                {"$set": {"senha": hash_senha}}
                            )

                            # # Atualiza a senha no banco de dados
                            # result = colaboradores.update_one(
                            #     {"e_mail": email},
                            #     {"$set": {"senha": nova_senha}}
                            # )

                            if result.matched_count > 0:
                                st.success("Senha redefinida com sucesso!")

                                # Limpa as variáveis da sessão
                                for key in ["codigo_enviado", "codigo_verificacao", "email_verificado", "codigo_validado"]:
                                    st.session_state.pop(key, None)

                                # Marca usuário como logado e reinicia o app
                                st.session_state.logged_in = True
                                time.sleep(2)
                                st.rerun()
                            else:
                                st.error("Erro ao redefinir a senha. Tente novamente.")
                        except Exception as e:
                            st.error(f"Erro ao atualizar a senha: {e}")
                    else:
                        st.error("Nenhum usuário encontrado com esse e-mail.")
                else:
                    st.error("As senhas não coincidem ou estão vazias.")



##############################################################################################################
# TELA DE LOGIN
##############################################################################################################




def login():
    # Cria colunas para centralizar o formulário
    col1, col2, col3 = st.columns([2, 3, 2])   

    # Exibe o logo
    col2.image("images/logo dialogos do babacu.png", width=199)

    col2.write('')
    col2.write('')
    col2.write('')
    col2.write('')

    # Exibe o título 
    st.markdown("<div style='text-align: center;'><h1 style='color: #666;'><strong>Biblioteca Diálogos do Babaçu</strong></h1></div>", unsafe_allow_html=True)
    st.write('')
    st.write('')
    st.write('')
    st.write('')

    col1, col2, col3 = st.columns([2, 3, 2])   

    with col2.form("login_form", border=False):
        email_input = st.text_input("Insira seu e-mail")
        password = st.text_input("Insira a senha", type="password")

        st.write('')

        if st.form_submit_button("Entrar"):
            # Busca apenas por e-mail no banco
            usuario_encontrado = colaboradores.find_one({
                "e_mail": {"$regex": f"^{email_input.strip()}$", "$options": "i"}
            })

            st.session_state["email_para_recuperar"] = email_input.strip()

            if usuario_encontrado:
                # Verifica se o usuário está ativo
                if usuario_encontrado.get("status", "").lower() != "ativo":
                    st.error("Usuário inativo. Entre em contato com o renato@ispn.org.br.")
                    return

                # Pegando o hash da senha armazenado no banco
                senha_hash_armazenada = usuario_encontrado.get("senha", "")

                # É importante garantir que está em bytes
                if isinstance(senha_hash_armazenada, str):
                    senha_hash_armazenada = senha_hash_armazenada.encode("utf-8")

                # Verifica a senha digitada com o hash usando bcrypt
                if bcrypt.checkpw(password.encode("utf-8"), senha_hash_armazenada):
                    st.session_state["logged_in"] = True
                    st.session_state["nome"] = usuario_encontrado.get("nome_completo")
                    st.session_state["permissao"] = usuario_encontrado.get("permissao")
                    st.rerun()
                else:
                    st.error("E-mail ou senha inválidos!")
            else:
                st.error("E-mail ou senha inválidos!")

    # Botão para recuperar senha
    col2.write('')
    col2.write('')
    col2.button("Esqueci a senha", key="forgot_password", type="tertiary", on_click=recuperar_senha_dialog)

    # Informação adicional
    col2.markdown("<div style='color: #007ad3;'><br>É o seu primeiro acesso?<br>Clique em \"Esqueci a senha\".</div>", unsafe_allow_html=True)





##############################################################################################################
# EXECUÇÃO PRINCIPAL: VERIFICA LOGIN E NAVEGA ENTRE PÁGINAS
##############################################################################################################


# Se o usuário ainda não estiver logado
if "logged_in" not in st.session_state or not st.session_state["logged_in"]:
    login()  # Mostra tela de login

else:


    # PÁGINAS -----------------------------------------

    # Mostra menu de navegação se estiver logado

# ??????????????????
    # st.sidebar.write(st.session_state)

    # MENU DE VISITANTE
    if st.session_state["permissao"] == "Visitante":

        pg = st.navigation([
            "Biblioteca.py", 
            "Mapa.py",
        ])

        pg_com_icones = st.navigation([
        st.Page("Biblioteca.py", title="Biblioteca", icon=":material/menu_book:"), 
        st.Page("Mapa.py", title="Mapa", icon=":material/map:"),           
        ])

        # Executa a página selecionada
        pg_com_icones.run()

    else:

        pg = st.navigation([
            "Biblioteca.py", 
            "Mapa.py",
            "Gerenciamento.py", 
        
        ])

        pg_com_icones = st.navigation([
        st.Page("Biblioteca.py", title="Biblioteca", icon=":material/menu_book:"), 
        st.Page("Mapa.py", title="Mapa", icon=":material/map:"),           
        st.Page("Gerenciamento.py", title="Gerenciamento", icon=":material/settings:"), 
        ])

        # Executa a página selecionada
        pg_com_icones.run()


