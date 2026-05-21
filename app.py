import streamlit as st
import pandas as pd
from openai import OpenAI
import requests
from bs4 import BeautifulSoup
import json
import os
from datetime import datetime

# 1. Configuração da Página
st.set_page_config(page_title="Salesforce Admin Exam Prep", page_icon="🛡️", layout="wide")

# 2. Autenticação (Acessando os Secrets do Streamlit de forma segura)
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])


# --- BANCO DE LINKS OFICIAIS ---
LINKS_CERTIFICACAO = {
    "Configuração e Objetos (20%)": "https://help.salesforce.com/s/articleView?id=sf.dev_object_overview.htm&type=5",
    "Segurança e Acesso (14%)": "https://help.salesforce.com/s/articleView?id=sf.security_overview.htm&type=5",
    "Automação de Processos/Flow (16%)": "https://help.salesforce.com/s/articleView?id=sf.flow.htm&type=5",
    "Relatórios e Dashboards (10%)": "https://help.salesforce.com/s/articleView?id=sf.reports_overview.htm&type=5",
    "Guia Geral do Administrador": "https://help.salesforce.com/s/articleView?id=sf.admin_setup_guide.htm&type=5",
    "Personalizado (Usar link do campo abaixo)": "Personalizado"
}

# --- FUNÇÕES DE APOIO ---
def carregar_dados():
    arquivo = 'historico_simulados.csv'
    if os.path.exists(arquivo):
        return pd.read_csv(arquivo)
    return pd.DataFrame(columns=['Data', 'Tema', 'Dificuldade', 'Acertos', 'Total', 'Score %'])

def salvar_no_historico(tema, dificuldade, pontos, total):
    arquivo = 'historico_simulados.csv'
    data_atual = datetime.now().strftime("%d/%m/%Y %H:%M")
    score = int((pontos / total) * 100)
    # CORREÇÃO AQUI: Mudado de difficulty para dificuldade para sumir o erro vermelho
    novo_registro = pd.DataFrame([[data_atual, tema, dificuldade, pontos, total, f"{score}%"]], 
                                columns=['Data', 'Tema', 'Dificuldade', 'Acertos', 'Total', 'Score %'])
    df_atual = carregar_dados()
    df_final = pd.concat([df_atual, novo_registro], ignore_index=True)
    df_final.to_csv(arquivo, index=False)

def extrair_texto_url(url):
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
        for script in soup(["script", "style"]):
            script.extract()
        texto = soup.get_text(separator=' ')
        return " ".join(texto.split())
        return " ".join(texto.split())[:5000] # Limite para não estourar tokens
    except Exception as e:
        st.error(f"Erro ao acessar a documentação: {e}")
        return None
