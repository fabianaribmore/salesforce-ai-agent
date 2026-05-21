# --- ABA 3: PROGRESSO PROFISSIONAL WEB ---
with aba_progresso:
    df = carregar_dados()
    
    if not df.empty:
        df['Tema'] = df['Tema'].apply(lambda x: re.sub(r'\s*\(\d+%\)\s*', '', str(x)).strip())
        df['Score_Num'] = df['Score %'].astype(str).str.replace('%','').astype(int)
        
        media_geral = int(df['Score_Num'].mean())
        status_aprovacao = "Aprovado 🎉" if media_geral >= 65 else "Abaixo da Meta"
        
        col_kpi1, col_kpi2 = st.columns([1, 2])
        with col_kpi1:
            st.metric(label="Média Geral de Acertos", value=f"{media_geral}%", delta=status_aprovacao, delta_color="normal" if media_geral >= 65 else "inverse")
        
        st.write("---")
        
        st.markdown('<span style="font-size: 16px; font-weight: 700; color: #1E88E5; display: block; margin-bottom: 16px;">📋 Matriz Estratégica de Aprendizado</span>', unsafe_allow_html=True)
        
        # Agrupamento e cálculo do rendimento por módulo
        df_modulos = df.groupby('Tema').agg({'Acertos': 'sum', 'Total': 'sum'}).reset_index()
        df_modulos.columns = ['Módulo', 'Total Acertos', 'Total Questões']
        df_modulos['Porcentagem_Valor'] = ((df_modulos['Total Acertos'] / df_modulos['Total Questões']) * 100).astype(int)
        
        # Ordenação inteligente: menor aproveitamento no topo para priorizar estudos
        df_modulos = df_modulos.sort_values(by='Porcentagem_Valor', ascending=True)
        
        # Renderização dinâmica dos cards móveis/desktop responsivos
        for idx, row in df_modulos.iterrows():
            pct = row['Porcentagem_Valor']
            modulo_nome = row['Módulo']
            
            # Regra técnica de cores e textos do Plano de Ação
            if pct < 50:
                texto_acao = "Prioridade Alta"
                cor_badge = "#D32F2F"   # Vermelho corporativo
                cor_fundo = "#FFEBEE"
            elif pct < 65:
                texto_acao = "Ajustes Finais"
                cor_badge = "#F57C00"   # Laranja
                cor_fundo = "#FFF3E0"
            elif pct < 80:
                texto_acao = "Meta Atingida"
                cor_badge = "#388E3C"   # Verde
                cor_fundo = "#E8F5E9"
            else:
                texto_acao = "Excelente"
                cor_badge = "#1976D2"   # Azul premium
                cor_fundo = "#E3F2FD"
            
            # Estrutura HTML/CSS limpa para os Cards
            card_html = f"""
            <div style="
                background-color: transparent;
                border-bottom: 1px solid #E0E0E0;
                padding: 12px 4px;
                display: flex;
                justify-content: space-between;
                align-items: center;
                gap: 10px;
            ">
                <div style="flex: 1;">
                    <div style="font-size: 14px; font-weight: 600; color: #333333; line-height: 1.3;">
                        {modulo_nome}
                    </div>
                    <div style="font-size: 12px; color: #666666; margin-top: 2px;">
                        Aproveitamento atual: <strong>{pct}%</strong>
                    </div>
                </div>
                <div style="
                    background-color: {cor_fundo};
                    color: {cor_badge};
                    font-size: 11px;
                    font-weight: 700;
                    padding: 5px 10px;
                    border-radius: 12px;
                    text-transform: uppercase;
                    letter-spacing: 0.5px;
                    white-space: nowrap;
                    text-align: center;
                    border: 1px solid {cor_badge}40;
                ">
                    {texto_acao}
                </div>
            </div>
            """
            st.markdown(card_html, unsafe_allow_html=True)
            
    else:
        st.info("O histórico está vazio. Faça um teste para ativar o painel!")
