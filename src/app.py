import io
import streamlit as st

# Inicializar variáveis de sessão no topo
if 'analysis_completed' not in st.session_state:
    st.session_state.analysis_completed = False
if 'analysis_result' not in st.session_state:
    st.session_state.analysis_result = None
if 'report_data' not in st.session_state:
    st.session_state.report_data = None

import pandas as pd
try:
    from fpdf import FPDF
except ImportError:
    FPDF = None
import streamlit as st
from pathlib import Path
from utils.file_utils import extract_structured_data, analyze_with_openai_structured, comparar_propostas
from utils.report_generator import BIDReportGenerator
import pandas as pd

def exibir_tabelas_estruturadas():
    """Exibe tabelas estruturadas separadas para mapa e propostas"""
    if not st.session_state.analysis_result:
        st.warning("Nenhum dado para exibir. Faça o upload dos arquivos primeiro.")
        return
    
    # Obtém os DataFrames estruturados
    dataframes = st.session_state.analysis_result.get("dataframes", {})
    mapa_df = dataframes.get("mapa_df")
    propostas_dfs = dataframes.get("propostas_dfs", [])
    
    # Exibe Mapa de Concorrência
    st.subheader("📋 MAPA DE CONCORRÊNCIA")
    if mapa_df is not None and not mapa_df.empty:
        st.dataframe(
            mapa_df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Nome_Proposta": "Nome da Proposta",
                "Numero_Proposta": "Nº Proposta",
                "Empresa_Participante": "Empresa",
                "Modelo_Produto": "Modelo",
                "Item": "Descrição do Item",
                "Quantidade": st.column_config.NumberColumn("Qtd.", format="%.0f"),
                "Unidade": "Un.",
                "Custo_Unitario": st.column_config.NumberColumn("Custo Unit. (R$)", format="R$ %.2f"),
                "Custo_Total": st.column_config.NumberColumn("Custo Total (R$)", format="R$ %.2f"),
                "Status_Equalizacao": "Status"
            }
        )
        st.info(f"📊 Total de itens no mapa: {len(mapa_df)}")
    else:
        st.warning("⚠️ Mapa de concorrência não encontrado ou vazio.")
    
    # Exibe Propostas Separadamente
    st.subheader("📄 PROPOSTAS ANALISADAS")
    
    if propostas_dfs and len(propostas_dfs) > 0:
        # Cria abas para cada proposta
        propostas_info = st.session_state.analysis_result.get("propostas", [])
        
        if len(propostas_dfs) == 1:
            # Se só há uma proposta, exibe diretamente
            proposta_df = propostas_dfs[0]
            proposta_info = propostas_info[0] if propostas_info else {}
            
            nome_fornecedor = proposta_info.get("fornecedor", "Fornecedor")
            nome_arquivo = proposta_info.get("nome_arquivo", "Arquivo")
            
            st.write(f"**{nome_fornecedor}** - `{nome_arquivo}`")
            
            if proposta_df is not None and not proposta_df.empty:
                st.dataframe(
                    proposta_df,
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "Nome_Proposta": "Nome da Proposta",
                        "Numero_Proposta": "Nº Proposta",
                        "Empresa_Participante": "Empresa",
                        "Modelo_Produto": "Modelo",
                        "Item": "Descrição do Item",
                        "Quantidade": st.column_config.NumberColumn("Qtd.", format="%.0f"),
                        "Unidade": "Un.",
                        "Custo_Unitario": st.column_config.NumberColumn("Custo Unit. (R$)", format="R$ %.2f"),
                        "Custo_Total": st.column_config.NumberColumn("Custo Total (R$)", format="R$ %.2f"),
                        "Status_Equalizacao": "Status"
                    }
                )
                st.info(f"📊 Total de itens na proposta: {len(proposta_df)}")
            else:
                st.warning("⚠️ Dados da proposta não puderam ser processados.")
        else:
            # Múltiplas propostas - usa abas
            tabs = st.tabs([
                f"{propostas_info[i].get('fornecedor', f'Proposta {i+1}')}" 
                for i in range(len(propostas_dfs))
            ])
            
            for i, (tab, proposta_df) in enumerate(zip(tabs, propostas_dfs)):
                with tab:
                    proposta_info = propostas_info[i] if i < len(propostas_info) else {}
                    nome_arquivo = proposta_info.get("nome_arquivo", "Arquivo")
                    
                    st.write(f"📄 Arquivo: `{nome_arquivo}`")
                    
                    if proposta_df is not None and not proposta_df.empty:
                        st.dataframe(
                            proposta_df,
                            use_container_width=True,
                            hide_index=True,
                            column_config={
                                "Nome_Proposta": "Nome da Proposta",
                                "Numero_Proposta": "Nº Proposta",
                                "Empresa_Participante": "Empresa",
                                "Modelo_Produto": "Modelo",
                                "Item": "Descrição do Item",
                                "Quantidade": st.column_config.NumberColumn("Qtd.", format="%.0f"),
                                "Unidade": "Un.",
                                "Custo_Unitario": st.column_config.NumberColumn("Custo Unit. (R$)", format="R$ %.2f"),
                                "Custo_Total": st.column_config.NumberColumn("Custo Total (R$)", format="R$ %.2f"),
                                "Status_Equalizacao": "Status"
                            }
                        )
                        st.info(f"📊 Total de itens: {len(proposta_df)}")
                    else:
                        st.warning("⚠️ Dados da proposta não puderam ser processados.")
    else:
        st.warning("⚠️ Nenhuma proposta encontrada.")

def exibir_analise_equalizada():
    """Exibe resultado da análise de equalização"""
    if not hasattr(st.session_state, 'analise_ia_result') or not st.session_state.analise_ia_result:
        return
    
    analise = st.session_state.analise_ia_result
    
    if analise.get("erro"):
        st.error(f"❌ Erro na análise: {analise.get('mensagem', 'Erro desconhecido')}")
        return
    
    st.subheader("🎯 RESULTADO DA ANÁLISE DE EQUALIZAÇÃO")
    
    # Resumo da equalização
    resumo = analise.get("resumo_equalizacao", {})
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("📄 Total de Propostas", resumo.get("total_propostas", 0))
    with col2:
        st.metric("✅ Itens Equalizados", resumo.get("itens_equalizados", 0))
    with col3:
        st.metric("❌ Itens Não Equalizados", resumo.get("itens_nao_equalizados", 0))
    
    # Exibe propostas equalizadas
    propostas_analisadas = analise.get("propostas_analisadas", [])
    
    if propostas_analisadas:
        st.subheader("📊 PROPOSTAS COM STATUS DE EQUALIZAÇÃO")
        
        for proposta in propostas_analisadas:
            if not proposta.get("erro"):
                with st.expander(f"🏢 {proposta.get('fornecedor', 'Fornecedor')} - {proposta.get('nome_arquivo', 'Arquivo')}"):
                    
                    # Métricas da proposta
                    col1, col2 = st.columns(2)
                    with col1:
                        st.metric("✅ Equalizados", proposta.get("itens_equalizados", 0))
                    with col2:
                        st.metric("❌ Não Equalizados", proposta.get("itens_nao_equalizados", 0))
                    
                    # DataFrame equalizado
                    df_equalizado = proposta.get("dataframe_equalizado")
                    if df_equalizado is not None and not df_equalizado.empty:
                        st.dataframe(
                            df_equalizado,
                            use_container_width=True,
                            hide_index=True,
                            column_config={
                                "Status_Equalizacao": st.column_config.TextColumn(
                                    "Status",
                                    help="Status de equalização do item"
                                )
                            }
                        )
                    
                    # Observações
                    observacoes = proposta.get("observacoes", [])
                    if observacoes:
                        st.write("📝 **Observações:**")
                        for obs in observacoes:
                            st.write(f"• **{obs.get('item', 'Item')}**: {obs.get('motivo', 'N/A')}")
    
    # Mix de melhor preço
    mix = analise.get("mix_melhor_preco", {})
    if mix and not mix.get("erro"):
        st.subheader("💰 MIX DE MELHOR PREÇO")
        
        itens_mix = mix.get("itens", [])
        if itens_mix:
            # Cria DataFrame do mix
            dados_mix = []
            for item in itens_mix:
                dados_mix.append({
                    "Item": item.get("item", "N/A"),
                    "Fornecedor": item.get("fornecedor_selecionado", "N/A"),
                    "Custo": item.get("custo", 0)
                })
            
            df_mix = pd.DataFrame(dados_mix)
            st.dataframe(
                df_mix,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Custo": st.column_config.NumberColumn("Custo (R$)", format="R$ %.2f")
                }
            )
            
            total_mix = mix.get("total", 0)
            st.success(f"💰 **Total do Mix de Melhor Preço: R$ {total_mix:,.2f}**")

# Mantém a função original para compatibilidade (será removida gradualmente)
def exibir_tabela_extraida():
    """Função mantida para compatibilidade - será removida em versões futuras"""
    st.warning("Esta função está sendo descontinuada. Use 'exibir_tabelas_estruturadas()' no lugar.")
    exibir_tabelas_estruturadas()
import json  # Importado para usar o json.dumps

# Configuração da página
st.set_page_config(
    page_title="TOOLS - Análise de BID",
    page_icon="🔨",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# CSS customizado para o layout da TOOLS
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(90deg, #009e3c 0%, #00b347 100%);
        padding: 1rem 2rem;
        border-radius: 10px;
        margin-bottom: 2rem;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }
    .main-header h1 {
        color: white;
        margin: 0;
        font-size: 2rem;
        font-weight: 700;
    }
    .main-header h3 {
        color: #f0f8f0;
        margin: 0;
        font-size: 1.1rem;
        font-weight: 400;
    }
    .ai-analysis {
        background-color: #f8f9fa;
        border-left: 4px solid #009e3c;
        padding: 1rem;
        margin: 1rem 0;
        border-radius: 5px;
    }
    .download-buttons {
        display: flex;
        gap: 10px;
        margin: 20px 0;
    }
    .report-section {
        background-color: #f8f9fa;
        padding: 20px;
        border-radius: 10px;
        margin: 20px 0;
        border: 1px solid #dee2e6;
    }
</style>
""", unsafe_allow_html=True)

st.markdown('<div style="margin-top: 10px; margin-bottom: 0px; text-align: center;">', unsafe_allow_html=True)
st.image("src/utils/Logo Verde.png", width=180)
st.markdown('<h3 style="margin-top: 0px; margin-bottom: 0px; color: #0e938e; font-weight: 600;">Agente de Suprimentos - Análise de BID</h3>', unsafe_allow_html=True)
st.markdown('</div>', unsafe_allow_html=True)
st.markdown('<div style="margin-top: 32px;"></div>', unsafe_allow_html=True)

# Instruções do processo de análise

# Inicializar variáveis de sessão
if 'analysis_completed' not in st.session_state:
    st.session_state.analysis_completed = False
if 'analysis_result' not in st.session_state:
    st.session_state.analysis_result = None
if 'report_data' not in st.session_state:
    st.session_state.report_data = None

# Upload de arquivos

# NOVO FLUXO: Solicitação clara dos arquivos
st.markdown("""
### 📁 Importação de Documentos
Por favor, envie o mapa de concorrência (PDF ou Excel) e as propostas comerciais associadas para análise comparativa.
""")

uploaded_files = st.file_uploader(
    "Enviar arquivos de mapa e propostas",
    type=["pdf", "xlsx", "xls"],
    accept_multiple_files=True,
)

if uploaded_files:
    st.markdown("#### Arquivos carregados:")
    for file in uploaded_files:
        st.write(f"- **{file.name}** ({file.type}, {file.size/1024:.1f} KB)")


    if st.button("🔍 Solicitar Extração dos Dados", type="primary"):
        with st.spinner("🔄 Extraindo dados dos documentos..."):
            result = extract_structured_data(uploaded_files)
            st.session_state.analysis_result = result


    # Exibe sempre que houver resultado de extração
    if st.session_state.analysis_result and isinstance(st.session_state.analysis_result, dict):
        st.success("✅ Extração concluída com sucesso!")
        # Se houver validações, exibe
        if "validations" in st.session_state.analysis_result:
            st.markdown("### 📋 Validação dos Documentos:")
            for validation in st.session_state.analysis_result["validations"]:
                st.markdown(f"- {validation}")

        # Exibe as tabelas estruturadas separadas
        exibir_tabelas_estruturadas()

    # NOVO: Relatório colorido lado a lado sem IA
    if st.session_state.analysis_result is not None:
        mapa = st.session_state.analysis_result.get("mapa_concorrencia", {})
        propostas = st.session_state.analysis_result.get("propostas", [])
        if not mapa or not mapa.get("itens"):
            st.warning("Por favor, insira o mapa de concorrência para realizar a análise comparativa.")
        else:
            comparacao = comparar_propostas(mapa, propostas)
            if isinstance(comparacao, dict):
                st.success("✅ Relatório comparativo gerado!")
                st.markdown("### 📊 Relatório Técnico Comparativo")
                # Monta DataFrame para o relatório técnico comparativo
                import pandas as pd
                tabela_comparativa = []
                for item, mix_item in zip(comparacao['resultado'], comparacao['mix_melhor_preco']):
                    fornecedores = item.get("fornecedores", {})
                    for fornecedor, dados in fornecedores.items():
                        linha = {
                            "Item": item.get("item", ""),
                            "Qtd.": item.get("quantidade", ""),
                            "Fabricante": dados.get("fabricante", fornecedor),
                            "Modelo": dados.get("modelo_produto", dados.get("modelo", "")),
                            "Fornecedor": fornecedor,
                            "Valor Uni (R$)": dados.get("valor", ""),
                            "Especificação": dados.get("especificacao", ""),
                            "Melhor Preço": item.get("melhor_preco", ""),
                            "Pior Preço": (
                                max(
                                    [f for f in fornecedores if isinstance(fornecedores[f].get("valor",0), (int, float)) or str(fornecedores[f].get("valor",0)).replace(',','').replace('.','').isdigit()],
                                    key=lambda x: float(str(fornecedores[x].get("valor",0)).replace('.','').replace(',','.')) if str(fornecedores[x].get("valor",0)).replace(',','').replace('.','').isdigit() else 0
                                ) if [f for f in fornecedores if isinstance(fornecedores[f].get("valor",0), (int, float)) or str(fornecedores[f].get("valor",0)).replace(',','').replace('.','').isdigit()] else ""
                            ) if fornecedores else "",
                            "Diferença": item.get("diferenca_valores", ""),
                            "Sugestão": item.get("recomendacao", "")
                        }
                        tabela_comparativa.append(linha)
                df_comparativo = pd.DataFrame(tabela_comparativa)
                st.dataframe(df_comparativo, use_container_width=True)
                # Removido Mix de Melhor Preço por Item
                # Resumo final: ranking dos fornecedores pelo valor total
                st.markdown("#### 🏅 Ranking dos Fornecedores pelo Valor Total")
                ranking = {}
                for item in comparacao['resultado']:
                    for f, d in item['fornecedores'].items():
                        if isinstance(d['valor'], (int, float)):
                            ranking[f] = ranking.get(f, 0) + d['valor']
                ranking_ord = sorted(ranking.items(), key=lambda x: x[1])
                st.table([{ 'Fornecedor': f, 'Valor Total': v } for f, v in ranking_ord])
                # Removido Condições de Pagamento e Descontos

                # Botões de exportação Excel e PDF
                st.markdown("---")
                st.markdown("### Exportar Relatório")
                import pandas as pd
                from io import BytesIO
                import base64
                # Monta DataFrame do resultado
                df_result = pd.DataFrame([
                    {
                        'Item': item.get('item',''),
                        **{f: item['fornecedores'][f]['valor'] for f in item['fornecedores']},
                        'Melhor Fornecedor': item.get('melhor_preco',''),
                        'Pior Fornecedor': (
                            max(
                                [f for f in item['fornecedores'] if isinstance(item['fornecedores'][f]['valor'], (int, float))],
                                key=lambda f: item['fornecedores'][f]['valor']
                            ) if any(isinstance(item['fornecedores'][f]['valor'], (int, float)) for f in item['fornecedores']) else ''
                        ),
                        'Diferença': item.get('diferenca_valores','')
                    }
                    for item in comparacao['resultado']
                ])
                # Exportar Excel
                output_excel = BytesIO()
                df_result.to_excel(output_excel, index=False)
                output_excel.seek(0)
                b64_excel = base64.b64encode(output_excel.read()).decode()
                href_excel = f'<a href="data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64,{b64_excel}" download="relatorio_comparativo.xlsx">📥 Baixar Excel</a>'
                st.markdown(href_excel, unsafe_allow_html=True)
                # Exportar PDF (simples, via HTML)
                try:
                    from fpdf import FPDF
                    pdf = FPDF()
                    pdf.add_page()
                    pdf.set_font("Arial", size=12)
                    pdf.cell(200, 10, txt="Relatório Comparativo de Propostas", ln=True, align='C')
                    pdf.ln(10)
                    # Cabeçalho
                    colunas = df_result.columns.tolist()
                    for col in colunas:
                        pdf.cell(40, 10, col, border=1)
                    pdf.ln()
                    # Dados
                    for i, row in df_result.iterrows():
                        for col in colunas:
                            valor = str(row[col])
                            pdf.cell(40, 10, valor, border=1)
                        pdf.ln()
                    pdf_bytes = pdf.output(dest='S').encode('latin1')
                    b64_pdf = base64.b64encode(pdf_bytes).decode()
                    href_pdf = f'<a href="data:application/pdf;base64,{b64_pdf}" download="relatorio_comparativo.pdf">📥 Baixar PDF</a>'
                    st.markdown(href_pdf, unsafe_allow_html=True)
                except Exception as e:
                    st.info("PDF não disponível: instale a biblioteca fpdf (pip install fpdf) para exportar.")
            else:
                st.error(comparacao[0].get('mensagem', 'Erro na análise comparativa.'))
    if "analysis_result_ia" in st.session_state:
        st.write("Resultado IA:", st.session_state.analysis_result_ia)

        # Botão para realizar análise de equalização
        if st.button("🎯 Analisar Equalização"):
            with st.spinner("⚙️ Realizando análise de equalização..."):
                result_ia = analyze_with_openai_structured(st.session_state.analysis_result)
                st.session_state.analise_ia_result = result_ia

        # Exibe resultado da análise de equalização
        if hasattr(st.session_state, 'analise_ia_result') and st.session_state.analise_ia_result:
            exibir_analise_equalizada()

# Seção de Relatórios - mantida após análise
if st.session_state.get('analysis_completed', False) or st.session_state.get('analise_ia_result'):
    st.markdown("---")
    st.subheader("📊 RELATÓRIOS E EXPORTAÇÕES")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("📥 Exportar para Excel"):
            st.info("Funcionalidade de exportação será implementada em breve.")
    
    with col2:
        if st.button("📄 Gerar Relatório PDF"):
            st.info("Funcionalidade de relatório PDF será implementada em breve.")

# Rodapé
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #666; font-size: 0.9rem;">
    <p>TOOLS Engenharia - Agente de Suprimentos com IA | Versão 2.1 | Ambiente de Produção</p>
</div>
""", unsafe_allow_html=True)
