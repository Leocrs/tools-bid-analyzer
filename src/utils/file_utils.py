import pandas as pd
import PyPDF2
import json
import openai
import os
from dotenv import load_dotenv
from pathlib import Path
import logging
import re

# Carrega variáveis de ambiente
load_dotenv()

# Configuração de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuração OpenAI
openai.api_key = os.getenv("OPENAI_API_KEY")

def extract_text_from_pdf_complete(file):
    """Extrai TODO o texto do PDF para análise completa"""
    try:
        file.seek(0)
        reader = PyPDF2.PdfReader(file)
        text = ""
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
        return text
    except Exception as e:
        logger.error(f"Erro ao extrair texto do PDF: {e}")
        return ""

def identify_supplier_from_filename(filename):
    """Identifica o fornecedor pelo nome do arquivo"""
    filename_lower = filename.lower()
    if "assistec" in filename_lower:
        return "ASSISTEC"
    elif "sulfrio" in filename_lower:
        return "SULFRIO"
    elif "mapa" in filename_lower:
        return "MAPA_CONCORRENCIA"
    else:
        # Tenta extrair nome da empresa do início do arquivo
        parts = filename.split(' - ')
        if len(parts) > 0:
            potential_company = parts[0].strip().upper()
            return potential_company
        return "FORNECEDOR_NAO_IDENTIFICADO"

def extract_values_from_text(text):
    """Extrai valores monetários do texto"""
    # Padrões para valores em reais
    patterns = [
        r'R\$\s*([\d.,]+)',
        r'(\d{1,3}(?:\.\d{3})*(?:,\d{2})?)',
        r'TOTAL[:\s]*([\d.,]+)',
        r'VALOR[:\s]*([\d.,]+)'
    ]
    
    values = []
    for pattern in patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        values.extend(matches)
    
    return values

def extract_items_from_text(text):
    """Extrai itens/equipamentos do texto"""
    # Padrões comuns para equipamentos de ar condicionado
    patterns = [
        r'UE-\d+[A-Z]?\s*-[^-\n]+',  # Padrão UE-01A - DESCRIÇÃO
        r'SPLIT\s+\d+[.,]?\d*\s*BTU[/H]*',
        r'CASSETE\s+\d+[.,]?\d*\s*BTU[/H]*',
        r'HI\s*WALL\s+\d+[.,]?\d*\s*BTU[/H]*',
        r'DUTO\s+\d+[.,]?\d*\s*BTU[/H]*'
    ]
    
    items = []
    for pattern in patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        items.extend(matches)
    
    return list(set(items))  # Remove duplicatas

def extract_structured_data_real(files):
    """Extrai dados REAIS e estruturados dos arquivos"""
    data = {
        "mapa_concorrencia": None,
        "propostas": []
    }
    
    for file in files:
        supplier = identify_supplier_from_filename(file.name)
        
        # Determina se é Excel ou PDF
        ext = Path(file.name).suffix.lower()
        
        if ext in [".xlsx", ".xls"]:
            # Para Excel, extrai como DataFrame
            try:
                file.seek(0)
                df = pd.read_excel(file)
                content = {
                    "tipo": "excel",
                    "dataframe": df,
                    "texto": df.to_string(),
                    "valores": extract_values_from_text(df.to_string()),
                    "itens": extract_items_from_text(df.to_string())
                }
            except Exception as e:
                logger.error(f"Erro ao processar Excel {file.name}: {e}")
                content = {"tipo": "excel", "erro": str(e)}
        else:
            # Para PDF, extrai texto completo
            full_text = extract_text_from_pdf_complete(file)
            content = {
                "tipo": "pdf",
                "texto_completo": full_text,
                "valores": extract_values_from_text(full_text),
                "itens": extract_items_from_text(full_text)
            }
        
        if supplier == "MAPA_CONCORRENCIA":
            data["mapa_concorrencia"] = {
                "nome_arquivo": file.name,
                "fornecedor": supplier,
                **content
            }
        else:
            data["propostas"].append({
                "nome_arquivo": file.name,
                "fornecedor": supplier,
                **content
            })
    
    return data

def analyze_with_openai_real(data):
    """Análise REAL dos documentos com comparação lado a lado"""
    
    # Prepara resumo dos fornecedores identificados
    fornecedores = [p['fornecedor'] for p in data['propostas']]
    
    # Limita o texto para não exceder tokens
    def limit_text(text, max_chars=2000):
        return text[:max_chars] + "..." if len(text) > max_chars else text
    
    # Monta o prompt para análise REAL
    prompt = f"""
ANÁLISE REAL DE PROPOSTAS - TOOLS ENGENHARIA

Você recebeu documentos REAIS de:
- MAPA: {data['mapa_concorrencia']['nome_arquivo'] if data['mapa_concorrencia'] else 'Não fornecido'}
- FORNECEDORES: {', '.join(fornecedores)}

TAREFA: Fazer comparação LADO A LADO entre os fornecedores identificados nos documentos.

EXTRAIA dos documentos e COMPARE:
1. Itens/equipamentos específicos de cada proposta
2. Valores unitários e totais REAIS
3. Marcas/especificações técnicas mencionadas
4. Quantidades de cada item
5. Condições comerciais (prazos, pagamento)

RETORNE em JSON com dados EXTRAÍDOS dos documentos:
{{
  "comparacao_lado_a_lado": [
    {{
      "item": "nome_equipamento_extraido_do_documento",
      "quantidade": "quantidade_real_extraida",
      "fornecedores": {{
        "{fornecedores[0] if fornecedores else 'FORNECEDOR1'}": {{"valor": "valor_extraido", "especificacao": "spec_extraida"}},
        "{fornecedores[1] if len(fornecedores) > 1 else 'FORNECEDOR2'}": {{"valor": "valor_extraido", "especificacao": "spec_extraida"}}
      }},
      "melhor_preco": "fornecedor_com_menor_valor",
      "diferenca_valores": "diferenca_calculada"
    }}
  ],
  "resumo_fornecedores": {{
    "{fornecedores[0] if fornecedores else 'FORNECEDOR1'}": {{"valor_total_proposta": "valor_extraido", "total_itens": "numero_itens"}},
    "{fornecedores[1] if len(fornecedores) > 1 else 'FORNECEDOR2'}": {{"valor_total_proposta": "valor_extraido", "total_itens": "numero_itens"}}
  }},
  "analise_tecnica": [
    {{
      "criterio": "criterio_avaliado",
      "resultado": "conforme_ou_nao_conforme",
      "detalhes": "detalhes_especificos_encontrados"
    }}
  ],
  "recomendacoes": [
    "Recomendação baseada nos dados REAIS encontrados nos documentos"
  ]
}}

DADOS DOS DOCUMENTOS REAIS:
"""
    
    # Adiciona dados do mapa se existir
    if data['mapa_concorrencia']:
        if data['mapa_concorrencia'].get('texto_completo'):
            prompt += f"\nMAPA DE CONCORRÊNCIA:\n{limit_text(data['mapa_concorrencia']['texto_completo'])}"
        elif data['mapa_concorrencia'].get('texto'):
            prompt += f"\nMAPA DE CONCORRÊNCIA:\n{limit_text(data['mapa_concorrencia']['texto'])}"
    
    # Adiciona dados das propostas
    for proposta in data['propostas']:
        prompt += f"\n\n{proposta['fornecedor']} ({proposta['nome_arquivo']}):"
        if proposta.get('texto_completo'):
            prompt += f"\n{limit_text(proposta['texto_completo'])}"
        elif proposta.get('texto'):
            prompt += f"\n{limit_text(proposta['texto'])}"

    try:
        response = openai.chat.completions.create(
            model="gpt-4",
            messages=[
                {
                    "role": "system", 
                    "content": "Você é um analista de suprimentos experiente. Extraia dados REAIS dos documentos fornecidos. NÃO invente valores ou informações. Analise apenas o que está escrito nos documentos. Responda APENAS com JSON válido."
                },
                {"role": "user", "content": prompt}
            ],
            max_tokens=2500,
            temperature=0.0  # Temperatura 0 para máxima precisão
        )
        
        content = response.choices[0].message.content
        json_start = content.find('{')
        json_end = content.rfind('}') + 1
        
        if json_start != -1 and json_end > json_start:
            json_str = content[json_start:json_end]
            return json.loads(json_str)
        else:
            return {"erro": "GPT não retornou JSON válido", "resposta_bruta": content}
            
    except Exception as e:
        logger.error(f"Erro na análise OpenAI: {e}")
        return {"erro": f"Erro ao processar análise com IA: {str(e)}"}

def handle_uploaded_files(files):
    """Processa arquivos e retorna dados extraídos para revisão antes da IA"""
    if not files:
        return {
            "success": False,
            "message": "Nenhum arquivo enviado",
            "validations": [],
            "ai_analysis": "",
            "structured_data": {}
        }
    validations = []
    mapa_concorrencia = None
    propostas = []
    for file in files:
        ext = Path(file.name).suffix.lower()
        file.seek(0)
        if ext in [".xlsx", ".xls"]:
            # Considera o primeiro Excel como mapa de concorrência
            df = pd.read_excel(file)
            texto = df.to_string()
            mapa_concorrencia = {
                "nome_arquivo": file.name,
                "texto_completo": texto
            }
            validations.append(f"✅ Excel extraído: {file.name}")
        elif ext == ".pdf":
            try:
                from PyPDF2 import PdfReader
                reader = PdfReader(file)
                texto = "\n".join(page.extract_text() or "" for page in reader.pages)
            except Exception:
                texto = "Erro ao extrair texto do PDF."
            propostas.append({
                "nome_arquivo": file.name,
                "fornecedor": Path(file.name).stem,
                "texto_completo": texto
            })
            validations.append(f"✅ PDF extraído: {file.name}")
        else:
            validations.append(f"⚠️ Tipo de arquivo não suportado: {file.name}")

    structured_data = {
        "mapa_concorrencia": mapa_concorrencia,
        "propostas": propostas
    }
    ai_result = ""  # Só envia para IA após revisão

    return {
        "success": True,
        "message": "Arquivos extraídos para revisão!",
        "validations": validations,
        "ai_analysis": ai_result,
        "structured_data": structured_data
    }

# Mantém as funções antigas para compatibilidade
def extract_text_from_pdf(file, max_chars=4000):
    """Função mantida para compatibilidade - usa a versão completa"""
    return extract_text_from_pdf_complete(file)[:max_chars]

def extract_data_from_excel(file, max_rows=50):
    """Extrai dados estruturados de Excel com limite de linhas"""
    try:
        file.seek(0)
        df = pd.read_excel(file)
        df = df.head(max_rows)
        return df.to_dict(orient="records")
    except Exception as e:
        logger.error(f"Erro ao extrair dados do Excel: {e}")
        return []

def extract_structured_data(files):
    """Função mantida para compatibilidade"""
    return extract_structured_data_real(files)

def analyze_with_openai_structured(data):
    """
    Função de análise IA estruturada: compara dados extraídos e gera relatório técnico lado a lado.
    Utiliza o mesmo fluxo da função real, mas pode ser adaptada para customizações futuras.
    """
    resultado_ia = analyze_with_openai_real(data)
    # Aqui, pode-se adicionar pós-processamento ou formatação extra se necessário
    return resultado_ia
