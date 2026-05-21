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

# --- REQUISITOS DA PROVA SALESFORCE ADMIN (CRT-101) ---
MODULOS_ADMIN = [
    "Configuração e Objetos (20%)",
    "Segurança e Acesso (14%)",
    "Automação de Processos/Flow (16%)",
    "Relatórios e Dashboards (10%)",
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
    novo_registro = pd.DataFrame([[data_atual, tema, dificuldade, pontos, total, f"{score}%"]], 
                                columns=['Data', 'Tema', 'Dificuldade', 'Acertos', 'Total', 'Score %'])
    df_atual = carregar_dados()
    df_final = pd.concat([df_atual, novo_registro], ignore_index=True)
    df_final.to_csv(arquivo, index=False)
    return score

def gerar_questoes_ia(tema, nivel):
    prompt = f"""
    Gere exatamente 15 perguntas de múltipla escolha sobre o módulo de Salesforce: {tema}, focado no nível {nivel}.
    Os cenários devem ser práticos, realistas e alinhados com a prova oficial de certificação Salesforce Certified Administrator (CRT-101).
    Responda EXCLUSIVAMENTE em formato JSON estruturado:
    {{
      "perguntas": [
        {{
          "pergunta": "Texto completo do cenário ou questão", 
          "opcoes": ["A) Opção 1", "B) Opção 2", "C) Opção 3", "D) Opção 4"], 
          "correta": "A",
          "explicacao": "Explicação detalhada do porquê esta alternativa está correta conforme as boas práticas da Salesforce."
        }}
      ]
    }}
    """
    response = client.chat.completions.create(
        model="gpt-4o-mini", 
        messages=[{"role": "system", "content": "Você é um instrutor e avaliador sênior especialista em certificações Salesforce."},
                  {"role": "user", "content": prompt}],
        response_format={ "type": "json_object" }
    )
    dados = json.loads(response.choices[0].message.content)
    return dados.get('perguntas', [])[:15]

# --- DESIGN PRINCIPAL ---
st.markdown('<h2 style="font-size: 22px; margin-bottom: 15px;">🎓 Simulado - Salesforce Administrator</h2>', unsafe_allow_html=True)

aba_config, aba_simulado, aba_progresso = st.tabs(["⚙️ Configurar", "🔥 Simulado", "📊 Meu Progresso"])

# --- ABA 1: CONFIGURAÇÃO ---
with aba_config:
    topico_selecionado = st.selectbox("Escolha o Tópico do Exame:", MODULOS_ADMIN)
    nivel = st.selectbox("Escolha o Nível de Dificuldade:", ["Iniciante", "Intermediário", "Especialista"])
    
    if st.button("🚀 Gerar Simulado Completo"):
        with st.spinner("Construindo caderno com 15 questões..."):
            st.session_state.questoes = gerar_questoes_ia(topico_selecionado, nivel)
            st.session_state.respostas_usuario = {}
            st.session_state.corrigido = False
            st.session_state.simulado_ativo = True
            st.session_state.topico_atual = topico_selecionado
            st.session_state.nivel_atual = nivel
            st.session_state.confirmou_salvamento = False
            st.success("Simulado pronto! Vá para a aba '🔥 Simulado'.")

# --- ABA 2: O SIMULADO ---
with aba_simulado:
    if st.session_state.get('simulado_ativo'):
        st.markdown(f"### 📝 Desafio Iniciado: {st.session_state.get('topico_atual')}")
        st.caption(f"Nível: {st.session_state.get('nivel_atual')} | Meta: 65%")
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

        # Zona de Validação e Encerramento
        if not st.session_state.get('corrigido'):
            if st.button("🏁 Finalizar e Corrigir Simulado"):
                total_questoes = len(st.session_state.questoes)
                respondidas = list(st.session_state.respostas_usuario.keys())
                
                # Verifica se há pendências
                if len(respondidas) < total_questoes:
                    st.error("⚠️ Atenção! Você não respondeu todas as questões do caderno.")
                    
                    # Cria listas de amostragem no final da tela
                    col_res_1, col_res_2 = st.columns(2)
                    with col_res_1:
                        ok_list = [f"Questão {idx+1}" for idx in respondidas]
                        st.info(f"**Respondidas ({len(respondidas)}):**\n" + (", ".join(ok_list) if ok_list else "Nenhuma"))
                    with col_res_2:
                        falta_list = [f"Questão {idx+1}" for idx in range(total_questoes) if idx not in respondidas]
                        st.warning(f"**Faltam Responder ({len(falta_list)}):**\n" + ", ".join(falta_list))
                else:
                    st.session_state.confirmou_salvamento = True

            # Caixa de confirmação de salvamento (Aparece se passou no teste de preenchimento)
            if st.session_state.get('confirmou_salvamento'):
                st.write("---")
                st.markdown("#### 💾 Deseja salvar este progresso no seu histórico?")
                col_btn1, col_btn2 = st.columns(2)
                
                if col_btn1.button("✅ Sim, Salvar e Corrigir"):
                    acertos = sum(1 for i, q in enumerate(st.session_state.questoes) if st.session_state.respostas_usuario.get(i) == q['correta'])
                    st.session_state.corrigido = True
                    st.session_state.confirmou_salvamento = False
                    score_final = salvar_no_historico(st.session_state.topico_atual, st.session_state.nivel_atual, acertos, len(st.session_state.questoes))
                    
                    if score_final == 100:
                        st.balloons()
                        st.success("🏆 INCRÍVEL! Parabéns, você gabaritou com 100% de aproveitamento!")
                    elif score_final >= 65:
                        st.balloons()
                        st.info("🎉 Você foi muito bem até aqui, mas pode melhorar ainda mais!")
                    else:
                        st.warning("Treino concluído! Revise as justificativas técnicas para alcançar os 65% na próxima tentativa.")
                    st.rerun()
                    
                if col_btn2.button("❌ Não, Apenas Corrigir Sem Salvar"):
                    st.session_state.corrigido = True
                    st.session_state.confirmou_salvamento = False
                    st.rerun()
    else:
        st.info("Nenhum simulado ativo. Monte a configuração na primeira aba para iniciar!")

# --- ABA 3: PROGRESSO OTIMIZADA (MOBILE-FIRST) ---
with aba_progresso:
    df = carregar_dados()
    
    if not df.empty:
        df['Score_Num'] = df['Score %'].str.replace('%','').astype(int)
        
        # Resumo de Status Principal (Métricas Compactas)
        media_geral = int(df['Score_Num'].mean())
        col_m1, col_m2 = st.columns(2)
        with col_m1:
            st.metric(label="🎯 Média Geral", value=f"{media_geral}%")
        with col_m2:
            status_aprovacao = "Aprovada 🎉" if media_geral >= 65 else "Abaixo da Meta"
            st.metric(label="🛡️ Certificação", value=status_aprovacao)
            
        st.write("---")
        
        # --- TABELA 1: RENDIMENTO POR MÓDULO (Compacta) ---
        st.write("### 🏷️ Rendimento por Módulo")
        df_modulos = df.groupby('Tema')['Score_Num'].mean().reset_index()
        df_modulos.columns = ['Módulo', 'Média']
        df_modulos['Média'] = df_modulos['Média'].round(0).astype(int).astype(str) + '%'
        st.dataframe(df_modulos, use_container_width=True, hide_index=True)
        
        st.write("---")
        
        # --- SEÇÃO CRÍTICA ULTRA COMPACTA (Evita quebra no celular) ---
        st.write("### 🔍 Atenção Urgente:")
        medias_por_tema = df.groupby('Tema')['Score_Num'].mean().to_dict()
        
        temas_criticos = [f"⚠️ {tema[:18]}... ({int(media)}%)" for tema, media in medias_por_tema.items() if media < 65]
                
        if temas_criticos:
            for item in temas_criticos:
                st.write(item)
        else:
            st.success("🔥 Todos os módulos estão acima da média!")

        st.write("---")
        
        # --- TABELA 2: HISTÓRICO DE SIMULADOS ENXUTO (Sem data e sem dificuldade) ---
        st.write("### 📋 Detalhes dos Testes")
        
        df_visual = df.copy()
        df_visual['Resultado'] = df_visual['Score_Num'].apply(lambda x: "💚 OK" if x >= 65 else "❤️ Rev")
        df_visual = df_visual[['Tema', 'Score %', 'Resultado']]
        df_visual.columns = ['Módulo', 'Aproveitamento', 'Status']
        
        st.dataframe(df_visual.iloc[::-1], use_container_width=True, hide_index=True)
        
    else:
        st.info("O histórico está vazio. Faça um teste para ativar o painel!")
