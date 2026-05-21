import streamlit as st
import pandas as pd
from openai import OpenAI
import requests
from bs4 import BeautifulSoup
import json
import os
from datetime import datetime
import zoneinfo

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
    
    # Define o fuso horário oficial do Brasil (Brasília) para corrigir o servidor externo
    fuso_brasil = zoneinfo.ZoneInfo("America/Sao_Paulo")
    data_atual = datetime.now(fuso_brasil).strftime("%d/%m/%Y %H:%M")
    
    score = int((pontos / total) * 100)
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
        return " ".join(texto.split())[:5000] # Limite para não estourar tokens
    except Exception as e:
        st.error(f"Erro ao acessar a documentação: {e}")
        return None

def gerar_questoes_ia(tema, nivel, contexto_web):
    base_info = f"Baseie-se neste conteúdo oficial da Salesforce: {contexto_web}" if contexto_web else "Use seu conhecimento geral de Salesforce."
    
    prompt = f"""
    {base_info}
    Gere exatamente 10 perguntas de múltipla escolha sobre Salesforce {tema}, nível {nivel}.
    Foque em cenários de prova de certificação Administrator (CRT-101).
    Responda EXCLUSIVAMENTE em formato JSON:
    {{
      "perguntas": [
        {{
          "pergunta": "Texto da pergunta", 
          "opcoes": ["A) ", "B) ", "C) ", "D) "], 
          "correta": "A",
          "explicacao": "Explicação técnica baseada na documentação."
        }}
      ]
    }}
    """
    response = client.chat.completions.create(
        model="gpt-4o-mini", 
        messages=[{"role": "system", "content": "Você é um instrutor Salesforce certified."},
                  {"role": "user", "content": prompt}],
        response_format={ "type": "json_object" }
    )
    dados = json.loads(response.choices[0].message.content)
    return dados.get('perguntas', [])[:10]

# --- ESTRUTURA PRINCIPAL (SEM BARRA LATERAL) ---
st.title("🎓 Salesforce Admin Coach AI")

# Criando as 3 abas no topo do aplicativo para navegação mobile amigável
aba_config, aba_simulado, aba_progresso = st.tabs(["⚙️ Configurar", "🔥 Simulado", "📊 Meu Progresso"])

# --- ABA 1: CONFIGURAÇÃO ---
with aba_config:
    st.write("### Prepare o seu próximo teste")
    
    col1, col2 = st.columns(2)
    with col1:
        topico_selecionado = st.selectbox("Escolha o Tópico do Exame:", list(LINKS_CERTIFICACAO.keys()))
    with col2:
        nivel = st.selectbox("Escolha o Nível de Dificuldade:", ["Iniciante", "Intermediário", "Especialista"])
        
    url_manual = st.text_input("🔗 Link Avançado (Opcional):", placeholder="Cole um link do Help Salesforce...")
    
    if st.button("🚀 Gerar Novas Questões"):
        url_para_ler = url_manual if topico_selecionado == "Personalizado (Usar link do campo abaixo)" else LINKS_CERTIFICACAO[topico_selecionado]
        
        with st.spinner("Analisando a documentação oficial da Salesforce..."):
            conteudo = extrair_texto_url(url_para_ler)
            st.session_state.questoes = gerar_questoes_ia(topico_selecionado, nivel, conteudo)
            st.session_state.respostas_usuario = {}
            st.session_state.corrigido = False
            st.session_state.simulado_ativo = True
            st.session_state.topico_atual = topico_selecionado
            st.session_state.nivel_atual = nivel
            st.success("Simulado gerado com sucesso! Clique na aba '🔥 Simulado' para começar.")

# --- ABA 2: O SIMULADO ---
with aba_simulado:
    if st.session_state.get('simulado_ativo'):
        st.write(f"### 📝 Teste Atual: {st.session_state.get('topico_atual')} ({st.session_state.get('nivel_atual')})")
        st.write("---")
        
        for i, q in enumerate(st.session_state.questoes):
            st.subheader(f"Questão {i+1}")
            st.write(q['pergunta'])
            
            resp = st.radio(f"Opções para a Q{i+1}:", q['opcoes'], key=f"q_{i}", index=None, disabled=st.session_state.get('corrigido', False))
            
            if resp:
                st.session_state.respostas_usuario[i] = resp[0]

            if st.session_state.get('corrigido'):
                user_choice = st.session_state.respostas_usuario.get(i)
                if user_choice == q['correta']:
                    st.success(f"✅ Correto! Gabarito: {q['correta']}")
                else:
                    st.error(f"❌ Incorreto. Você respondeu {user_choice if user_choice else 'Vazio'}, a resposta certa é {q['correta']}.")
                
                with st.expander("💡 Justificativa Oficial"):
                    st.write(q['explicacao'])
            st.markdown("---")

        if not st.session_state.get('corrigido'):
            if st.button("✅ Enviar Respostas para Correção"):
                acertos = sum(1 for i, q in enumerate(st.session_state.questoes) if st.session_state.respostas_usuario.get(i) == q['correta'])
                st.session_state.corrigido = True
                salvar_no_historico(st.session_state.topico_atual, st.session_state.nivel_atual, acertos, len(st.session_state.questoes))
                st.balloons()
                st.rerun()
    else:
        st.info("Nenhum simulado ativo no momento. Vá até a aba '⚙️ Configurar' e gere um novo teste!")

# --- ABA 3: PROGRESSO OTIMIZADA PARA CELULAR ---
with aba_progresso:
    st.write("### 📈 Sua Evolução nos Estudos")
    df = carregar_dados()
    
    if not df.empty:
        # Tratamento de dados para o gráfico
        df['Score_Num'] = df['Score %'].str.replace('%','').astype(int)
        
        # Elemento 1: Cartão de Destaque no topo
        media_atual = int(df['Score_Num'].mean())
        st.metric(label="🎯 Média de Acertos Geral", value=f"{media_atual}%")
        
        # Elemento 2: Gráfico de Linha Ajustado
        st.write("**Histórico de Rendimento (Acertos %):**")
        st.line_chart(df.set_index('Data')['Score_Num'], height=250)
        
        # Elemento 3: Tabela completa responsiva (use_container_width evita que ela amasse)
        st.write("**📋 Detalhes dos Testes Realizados:**")
        st.dataframe(df.drop(columns=['Score_Num']), use_container_width=True)
    else:
        st.info("Você ainda não salvou nenhum simulado. Complete um teste para ver seu gráfico evoluir!")
