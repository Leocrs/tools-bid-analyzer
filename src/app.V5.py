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
import base64
from io import BytesIO

# Inicializar variáveis de sessão
if 'analysis_completed' not in st.session_state:
    st.session_state.analysis_completed = False
if 'analysis_result' not in st.session_state:
    st.session_state.analysis_result = None
if 'report_data' not in st.session_state:
    st.session_state.report_data = None

# Função para exportar o relatório (Excel e PDF)
def exportar_relatorio_comparativo(df_comparativo):
    """Exporta o relatório comparativo para Excel e PDF"""
    # Exportação para Excel
    output_excel = BytesIO()
    df_comparativo.to_excel(output_excel, index=False)
    output_excel.seek(0)
    b64_excel = base64.b64encode(output_excel.read()).decode()
    href_excel = f'<a href="data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64,{b64_excel}" download="relatorio_comparativo.xlsx">📥 Baixar Excel</a>'
    st.markdown(href_excel, unsafe_allow_html=True)
    
    # Exportação para PDF
    try:
        from fpdf import FPDF
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=12)
        pdf.cell(200, 10, txt="Relatório Comparativo de Propostas", ln=True, align='C')
        pdf.ln(10)
        colunas = df_comparativo.columns.tolist()
        for col in colunas:
            pdf.cell(40, 10, col, border=1)
        pdf.ln()
        for i, row in df_comparativo.iterrows():
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

# Função de exibição das tabelas
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
        st.dataframe(mapa_df, use_container_width=True, hide_index=True)
        st.info(f"📊 Total de itens no mapa: {len(mapa_df)}")
    else:
        st.warning("⚠️ Mapa de concorrência não encontrado ou vazio.")
    
    # Exibe Propostas Separadas
    st.subheader("📄 PROPOSTAS ANALISADAS")
    
    if propostas_dfs and len(propostas_dfs) > 0:
        # Cria abas para cada proposta
        for i, proposta_df in enumerate(propostas_dfs):
            st.write(f"**Proposta {i+1}**")
            if proposta_df is not None and not proposta_df.empty:
                st.dataframe(proposta_df, use_container_width=True, hide_index=True)
            else:
                st.warning("⚠️ Dados da proposta não puderam ser processados.")
    else:
        st.warning("⚠️ Nenhuma proposta encontrada.")

# Upload de arquivos com feedback
st.markdown("### 📁 Importação de Documentos")
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
            result = extract_structured_data_real(uploaded_files)
            if 'erro' in result:
                st.error(f"❌ Erro: {result.get('mensagem')}")
            else:
                st.session_state.analysis_result = result
                st.success("✅ Extração concluída com sucesso!")
                # Exibe as tabelas estruturadas
                exibir_tabelas_estruturadas()

    # Exibe relatório comparativo se disponível
    if st.session_state.analysis_result and "comparativo_df" in st.session_state.analysis_result:
        st.markdown("### 📊 Relatório Comparativo")
        df_comparativo = st.session_state.analysis_result["comparativo_df"]
        st.dataframe(df_comparativo, use_container_width=True)
        exportar_relatorio_comparativo(df_comparativo)
