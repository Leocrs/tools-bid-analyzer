import streamlit as st
from pathlib import Path
from utils.file_utils import handle_uploaded_files, validate_file_type
from utils.report_generator import BIDReportGenerator

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

# Header principal
st.markdown("""
<div class="main-header">
    <h1>🔨 TOOLS Engenharia</h1>
    <h3>Agente de Suprimentos - Análise de BID</h3>
</div>
""", unsafe_allow_html=True)

# Instruções do processo de análise
st.markdown("""
### 📝 Etapas do Processo de Análise

**Primeira Parte:**  
Avaliar se o mapa em Excel está igual às propostas e se as propostas estão equalizadas.

**Segunda Etapa:**  
Avaliar se as propostas estão aderentes ao projeto.

**Terceira Etapa:**  
Montar uma base histórica com serviços já contratados para servir como referência.

---
**🤖 IA utilizada:**  
OpenAI GPT-4 para análise automática e inteligente dos documentos de BID.
""")

# Inicializar variáveis de sessão
if 'analysis_completed' not in st.session_state:
    st.session_state.analysis_completed = False
if 'analysis_result' not in st.session_state:
    st.session_state.analysis_result = None
if 'report_data' not in st.session_state:
    st.session_state.report_data = None

# Upload de arquivos
st.markdown("### 📁 Importar Documentos")
uploaded_files = st.file_uploader(
    "Arraste e solte os arquivos aqui ou clique para selecionar (PDF ou Excel):",
    type=["pdf", "xlsx", "xls"],
    accept_multiple_files=True
)

if uploaded_files:
    st.markdown("#### Arquivos carregados:")
    for file in uploaded_files:
        st.write(f"- **{file.name}** ({file.type}, {file.size/1024:.1f} KB)")
    
    if st.button("🔍 Solicitar Análise com IA", type="primary"):
        with st.spinner("🤖 Processando documentos e realizando análise com IA..."):
            result = handle_uploaded_files(uploaded_files)
            st.session_state.analysis_result = result
            
            if result["success"]:
                st.success("✅ Análise concluída com sucesso!")
                
                # Exibe validações
                st.markdown("### 📋 Validação dos Documentos:")
                for validation in result["validations"]:
                    st.markdown(f"- {validation}")
                
                # Exibe análise da IA
                if result["ai_analysis"]:
                    st.markdown("### 🤖 Análise Inteligente:")
                    st.markdown(f'<div class="ai-analysis">{result["ai_analysis"]}</div>', unsafe_allow_html=True)
                
                # Gerar relatório
                st.session_state.analysis_completed = True
                
            else:
                st.error(result["message"])
                if result["validations"]:
                    st.markdown("### ⚠️ Detalhes:")
                    for validation in result["validations"]:
                        st.markdown(f"- {validation}")

# Seção de Relatórios (só aparece após análise)
if st.session_state.analysis_completed and st.session_state.analysis_result:
    st.markdown('<div class="report-section">', unsafe_allow_html=True)
    
    # Gerar dados do relatório
    if st.session_state.report_data is None:
        with st.spinner("📊 Gerando relatório..."):
            report_generator = BIDReportGenerator()
            files_info = [{"name": f.name, "size": len(f.getvalue())} for f in uploaded_files] if uploaded_files else []
            report_data = report_generator.extract_data_from_analysis(
                st.session_state.analysis_result["ai_analysis"], 
                files_info
            )
            charts = report_generator.generate_charts(report_data)
            st.session_state.report_data = {"data": report_data, "charts": charts}
    
    # Exibir relatório na tela
    report_generator = BIDReportGenerator()
    report_generator.display_report_preview(
        st.session_state.report_data["data"], 
        st.session_state.report_data["charts"]
    )
    
    # Botões de download
    st.markdown("### 📥 Exportar Relatório")
    col1, col2, col3 = st.columns([1, 1, 2])
    
    with col1:
        if st.button("📊 Exportar para Excel", type="secondary"):
            with st.spinner("Gerando Excel..."):
                excel_file = report_generator.generate_excel_report(
                    st.session_state.report_data["data"],
                    st.session_state.report_data["charts"]
                )
                if excel_file:
                    st.download_button(
                        label="⬇️ Download Excel",
                        data=excel_file,
                        file_name=f"relatorio_bid_{st.session_state.report_data['data']['resumo']['data_analise'].replace('/', '-').replace(' ', '_').replace(':', '-')}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
    
    with col2:
        if st.button("📄 Exportar para PDF", type="secondary"):
            with st.spinner("Gerando PDF..."):
                pdf_file = report_generator.generate_pdf_report(
                    st.session_state.report_data["data"],
                    st.session_state.report_data["charts"]
                )
                if pdf_file:
                    st.download_button(
                        label="⬇️ Download PDF",
                        data=pdf_file,
                        file_name=f"relatorio_bid_{st.session_state.report_data['data']['resumo']['data_analise'].replace('/', '-').replace(' ', '_').replace(':', '-')}.pdf",
                        mime="application/pdf"
                    )
    
    st.markdown('</div>', unsafe_allow_html=True)

# Rodapé
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #666; font-size: 0.9rem;">
    <p>TOOLS Engenharia - Agente de Suprimentos com IA | Versão 2.1 | Ambiente de Produção</p>
</div>
""", unsafe_allow_html=True)
