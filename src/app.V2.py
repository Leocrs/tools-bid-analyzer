import io
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
st.image("utils/Logo Verde.png", width=180)
st.markdown('<h3 style="margin-top: 0px; margin-bottom: 0px; color: #0e938e; font-weight: 600;">Agente de Suprimentos - Análise de BID</h3>', unsafe_allow_html=True)
st.markdown('</div>', unsafe_allow_html=True)
st.markdown('<div style="margin-top: 32px;"></div>', unsafe_allow_html=True)

# Instruções do processo de análise
st.markdown("""
### 📝 Etapas do Processo de Análise

**Primeira Parte:**  
Avaliar se o mapa em Excel ou PDF está igual às propostas e se as propostas estão equalizadas.

**Segunda Etapa:**  
Avaliar se as propostas estão aderentes ao projeto.

**Terceira Etapa:**  
Montar uma base histórica com serviços já contratados para servir como referência.

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

        # Exibe texto extraído dos arquivos para revisão
        st.markdown("### 📄 Texto extraído dos Documentos (pré-IA)")
        # Mapa de concorrência
        mapa = st.session_state.analysis_result.get("mapa_concorrencia")
        if not isinstance(mapa, dict):
            mapa = {}
        if mapa.get("texto_completo"):
            st.markdown(f"**{mapa.get('nome_arquivo', 'Mapa de Concorrência')}**")
            st.text((mapa["texto_completo"] or "")[:2000])
        # Propostas
        for proposta in st.session_state.analysis_result.get("propostas", []):
            st.markdown(f"**{proposta.get('nome_arquivo', 'Proposta')}**")
            st.text((proposta.get("texto_completo") or "")[:2000])

        st.info("Revise os dados extraídos acima. Se estiverem legíveis e completos, clique abaixo para análise com IA.")

        # Camada de debug visual
        st.markdown("---")
        st.markdown("#### � Debug IA - Status e Dados")
    if st.session_state.analysis_result is not None:
        st.write("Dados enviados para IA:", st.session_state.analysis_result)
    else:
        st.write("Nenhum dado extraído ainda.")

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
                st.markdown("### 📊 Relatório Técnico Comparativo (Colorido)")
                st.markdown("#### Comparação Lado a Lado dos Itens")
                for item, mix_item in zip(comparacao['resultado'], comparacao['mix_melhor_preco']):
                    st.markdown(f"**{item.get('item','Item')}** | Quantidade: {item.get('quantidade','-')}")
                    fornecedores = item.get("fornecedores", {})
                    melhor = item.get("melhor_preco", "")
                    valores = [(f, fornecedores[f]["valor"]) for f in fornecedores if isinstance(fornecedores[f]["valor"], (int, float))]
                    pior = max(valores, key=lambda x: x[1])[0] if valores else None
                    cols = st.columns(len(fornecedores)+1)
                    for idx, (fornecedor, dados) in enumerate(fornecedores.items()):
                        valor = dados.get("valor", "-")
                        especificacao = dados.get("especificacao", "-")
                        cor = "#009e3c" if fornecedor == melhor else ("#d32f2f" if fornecedor == pior else "#f8f9fa")
                        if isinstance(valor, (int, float)):
                            valor_fmt = f"{valor:,.2f}".replace(",", ".").replace(".", ",", 1)
                        else:
                            valor_fmt = str(valor)
                        with cols[idx]:
                            st.markdown(f"<div style='background:{cor};padding:10px;border-radius:8px;color:{'white' if cor in ['#009e3c','#d32f2f'] else 'black'}'>"
                                        f"<b>{fornecedor}</b><br>"
                                        f"<b>Valor:</b> R$ {valor_fmt}<br>"
                                        f"<b>Especificação:</b> {especificacao}"
                                        "</div>", unsafe_allow_html=True)
                    # Coluna extra: melhor fornecedor do mix
                    with cols[-1]:
                        mix_forn = mix_item.get('melhor_fornecedor', '-')
                        mix_valor = mix_item.get('melhor_valor', '-')
                        if isinstance(mix_valor, (int, float)):
                            mix_valor_fmt = f"{mix_valor:,.2f}".replace(",", ".").replace(".", ",", 1)
                        else:
                            mix_valor_fmt = str(mix_valor)
                        st.markdown(f"<div style='background:#e3fcec;padding:10px;border-radius:8px;color:#333'>"
                                    f"<b>Melhor Fornecedor</b><br>"
                                    f"<b>{mix_forn}</b><br>"
                                    f"<b>Valor:</b> R$ {mix_valor_fmt}"
                                    "</div>", unsafe_allow_html=True)
                    diferenca = item.get('diferenca_valores','-')
                    if isinstance(diferenca, (int, float)):
                        diferenca_fmt = f"{diferenca:,.2f}".replace(",", ".").replace(".", ",", 1)
                    else:
                        diferenca_fmt = str(diferenca)
                    st.markdown(f"<b>Melhor Preço:</b> <span style='color:#009e3c'>{melhor}</span> | <b>Pior Preço:</b> <span style='color:#d32f2f'>{pior}</span> | <b>Diferença:</b> R$ {diferenca_fmt}", unsafe_allow_html=True)
                    recomendacao = item.get('recomendacao', None)
                    if recomendacao:
                        st.markdown(f"<div style='background:#e3fcec;padding:8px;border-radius:6px;margin-top:4px;margin-bottom:4px;color:#333'><b>Sugestão:</b> {recomendacao}</div>", unsafe_allow_html=True)
                    st.markdown("---")
                # Exibe o mix de melhor preço geral
                st.markdown("#### 🏆 Mix de Melhor Preço por Item")
                st.table([{ 'Item': m['item'], 'Melhor Fornecedor': m['melhor_fornecedor'], 'Valor': m['melhor_valor'] } for m in comparacao['mix_melhor_preco']])
                # Resumo final: ranking dos fornecedores pelo valor total
                st.markdown("#### 🏅 Ranking dos Fornecedores pelo Valor Total")
                ranking = {}
                for item in comparacao['resultado']:
                    for f, d in item['fornecedores'].items():
                        if isinstance(d['valor'], (int, float)):
                            ranking[f] = ranking.get(f, 0) + d['valor']
                ranking_ord = sorted(ranking.items(), key=lambda x: x[1])
                st.table([{ 'Fornecedor': f, 'Valor Total': v } for f, v in ranking_ord])
                # Exibe condições de pagamento e descontos se existirem
                st.markdown("#### 💳 Condições de Pagamento e Descontos")
                for proposta in propostas:
                    cond = proposta.get('texto_completo','')
                    st.markdown(f"<div style='background:#f4f4f4;padding:8px;border-radius:6px;margin-bottom:4px;color:#333'><b>{proposta.get('fornecedor',proposta.get('nome_arquivo','Proposta'))}</b><br>{cond}</div>", unsafe_allow_html=True)
            else:
                st.error(comparacao[0].get('mensagem', 'Erro na análise comparativa.'))
    if "analysis_result_ia" in st.session_state:
        st.write("Resultado IA:", st.session_state.analysis_result_ia)

        # Botão para enviar para IA após revisão
        if st.button("🚀 Analisar com IA"):
            with st.spinner("🤖 Realizando análise com IA..."):
                result_ia = analyze_with_openai_structured(st.session_state.analysis_result)
                st.session_state.analysis_result_ia = result_ia

        # Exibe resultado da IA se já foi gerado
        if "analysis_result_ia" in st.session_state:
            ia_result = st.session_state.analysis_result_ia
            if isinstance(ia_result, dict):
                st.success("✅ Análise da IA concluída!")
                st.markdown("### 📊 Relatório Técnico gerado pela IA (OpenAI)")

            # 1. Tabela comparativa dos itens
            st.markdown("#### Comparação Lado a Lado dos Itens")
            comparacao = ia_result.get("comparacao_lado_a_lado", [])
            if comparacao:
                for item in comparacao:
                    st.markdown(f"**{item.get('item','Item')}** | Quantidade: {item.get('quantidade','-')}")
                    fornecedores = item.get("fornecedores", {})
                    melhor = item.get("melhor_preco", "")
                    # Descobre o pior valor
                    valores = [(f, fornecedores[f]["valor"]) for f in fornecedores if "valor" in fornecedores[f]]
                    if valores:
                        pior = max(valores, key=lambda x: x[1])[0]
                    else:
                        pior = None
                    cols = st.columns(len(fornecedores))
                    for idx, (fornecedor, dados) in enumerate(fornecedores.items()):
                        valor = dados.get("valor", "-")
                        especificacao = dados.get("especificacao", "-")
                        cor = "#009e3c" if fornecedor == melhor else ("#d32f2f" if fornecedor == pior else "#f8f9fa")
                        # Formata valor apenas se for numérico
                        if isinstance(valor, (int, float)):
                            valor_fmt = f"{valor:,.2f}".replace(",", ".").replace(".", ",", 1)  # Formato brasileiro
                        else:
                            valor_fmt = str(valor)
                        with cols[idx]:
                            st.markdown(f"<div style='background:{cor};padding:10px;border-radius:8px;color:{'white' if cor in ['#009e3c','#d32f2f'] else 'black'}'>"
                                        f"<b>{fornecedor}</b><br>"
                                        f"<b>Valor:</b> R$ {valor_fmt}<br>"
                                        f"<b>Especificação:</b> {especificacao}"
                                        "</div>", unsafe_allow_html=True)
                    diferenca = item.get('diferenca_valores','-')
                    if isinstance(diferenca, (int, float)):
                        diferenca_fmt = f"{diferenca:,.2f}".replace(",", ".").replace(".", ",", 1)
                    else:
                        diferenca_fmt = str(diferenca)
                    st.markdown(f"<b>Melhor Preço:</b> <span style='color:#009e3c'>{melhor}</span> | <b>Pior Preço:</b> <span style='color:#d32f2f'>{pior}</span> | <b>Diferença:</b> R$ {diferenca_fmt}", unsafe_allow_html=True)
                    st.markdown("---")

            # 2. Resumo dos fornecedores
            st.markdown("#### Resumo dos Fornecedores")
            resumo = ia_result.get("resumo_fornecedores", {})
            if resumo:
                cols = st.columns(len(resumo))
                for idx, (fornecedor, dados) in enumerate(resumo.items()):
                    valor_total = dados.get("valor_total_proposta", "-")
                    total_itens = dados.get("total_itens", "-")
                    with cols[idx]:
                        st.markdown(f"<div style='background:#f8f9fa;padding:10px;border-radius:8px;border:1px solid #dee2e6'>"
                                    f"<b>{fornecedor}</b><br>"
                                    f"<b>Valor Total:</b> {valor_total}<br>"
                                    f"<b>Total de Itens:</b> {total_itens}"
                                    "</div>", unsafe_allow_html=True)

            # 3. Análise técnica
            st.markdown("#### Análise Técnica")
            analise = ia_result.get("analise_tecnica", [])
            if analise:
                for criterio in analise:
                    st.markdown(f"- <b>{criterio.get('criterio','')}</b>: {criterio.get('resultado','')}<br><i>{criterio.get('detalhes','')}</i>", unsafe_allow_html=True)

            # 4. Recomendações
            st.markdown("#### Recomendações da IA")
            recomendacoes = ia_result.get("recomendacoes", [])
            for rec in recomendacoes:
                st.markdown(f"<div style='background:#009e3c;color:white;padding:10px;border-radius:8px;margin-bottom:8px'><b>{rec}</b></div>", unsafe_allow_html=True)

            # 5. Botões de exportação
            st.markdown("---")
            st.markdown("### Exportar Relatório")
            col1, col2 = st.columns(2)
            # Excel
            with col1:
                if st.button("📥 Exportar para Excel"):
                    df = pd.DataFrame([{
                        "Item": i.get("item",""),
                        "Quantidade": i.get("quantidade",""),
                        **{f"Valor {f}": d.get("valor","") for f, d in i.get("fornecedores",{}).items()},
                        **{f"Especificação {f}": d.get("especificacao","") for f, d in i.get("fornecedores",{}).items()},
                        "Melhor Preço": i.get("melhor_preco",""),
                        "Pior Preço": max(i.get("fornecedores",{}), key=lambda x: i["fornecedores"][x].get("valor",0)) if i.get("fornecedores",{}) else "",
                        "Diferença": i.get("diferenca_valores","")
                    } for i in ia_result.get("comparacao_lado_a_lado",[])])
                    output = io.BytesIO()
                    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                        df.to_excel(writer, index=False, sheet_name='Comparativo')
                    output.seek(0)
                    st.download_button(
                        label="Baixar Excel",
                        data=output,
                        file_name="relatorio_comparativo.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
            # PDF
            with col2:
                if FPDF is None:
                    st.warning("Para exportar PDF, instale o pacote fpdf: pip install fpdf")
                elif st.button("📄 Exportar para PDF"):
                    pdf = FPDF()
                    pdf.add_page()
                    pdf.set_font("Arial", size=12)
                    pdf.cell(200, 10, txt="Relatório Técnico Comparativo", ln=True, align='C')
                    pdf.ln(5)
                    for i in ia_result.get("comparacao_lado_a_lado", []):
                        pdf.set_font("Arial", style="B", size=11)
                        pdf.cell(0, 8, txt=f"Item: {i.get('item','')} | Quantidade: {i.get('quantidade','')}", ln=True)
                        pdf.set_font("Arial", size=10)
                        for f, d in i.get("fornecedores",{}).items():
                            pdf.cell(0, 7, txt=f"Fornecedor: {f} | Valor: R$ {d.get('valor','')} | Especificação: {d.get('especificacao','')}", ln=True)
                        pdf.cell(0, 7, txt=f"Melhor Preço: {i.get('melhor_preco','')} | Diferença: R$ {i.get('diferenca_valores','')}", ln=True)
                        pdf.ln(2)
                    pdf.ln(5)
                    pdf.set_font("Arial", style="B", size=11)
                    pdf.cell(0, 8, txt="Recomendações:", ln=True)
                    pdf.set_font("Arial", size=10)
                    for rec in ia_result.get("recomendacoes", []):
                        pdf.multi_cell(0, 7, txt=rec)
                    pdf_output = pdf.output(dest='S').encode('latin1')
                    st.download_button(
                        label="Baixar PDF",
                        data=pdf_output,
                        file_name="relatorio_comparativo.pdf",
                        mime="application/pdf"
                    )
        else:
            st.error("❌ Erro na análise da IA")
            st.write(st.session_state.analysis_result_ia)

        st.session_state.analysis_completed = True

# Seção de Relatórios (só aparece após análise)

# Rodapé
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #666; font-size: 0.9rem;">
    <p>TOOLS Engenharia - Agente de Suprimentos com IA | Versão 2.1 | Ambiente de Produção</p>
</div>
""", unsafe_allow_html=True)
