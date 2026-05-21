import streamlit as st
import pandas as pd
from openai import OpenAI
import json
import os
from datetime import datetime
import zoneinfo

# 1. Configuração da Página
st.set_page_config(page_title="Simulado - Salesforce Administrator", page_icon="🛡️", layout="wide")

# 2. Autenticação Segura
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

# --- SEGURANÇA: EVITAR ATTRIBUTE ERROR POR CHAVES ANTIGAS ---
if 'simulado_ativo' not in st.session_state:
    st.session_state.clear()
    st.session_state.simulado_ativo = False
    st.session_state.corrigido = False
    st.session_state.respostas_usuario = {}
    st.session_state.questoes = []

# --- REQUISITOS DA PROVA SALESFORCE ADMIN (CRT-101) ---
MODULOS_ADMIN = [
    "Configuração e Objetos",
    "Segurança e Acesso",
    "Automação de Processos/Flow",
    "Relatórios e Dashboards",
    "Guia Geral do Administrador"
]

# --- FUNÇÕES DE APOIO ---
def carregar_dados():
    arquivo = 'historico_simulados.csv'
    if os.path.exists(arquivo):
        return pd.read_csv(arquivo)
    return pd.DataFrame(columns=['Data', 'Tema', 'Dificuldade', 'Acertos', 'Total', 'Score %'])

def salvar_no_historico(tema, dificuldade, pontos, total):
    arquivo = 'historico_simulados.csv'
    fuso_brasil = zoneinfo.ZoneInfo("America/Sao_Paulo")
    data_atual = datetime.now(fuso_brasil).strftime("%d/%m/%Y %H:%M")
    
    score = int((pontos / total) * 100)
    # CORRIGIDO: de difficulty para dificuldade para eliminar o NameError
    novo_registro = pd.DataFrame([[data_atual, tema, dificuldade, pontos, total, f"{score}%"]], 
                                columns=['Data', 'Tema', 'Dificuldade', 'Acertos', 'Total', 'Score %'])
    df_atual = carregar_dados()
    df_final = pd.concat([df_atual, novo_registro], ignore_index=True)
    df_final.to_csv(arquivo, index=False)
    return score

def gerar_questoes_ia(tema, nivel):
    prompt = f"""
    Gere um caderno de testes COMPLETAMENTE ALEATÓRIO e INÉDITO contendo exatamente 10 perguntas de múltipla escolha sobre o módulo: {tema}.
    Nível de complexidade exigido: {nivel}.
    Mecânica de Alinhamento: Exame oficial Salesforce Certified Administrator (CRT-101).
    Importante: Varie os cenários de negócios, use diferentes objetos e requisitos práticos a cada execução para que o aluno nunca estude com o mesmo padrão.
    
    Certifique-se de preencher rigorosamente todos os 10 objetos no array JSON.
    Responda EXCLUSIVAMENTE no formato JSON estruturado abaixo:
    {{
      "perguntas": [
        {{
          "pergunta": "Texto dinâmico e prático do cenário ou questão", 
          "opcoes": ["A) Opção 1", "B) Opção 2", "C) Opção 3", "D) Opção 4"], 
          "correta": "A/B/C/D",
          "explicacao": "Análise técnica justificando a alternativa correta baseada nas regras de arquitetura da Salesforce."
        }}
      ]
    }}
    """
    response = client.chat.completions.create(
        model="gpt-4o-mini", 
        messages=[{"role": "system", "content": "Você é um avaliador Salesforce dinâmico. Sua meta é criar 10 questões originais, variadas e nunca repetidas dentro do bloco JSON."},
                  {"role": "user", "content": prompt}],
        response_format={ "type": "json_object" },
        temperature=0.9
    )
    dados = json.loads(response.choices[0].message.content)
    return dados.get('perguntas', [])[:10]

# --- DESIGN PRINCIPAL ---
st.markdown('<h2 style="font-size: 20px; margin-bottom: 12px; font-weight: 700; color: #1E88E5;">🛡️ Simulado - Salesforce Administrator</h2>', unsafe_allow_html=True)

aba_config, aba_simulado, aba_progresso = st.tabs(["⚙️ Configurar", "🔥 Simulado", "📊 Meu Progresso"])

# --- ABA 1: CONFIGURAÇÃO ---
with aba_config:
    topico_selecionado = st.selectbox("Escolha o Tópico do Exame:", MODULOS_ADMIN)
    nivel = st.selectbox("Escolha o Nível de Dificuldade:", ["Iniciante", "Intermediário", "Especialista"])
    
    if st.button("🚀 Gerar Simulado Completo"):
        with st.spinner("Sorteando 10 questões inéditas para o seu caderno..."):
            st.session_state.respostas_usuario = {}
            st.session_state.corrigido = False
            
            st.session_state.questoes = gerar_questoes_ia(topico_selecionado, nivel)
            st.session_state.topico_atual = topico_selecionado
            st.session_state.nivel_atual = nivel
            st.session_state.simulado_ativo = True
            st.success("Simulado pronto! Vá para a aba '🔥 Simulado'.")

# --- ABA 2: O SIMULADO ---
with aba_simulado:
    if st.session_state.get('simulado_ativo') and st.session_state.get('questoes'):
        st.markdown(f"### 📝 Prova Ativa: {st.session_state.get('topico_atual')}")
        st.caption(f"Nível selecionado: {st.session_state.get('nivel_atual')} | Alvo para aprovação: 65%")
        st.write("---")
        
        for i, q in enumerate(st.session_state.questoes):
            st.markdown(f"##### **Questão {i+1} de {len(st.session_state.questoes)}**")
            st.write(q['pergunta'])
            
            resp = st.radio(f"Selecione a resposta para a Q{i+1}:", q['opcoes'], key=f"q_{i}", index=None, disabled=st.session_state.get('corrigido', False))
            
            if resp:
                st.session_state.respostas_usuario[i] = resp[0]

            if st.session_state.get('corrigido'):
                user_choice = st.session_state.respostas_usuario.get(i)
                if user_choice == q['correta']:
                    st.success(f"✅ Correto! Gabarito: {q['correta']}")
                else:
                    st.error(f"❌ Errado. Sua resposta: {user_choice if user_choice else 'Nenhuma'}. Resposta Certa: {q['correta']}.")
                with st.expander("💡 Ver Justificativa Técnica"):
                    st.write(q['explicacao'])
            st.markdown("---")

        # --- BOTÃO DE FINALIZAÇÃO DIRETA ---
        if not st.session_state.get('corrigido'):
            if st.button("🏁 Finalizar e Corrigir Simulado"):
                total_questoes = len(st.session_state.questoes)
                
                if len(st.session_state.respostas_usuario) < total_questoes:
                    st.error("⚠️ Atenção! Você não respondeu todas as questões do caderno.")
                    st.markdown("<span style='font-size: 14px; font-weight: 700; display:block; margin-bottom:10px;'>📋 Painel de Revisão do Simulado</span>", unsafe_allow_html=True)
                    
                    grid_html = '<div style="display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 12px; justify-content: flex-start;">'
                    for idx in range(total_questoes):
                        respondida = idx in st.session_state.respostas_usuario
                        bg_color = "#2E7D32" if respondida else "#757575"
                        text_color = "#FFFFFF"
                        
                        grid_html += f'<div style="width: 36px; height: 36px; background-color: {bg_color}; color: {text_color}; display: flex; align-items: center; justify-content: center; font-weight: 700; border-radius: 6px; font-size: 14px;">{idx + 1}</div>'
                    grid_html += '</div>'
                    
                    legenda_html = """
                    <div style="display: flex; gap: 15px; font-size: 11px; font-weight: 600; margin-bottom: 15px;">
                        <div style="display: flex; align-items: center; gap: 5px;"><div style="width: 12px; height: 12px; background-color: #2E7D32; border-radius: 3px;"></div> Respondida</div>
                        <div style="display: flex; align-items: center; gap: 5px;"><div style="width: 12px; height: 12px; background-color: #757575; border-radius: 3px;"></div> Em Branco</div>
                    </div>
                    """
                    st.markdown(grid_html, unsafe_allow_html=True)
                    st.markdown(legenda_html, unsafe_allow_html=True)
                else:
                    acertos = sum(1 for i, q in enumerate(st.session_state.questoes) if st.session_state.respostas_usuario.get(i) == q['correta'])
                    salvar_no_historico(st.session_state.topico_atual, st.session_state.nivel_atual, acertos, total_questoes)
                    st.session_state.corrigido = True
                    st.rerun()
    else:
        st.info("Nenhum simulado ativo. Monte a configuração na primeira aba para iniciar!")

# --- ABA 3: PROGRESSO PROFISSIONAL WEB ---
with aba_progresso:
    df = carregar_dados()
    
    if not df.empty:
        df['Tema'] = df['Tema'].str.replace(r'\s\(\d+%\)', '', regex=True)
        df['Score_Num'] = df['Score %'].str.replace('%','').astype(int)
        
        media_geral = int(df['Score_Num'].mean())
        status_aprovacao = "Aprovado 🎉" if media_geral >= 65 else "Abaixo da Meta"
        color_status = "#2E7D32" if media_geral >= 65 else "#FF6D00" 
        
        with st.container(border=True):
            st.markdown(
                f"""
                <div style="text-align: center; padding: 2px;">
                    <span style="font-size: 12px; font-weight: 600; display:block; text-transform: uppercase; letter-spacing: 0.5px;">Média de Acertos Geral</span>
                    <span style="font-size: 30px; font-weight: 800; color: #1E88E5; display: block; line-height: 1.1;">{media_geral}%</span>
                    <span style="font-size: 12px; font-weight: 700; color: {color_status}; display: block; margin-top: 2px;">
                        Previsão: {status_aprovacao}
                    </span>
                </div>
                """, 
                unsafe_allow_html=True
            )
            
        st.write("---")
        
        st.markdown('<span style="font-size: 15px; font-weight: 700;">🏷️ Rendimento Médio por Módulo (Média de Questões)</span>', unsafe_allow_html=True)
        df_modulos = df.groupby('Tema').agg({'Acertos': 'mean', 'Total': 'mean'}).reset_index()
        df_modulos.columns = ['Módulo', 'Média de Acertos', 'Total de Questões']
        df_modulos['Rendimento Técnico'] = df_modulos['Média de Acertos'].round(1).astype(str) + " de " + df_modulos['Total de Questões'].astype(int).astype(str) + " acertos"
        
        st.dataframe(df_modulos[['Módulo', 'Rendimento Técnico']], use_container_width=True, hide_index=True)
        
        st.write("---")
        
        st.markdown('<span style="font-size: 15px; font-weight: 700;">🔍 Módulos que precisam de Atenção Urgente (Foco de Estudos):</span>', unsafe_allow_html=True)
        medias_por_tema = df.groupby('Tema')['Score_Num'].mean().to_dict()
        temas_criticos = [f"⚠️ **{tema}**" for tema, media in medias_por_tema.items() if media < 65]
                
        if temas_criticos:
            for item in temas_criticos:
                st.markdown(f"<div style='font-size:13px; margin-bottom:6px; color:#FF6D00;'>{item}</div>", unsafe_allow_html=True)
        else:
            st.success("🔥 Excelente! Todos os módulos estão operando com desempenho seguro.")
        
    else:
        st.info("O histórico está vazio. Faça um teste para ativar o painel!")
