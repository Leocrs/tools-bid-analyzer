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
    def limit_text(text, max_chars=2000):
        return text[:max_chars] + "..." if len(text) > max_chars else text
    prompt = f"""
ANÁLISE REAL DE PROPOSTAS - TOOLS ENGENHARIA

Você recebeu documentos REAIS de:
- MAPA: {data['mapa_concorrencia']['nome_arquivo'] if data['mapa_concorrencia'] else 'Não fornecido'}
- FORNECEDORES: {', '.join([p['fornecedor'] for p in data['propostas']])}

TAREFA: Fazer comparação LADO A LADO entre os fornecedores identificados nos documentos.

EXTRAIA dos documentos e COMPARE, item a item, trazendo:
- Quantidade
- Modelo
- Valor unitário
- Valor total
- Forma de pagamento
- Proposta
- Fornecedor
- Especificação técnica
- Para cada item, destaque o fornecedor com o menor valor (Mix de melhor preço)

Organize o relatório em formato tabular ou cards, lado a lado, para facilitar a comparação visual.

Ao final, gere um resumo do "Mix de melhor preço", indicando para cada item o fornecedor ideal e o valor, e o total do mix.

RETORNE em JSON estruturado, com todos os campos encontrados nos documentos.

DADOS DOS DOCUMENTOS REAIS:
"""
    if data['mapa_concorrencia']:
        if data['mapa_concorrencia'].get('texto_completo'):
            prompt += f"\nMAPA DE CONCORRÊNCIA:\n{limit_text(data['mapa_concorrencia']['texto_completo'])}"
        elif data['mapa_concorrencia'].get('texto'):
            prompt += f"\nMAPA DE CONCORRÊNCIA:\n{limit_text(data['mapa_concorrencia']['texto'])}"
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
            temperature=0.0
        )
        content = response.choices[0].message.content
        json_start = content.find('{')
        json_end = content.rfind('}') + 1
        if json_start != -1 and json_end > json_start:
            json_str = content[json_start:json_end]
            return json.loads(json_str)
        else:
            return {"erro": "GPT não retornou JSON válido", "resposta_bruta": content}
    except Exception as exc:
        logger.error(f"Erro na análise OpenAI: {exc}")
        return {"erro": f"Erro ao processar análise com IA: {str(exc)}"}

def extract_data_from_excel(file, max_rows=50):
    pass  # Função placeholder
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

# Função global para importação
def comparar_propostas(mapa, propostas):
    """Compara propostas e gera estrutura para relatório colorido"""
    itens_mapa = mapa.get("itens", [])
    resultado = []
    for item_nome in itens_mapa:
        fornecedores = {}
        for proposta in propostas:
            nome_forn = proposta.get("fornecedor", proposta.get("nome_arquivo", "Proposta"))
            texto = proposta.get("texto_completo", "")
            valor = None
            if item_nome in texto:
                idx = texto.find(item_nome)
                trecho = texto[idx:idx+200]
                match = re.search(r"(R\$\s?)([\d\.,]+)", trecho)
                if match:
                    valor = float(match.group(2).replace(".","").replace(",","."))
            fornecedores[nome_forn] = {"valor": valor if valor else "-", "especificacao": item_nome}
        valores_validos = [(f, d["valor"]) for f, d in fornecedores.items() if isinstance(d["valor"], (int, float))]
        melhor = min(valores_validos, key=lambda x: x[1])[0] if valores_validos else None
        pior = max(valores_validos, key=lambda x: x[1])[0] if valores_validos else None
        diferenca = None
        recomendacao = ""
        if melhor and pior:
            diferenca = fornecedores[pior]["valor"] - fornecedores[melhor]["valor"]
            if diferenca > 0:
                if diferenca > 1000:
                    recomendacao = f"Grande diferença de preço entre fornecedores. Recomenda-se negociar com {melhor} para o item '{item_nome}' devido ao melhor preço."
                else:
                    recomendacao = f"{melhor} apresenta o melhor preço para o item '{item_nome}'. Recomenda-se priorizar este fornecedor."
            else:
                recomendacao = f"Os preços estão próximos entre os fornecedores para o item '{item_nome}'. Avalie outros critérios além do preço."
        else:
            recomendacao = f"Não foi possível comparar preços para o item '{item_nome}'. Verifique se os dados extraídos estão completos."
        resultado.append({
            "item": item_nome,
            "quantidade": "-",
            "fornecedores": fornecedores,
            "melhor_preco": melhor,
            "diferenca_valores": diferenca,
            "recomendacao": recomendacao
        })
    return resultado
