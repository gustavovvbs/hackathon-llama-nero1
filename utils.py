import PyPDF2
from io import StringIO
from pydantic import BaseModel, Field 
from langchain_core.prompts import ChatPromptTemplate 
from langchain_openai import ChatOpenAI
from llama_parse import LlamaParse 
import httpx 
from io import BytesIO 
import tempfile 
from dotenv import load_dotenv 
import os

load_dotenv()


async def process_pdf(pdf_url):
    async def download_pdf(url):
        async with httpx.AsyncClient() as client:
            response = await client.get(url)
            pdf_bytes = response.content 


        return pdf_bytes 

    async def download_pdf_to_tempfile(url):
        async with httpx.AsyncClient(follow_redirects=True) as client:
            response = await client.get(url)
            pdf_bytes = response.content 
            print(pdf_bytes[:100])


        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
            tmp_file.write(pdf_bytes)
            tmp_file_path = tmp_file.name 

        return tmp_file_path

    file_path = await download_pdf_to_tempfile(pdf_url)
    parser = LlamaParse()

    parsing_result = await parser.aload_data(file_path)

    llm = ChatOpenAI(
        model='gpt-4o-2024-08-06',
        temperature=0
    )

    class Transaction(BaseModel):
        """Extrai valores relevantes de um documento de extrato bancário de um usuário"""
        tipo: str = Field(description="Classificação da transferência", examples=["""Alimentação: Transações relacionadas à aquisição de alimentos e bebidas, seja para consumo doméstico ou em estabelecimentos comerciais, como supermercados, restaurantes, lanchonetes e serviços de entrega de refeições.

Transporte: Despesas associadas ao deslocamento, incluindo abastecimento de veículos, uso de transporte público, serviços de transporte por aplicativo, manutenção de automóveis e custos de estacionamento.

Moradia: Gastos vinculados à residência, abrangendo pagamentos de aluguel ou financiamento imobiliário, contas de serviços públicos (energia elétrica, água, gás), serviços de comunicação (internet, telefone) e despesas com manutenção ou reparos domésticos.

Saúde: Despesas destinadas ao bem-estar físico e mental, como planos de saúde, compra de medicamentos, consultas médicas, exames laboratoriais e terapias diversas.

Educação: Investimentos em formação e aprendizado, incluindo mensalidades escolares ou universitárias, cursos de aprimoramento, aquisição de materiais didáticos e livros.

Lazer e Entretenimento: Gastos relacionados a atividades recreativas e culturais, como ingressos para cinema, teatro, shows, viagens, assinaturas de serviços de streaming e academias.

Vestuário e Serviços de beleza: Compras de roupas, calçados, acessórios pessoais, serviços de spa, barbearias entre outros.

Despesas Financeiras: Custos associados a serviços financeiros, como juros, multas, tarifas bancárias e anuidades de cartões de crédito.

Transferência Pessoal: Transações realizadas entre contas de pessoas físicas, geralmente envolvendo transferências entre familiares, amigos ou conhecidos para fins pessoais, como empréstimos informais, presentes ou compartilhamento de despesas.

Presentes e Doações: Transações destinadas à aquisição de presentes para terceiros ou contribuições para instituições de caridade.

Investimentos e Poupança: Aplicações financeiras visando retorno futuro, como depósitos em poupança, investimentos em ações, títulos ou aportes em previdência privada.

Despesas com Animais de Estimação: Gastos com cuidados de pets, incluindo alimentação, consultas veterinárias e produtos ou serviços relacionados.

Outras Despesas: Demais gastos que não se enquadram nas categorias anteriores, como pagamento de impostos, taxas diversas, serviços domésticos e assinaturas variadas."""])
        
        data: str = Field(description="Data da transferência")
        entrada_ou_saida: str = Field(description="Se a transferência foi de entrada ou saída")
        valor: str = Field(description="Valor da transferencia")

    system_schema = """Você vai receber um documento em PDF com o extrato bancário de um usuario. Faça uma lista desse schema definido para representar todas as transações."""

    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", system_schema),
            ("human", "Extrato completo: {extrato}"),
        ]
    )

    llm_with_tools = llm.bind_tools([Transaction])
    chain_structured = prompt | llm_with_tools 

    def format_docs(docs):
        return "\n\n".join([doc.text for doc in docs])

    formatted_docs = format_docs(parsing_result)

    response = chain_structured.invoke({"extrato": formatted_docs})

    return response

