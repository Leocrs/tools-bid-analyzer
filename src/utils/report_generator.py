import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from datetime import datetime
import xlsxwriter
import io
import re
import json


class BIDReportGenerator:
    def __init__(self):
        self.analysis_data = {}
        self.charts = {}
        
    def extract_data_from_analysis(self, ai_analysis, files_info):
        """Extrai dados estruturados da análise da IA"""
        try:
            # Simula extração de dados da análise
            # Em produção, você pode usar regex ou parsing mais sofisticado
            data = {
                "resumo": {
                    "total_fornecedores": self._extract_number(ai_analysis, "fornecedores?"),
                    "total_itens": self._extract_number(ai_analysis, "itens?"),
                    "menor_valor_total": 0,
                    "maior_valor_total": 0,
                    "data_analise": datetime.now().strftime("%d/%m/%Y %H:%M")
                },
                "fornecedores": self._extract_suppliers_data(ai_analysis),
                "itens": self._extract_items_data(ai_analysis),
                "recomendacoes": self._extract_recommendations(ai_analysis)
            }
            return data
        except Exception as e:
            st.error(f"Erro ao extrair dados da análise: {e}")
            return self._get_sample_data()
    
    def _extract_number(self, text, pattern):
        """Extrai números do texto usando regex"""
        import re
        match = re.search(f'(\d+)\s*{pattern}', text, re.IGNORECASE)
        return int(match.group(1)) if match else 0
    
    def _extract_suppliers_data(self, analysis):
        """Extrai dados dos fornecedores da análise"""
        # Dados de exemplo - em produção, extrair da análise real
        return [
            {"nome": "Fornecedor A", "total_itens": 15, "valor_total": 125000, "score": 85},
            {"nome": "Fornecedor B", "total_itens": 12, "valor_total": 118000, "score": 92},
            {"nome": "Fornecedor C", "total_itens": 18, "valor_total": 135000, "score": 78}
        ]
    
    def _extract_items_data(self, analysis):
        """Extrai dados dos itens da análise"""
        return [
            {"item": "Concreto C25", "quantidade": 150, "melhor_preco": 320.50, "melhor_fornecedor": "Fornecedor B"},
            {"item": "Aço CA-50", "quantidade": 2500, "melhor_preco": 4.85, "melhor_fornecedor": "Fornecedor A"},
            {"item": "Tijolo Cerâmico", "quantidade": 5000, "melhor_preco": 0.65, "melhor_fornecedor": "Fornecedor C"}
        ]
    
    def _extract_recommendations(self, analysis):
        """Extrai recomendações da análise"""
        return [
            "Fornecedor B apresenta melhor custo-benefício geral",
            "Verificar disponibilidade de estoque do Fornecedor A para aço",
            "Negociar desconto por volume com Fornecedor C",
            "Solicitar garantia estendida para materiais cerâmicos"
        ]
    
    def _get_sample_data(self):
        """Dados de exemplo para demonstração"""
        return {
            "resumo": {
                "total_fornecedores": 3,
                "total_itens": 25,
                "menor_valor_total": 118000,
                "maior_valor_total": 135000,
                "data_analise": datetime.now().strftime("%d/%m/%Y %H:%M")
            },
            "fornecedores": self._extract_suppliers_data(""),
            "itens": self._extract_items_data(""),
            "recomendacoes": self._extract_recommendations("")
        }
    
    def generate_charts(self, data):
        """Gera gráficos para o relatório"""
        charts = {}
        
        # Gráfico de comparação de fornecedores
        df_fornecedores = pd.DataFrame(data["fornecedores"])
        
        fig_fornecedores = px.bar(
            df_fornecedores, 
            x="nome", 
            y="valor_total",
            title="Comparação de Valores por Fornecedor",
            color="score",
            color_continuous_scale="RdYlGn"
        )
        fig_fornecedores.update_layout(
            xaxis_title="Fornecedores",
            yaxis_title="Valor Total (R$)",
            showlegend=False
        )
        charts["fornecedores_valor"] = fig_fornecedores
        
        # Gráfico de score dos fornecedores
        fig_score = px.bar(
            df_fornecedores,
            x="nome",
            y="score",
            title="Score de Avaliação dos Fornecedores",
            color="score",
            color_continuous_scale="RdYlGn"
        )
        fig_score.update_layout(
            xaxis_title="Fornecedores",
            yaxis_title="Score (%)",
            showlegend=False
        )
        charts["fornecedores_score"] = fig_score
        
        # Gráfico de distribuição de itens
        fig_itens = px.pie(
            df_fornecedores,
            values="total_itens",
            names="nome",
            title="Distribuição de Itens por Fornecedor"
        )
        charts["distribuicao_itens"] = fig_itens
        
        return charts
    
    def display_report_preview(self, data, charts):
        """Exibe prévia do relatório na tela"""
        st.markdown("## 📊 Relatório de Análise de BID")
        
        # Resumo executivo
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total de Fornecedores", data["resumo"]["total_fornecedores"])
        with col2:
            st.metric("Total de Itens", data["resumo"]["total_itens"])
        with col3:
            st.metric("Menor Valor Total", f"R$ {data['resumo']['menor_valor_total']:,.2f}")
        with col4:
            st.metric("Maior Valor Total", f"R$ {data['resumo']['maior_valor_total']:,.2f}")
        
        # Gráficos
        col1, col2 = st.columns(2)
        with col1:
            st.plotly_chart(charts["fornecedores_valor"], use_container_width=True)
        with col2:
            st.plotly_chart(charts["fornecedores_score"], use_container_width=True)
        
        st.plotly_chart(charts["distribuicao_itens"], use_container_width=True)
        
        # Tabela de fornecedores
        st.markdown("### 📋 Resumo dos Fornecedores")
        df_fornecedores = pd.DataFrame(data["fornecedores"])
        df_fornecedores["valor_total"] = df_fornecedores["valor_total"].apply(lambda x: f"R$ {x:,.2f}")
        df_fornecedores["score"] = df_fornecedores["score"].apply(lambda x: f"{x}%")
        st.dataframe(df_fornecedores, use_container_width=True)
        
        # Melhores preços por item
        st.markdown("### 💰 Melhores Preços por Item")
        df_itens = pd.DataFrame(data["itens"])
        df_itens["melhor_preco"] = df_itens["melhor_preco"].apply(lambda x: f"R$ {x:,.2f}")
        st.dataframe(df_itens, use_container_width=True)
        
        # Recomendações
        st.markdown("### 🎯 Recomendações")
        for i, rec in enumerate(data["recomendacoes"], 1):
            st.markdown(f"{i}. {rec}")
    
    def generate_excel_report(self, data, charts):
        """Gera relatório em Excel"""
        try:
            output = io.BytesIO()
            workbook = xlsxwriter.Workbook(output, {'in_memory': True})
            
            # Formatos
            title_format = workbook.add_format({
                'bold': True,
                'font_size': 16,
                'align': 'center',
                'valign': 'vcenter',
                'bg_color': '#009e3c',
                'font_color': 'white'
            })
            
            header_format = workbook.add_format({
                'bold': True,
                'bg_color': '#f0f8f0',
                'border': 1
            })
            
            cell_format = workbook.add_format({
                'border': 1,
                'align': 'center'
            })
            
            currency_format = workbook.add_format({
                'num_format': 'R$ #,##0.00',
                'border': 1,
                'align': 'right'
            })
            
            # Planilha Principal
            worksheet = workbook.add_worksheet('Relatório BID')
            
            # Título
            worksheet.merge_range('A1:F1', 'RELATÓRIO DE ANÁLISE DE BID - TOOLS ENGENHARIA', title_format)
            worksheet.write('A2', f'Data: {data["resumo"]["data_analise"]}')
            
            # Resumo
            row = 4
            worksheet.write(row, 0, 'RESUMO EXECUTIVO', header_format)
            worksheet.write(row + 1, 0, 'Total de Fornecedores:', cell_format)
            worksheet.write(row + 1, 1, data["resumo"]["total_fornecedores"], cell_format)
            worksheet.write(row + 2, 0, 'Total de Itens:', cell_format)
            worksheet.write(row + 2, 1, data["resumo"]["total_itens"], cell_format)
            
            # Fornecedores
            row = 8
            worksheet.write(row, 0, 'FORNECEDORES', header_format)
            headers = ['Nome', 'Total Itens', 'Valor Total', 'Score']
            for col, header in enumerate(headers):
                worksheet.write(row + 1, col, header, header_format)
            
            for i, fornecedor in enumerate(data["fornecedores"]):
                worksheet.write(row + 2 + i, 0, fornecedor["nome"], cell_format)
                worksheet.write(row + 2 + i, 1, fornecedor["total_itens"], cell_format)
                worksheet.write(row + 2 + i, 2, fornecedor["valor_total"], currency_format)
                worksheet.write(row + 2 + i, 3, f'{fornecedor["score"]}%', cell_format)
            
            # Itens
            row = 14
            worksheet.write(row, 0, 'MELHORES PREÇOS POR ITEM', header_format)
            headers = ['Item', 'Quantidade', 'Melhor Preço', 'Melhor Fornecedor']
            for col, header in enumerate(headers):
                worksheet.write(row + 1, col, header, header_format)
            
            for i, item in enumerate(data["itens"]):
                worksheet.write(row + 2 + i, 0, item["item"], cell_format)
                worksheet.write(row + 2 + i, 1, item["quantidade"], cell_format)
                worksheet.write(row + 2 + i, 2, item["melhor_preco"], currency_format)
                worksheet.write(row + 2 + i, 3, item["melhor_fornecedor"], cell_format)
            
            # Recomendações
            row = 20
            worksheet.write(row, 0, 'RECOMENDAÇÕES', header_format)
            for i, rec in enumerate(data["recomendacoes"]):
                worksheet.write(row + 1 + i, 0, f'{i+1}. {rec}')
            
            # Ajustar largura das colunas
            worksheet.set_column('A:A', 25)
            worksheet.set_column('B:B', 15)
            worksheet.set_column('C:C', 20)
            worksheet.set_column('D:D', 20)
            
            workbook.close()
            output.seek(0)
            return output
            
        except Exception as e:
            st.error(f"Erro ao gerar Excel: {e}")
            return None
    
    def generate_pdf_report(self, data, charts):
        """Gera relatório em PDF"""
        try:
            buffer = io.BytesIO()
            doc = SimpleDocTemplate(buffer, pagesize=A4)
            styles = getSampleStyleSheet()
            story = []
            
            # Estilo customizado
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontSize=18,
                spaceAfter=30,
                alignment=1,  # Centro
                textColor=colors.HexColor('#009e3c')
            )
            
            # Título
            story.append(Paragraph("RELATÓRIO DE ANÁLISE DE BID", title_style))
            story.append(Paragraph("TOOLS ENGENHARIA", styles['Heading2']))
            story.append(Spacer(1, 12))
            story.append(Paragraph(f"Data: {data['resumo']['data_analise']}", styles['Normal']))
            story.append(Spacer(1, 20))
            
            # Resumo Executivo
            story.append(Paragraph("RESUMO EXECUTIVO", styles['Heading2']))
            resumo_data = [
                ['Métrica', 'Valor'],
                ['Total de Fornecedores', str(data["resumo"]["total_fornecedores"])],
                ['Total de Itens', str(data["resumo"]["total_itens"])],
                ['Menor Valor Total', f'R$ {data["resumo"]["menor_valor_total"]:,.2f}'],
                ['Maior Valor Total', f'R$ {data["resumo"]["maior_valor_total"]:,.2f}']
            ]
            
            resumo_table = Table(resumo_data)
            resumo_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#009e3c')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 12),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            story.append(resumo_table)
            story.append(Spacer(1, 20))
            
            # Fornecedores
            story.append(Paragraph("ANÁLISE DE FORNECEDORES", styles['Heading2']))
            fornecedores_data = [['Nome', 'Total Itens', 'Valor Total', 'Score']]
            for f in data["fornecedores"]:
                fornecedores_data.append([
                    f["nome"],
                    str(f["total_itens"]),
                    f'R$ {f["valor_total"]:,.2f}',
                    f'{f["score"]}%'
                ])
            
            fornecedores_table = Table(fornecedores_data)
            fornecedores_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#009e3c')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            story.append(fornecedores_table)
            story.append(Spacer(1, 20))
            
            # Recomendações
            story.append(Paragraph("RECOMENDAÇÕES", styles['Heading2']))
            for i, rec in enumerate(data["recomendacoes"], 1):
                story.append(Paragraph(f"{i}. {rec}", styles['Normal']))
                story.append(Spacer(1, 6))
            
            doc.build(story)
            buffer.seek(0)
            return buffer
            
        except Exception as e:
            st.error(f"Erro ao gerar PDF: {e}")
            return None