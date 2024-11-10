from langchain_groq import ChatGroq
from dotenv import load_dotenv
import os

from langchain_core.prompts import PromptTemplate, ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from operator import itemgetter

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")

template_agregador = """
Você é um especialista em análise financeira acessível. Com base nas transações fornecidas, sua tarefa é:

1. Calcular o total gasto em cada categoria, explicando de forma clara e visual.
2. Destacar as maiores despesas individuais e em quais categorias elas se concentram.
3. Apresentar médias de gastos diárias, semanais e mensais de maneira simples.
4. Identificar períodos de maior gasto e ajudar o usuário a entender esses picos.
5. Destacar hábitos financeiros positivos que o usuário pode manter.

Mantenha o tom leve e educativo, ajudando o usuário a se sentir no controle de suas finanças.

Dados das transações:
{transacoes}
"""

template_padroes = """
Como especialista em análise financeira, ajude o usuário a identificar seus hábitos financeiros ao:

1. Descobrir padrões de gastos recorrentes com explicações claras.
2. Entender ciclos de despesas, como aumento no início ou fim do mês.
3. Apontar categorias com tendências de aumento nos gastos e que precisam de atenção.
4. Mostrar como diferentes categorias de despesas estão conectadas.

Apresente as informações de forma clara e educativa para que o usuário veja valor em sua análise.

Dados agregados:
{dados_agregados}

"""

template_tendencias = """
CVocê é um especialista em projeções financeiras. Ajude o usuário a planejar melhor seus gastos ao:

1. Estimar gastos futuros em categorias importantes.
2. Identificar tendências de aumento ou redução em despesas e explicar de forma acessível.
3. Comparar os hábitos do usuário com padrões saudáveis e dar contexto.
4. Avaliar se os gastos são sustentáveis ou precisam de ajustes.

Use um tom claro e motivador, ajudando o usuário a visualizar um caminho financeiro positivo.

Dados de padrões:
{padroes}

"""

template_anomalias = """
Como analista financeiro, ajude o usuário a identificar possíveis problemas em seus gastos ao:

1. Localizar despesas fora do padrão habitual e explicar o porquê.
2. Verificar cobranças duplicadas ou irregulares.
3. Identificar serviços recorrentes que parecem não estar sendo usados.
4. Apontar categorias com gastos desproporcionais e sugerir ajustes.

Se não encontrar anomalias, destaque o bom comportamento financeiro do usuário. Use exemplos simples e amigáveis.

Dados:
{dados_completos}
Padrões:
{padroes}
"""

template_insights = """
Como consultor financeiro, gere insights claros e acionáveis com base nos dados do usuário:

1. Áreas onde é possível economizar de forma prática.
2. Comportamentos financeiros positivos que o usuário deve manter.
3. Hábitos que precisam de ajustes com explicações claras.
4. Comparação com metas financeiras para motivar o usuário a melhorar.

Apresente os insights de forma acessível e motivadora, sugerindo passos concretos para o usuário.

Tendências:
{dados_completos}
Anomalias:
{anomalias}
"""

template_recomendacoes = """
Como consultor financeiro pessoal, ofereça recomendações práticas e amigáveis com base nos insights:

1. Sugestões específicas para economizar em categorias importantes.
2. Alternativas viáveis para serviços caros ou despesas desnecessárias.
3. Estratégias simples para melhorar os hábitos financeiros.
4. Metas alcançáveis para o próximo período com exemplos motivadores.

Use um tom amigável, explique de forma direta e adicione emojis para tornar a comunicação mais leve e engajante.

Insights disponíveis:
{insights}
"""

template_relatorio = """
Você é um especialista em criar relatórios financeiros claros e objetivos. Crie um relatório para o usuário que inclua:

1. Resumo dos Gastos:
   - Números principais e conclusões apresentadas de forma simples.
   - Gastos por categoria organizados visualmente.
   - Destaques de tendências de gastos.

2. Análise Detalhada:
   - Explicação de gastos por categorias com exemplos claros.
   - Tendências financeiras identificadas.
   - Anomalias importantes e como ajustá-las.

3. Recomendações:
   - Sugestões práticas para economizar.
   - Próximos passos que o usuário pode seguir facilmente.

Divida as seções do relatório com os seguintes caracteres:

---------------
"""

prompt_agregador = PromptTemplate.from_template(template_agregador)
prompt_padroes = PromptTemplate.from_template(template_padroes)
prompt_tendencias = PromptTemplate.from_template(template_tendencias)
prompt_anomalias = PromptTemplate.from_template(template_anomalias)
prompt_insights = PromptTemplate.from_template(template_insights)
prompt_recomendacoes = PromptTemplate.from_template(template_recomendacoes)
prompt_relatorio = PromptTemplate.from_template(template_relatorio)

llm = ChatGroq(
        api_key=GROQ_API_KEY,
        model="llama3-70b-8192"
    )

chain_agregador = prompt_agregador | llm | StrOutputParser()
chain_padroes = prompt_padroes | llm | StrOutputParser()
chain_tendencias = prompt_tendencias | llm | StrOutputParser()
chain_anomalias = prompt_anomalias | llm | StrOutputParser()
chain_insights = prompt_insights | llm | StrOutputParser()
chain_recomendacoes = prompt_recomendacoes | llm | StrOutputParser()
chain_relatorio = prompt_relatorio | llm | StrOutputParser()

chain_analise_basica = {"dados_agregados": chain_agregador} | chain_padroes

chain_gera_relatorio = (
    {"padroes": chain_analise_basica} 
    | RunnablePassthrough() 
    | {"dados_completos": chain_tendencias, "padroes": itemgetter("padroes")} 
    | {"anomalias": chain_anomalias, "dados_completos": itemgetter("dados_completos")}
    | RunnablePassthrough() 
    | {"insights": chain_insights, "dados_completos": itemgetter("dados_completos")}
    | {"recomendacoes": chain_recomendacoes, "insights": itemgetter("insights"), "dados_completos": itemgetter("dados_completos")}
    | chain_relatorio
)