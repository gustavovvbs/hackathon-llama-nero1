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
Você é um analista financeiro especializado em agregação de dados. A partir das transações classificadas fornecidas, você deve:

1. Calcular o total gasto em cada categoria
2. Identificar as maiores despesas individuais
3. Calcular médias diárias/semanais/mensais de gastos
4. Identificar períodos de maior gasto
5. Destacar comportamentos positivos a reforçar.

A ideia é que você agregue e analise os dados das transações classificadas para fornecer insights financeiros úteis. Detalhe a agragação.

Dados das transações:
{transacoes}
"""

template_padroes = """
Como especialista em análise de comportamento financeiro, analise os dados agregados para identificar:

1. Padrões de gastos recorrentes
2. Ciclos de despesas (início/fim de mês, fins de semana)
3. Categorias com gastos crescentes
4. Relações entre diferentes tipos de despesas

Detalhe os padrões e comportamentos identificados. A ideia é que esta seja uma análise básica da situação financeira do usuário.

Dados agregados:
{dados_agregados}
"""

template_tendencias = """
Como especialista em análise de tendências financeiras, examine os padrões identificados para:

1. Projetar gastos futuros por categoria
2. Identificar tendências de aumento/diminuição de gastos
3. Comparar com benchmarks de gastos saudáveis
4. Avaliar sustentabilidade dos padrões atuais

Detalhe bem as tendências identificadas e as projeções futuras. A ideia é que tenhamos o máximo de conhecimento possível do indíviduo para ajudá-lo a tomar decisões financeiras mais conscientes.

Dados de padrões:
{padroes}
"""

template_anomalias = """
Como especialista em detecção de anomalias financeiras, analise os dados e os padrões do usuário para identificar:

1. Gastos fora do padrão habitual
2. Possíveis cobranças duplicadas
3. Serviços recorrentes subutilizados
4. Categorias com gastos desproporcionais

Detalhe bem as anomalias identificadas e sugira ações corretivas. A ideia é que possamos ajudar o usuário a identificar e corrigir problemas financeiros antes que se tornem graves. Se não houver 
anomalias, informe que não foram encontradas.

Dados:
{dados_completos}
Padrões:
{padroes}
"""

template_insights = """
Como consultor financeiro, analise as tendências de comportamento do usuário, seus padrões e anomalias possivelmente identificadas para gerar insights acionáveis:

1. Principais áreas de oportunidade de economia
2. Comportamentos financeiros positivos a manter
3. Comportamentos que precisam de atenção
4. Comparação com metas financeiras (se estabelecidas)

Detalhe bem os insights gerados e sugira ações específicas para melhorar a saúde financeira do usuário. A ideia é que esses insights possam ser analisados por um consultor a fim do mesmo
criar recomendações personalizadas baseadas nestes insights.

Tendências:
{dados_completos}
Anomalias:
{anomalias}
"""

template_recomendacoes = """
Como consultor financeiro pessoal, crie recomendações personalizadas baseadas nos insights:

1. Sugestões específicas de economia por categoria
2. Alternativas para serviços caros identificados
3. Estratégias para melhorar hábitos financeiros
4. Metas sugeridas para o próximo período

Detalhes bem as recomendações e sugira ações específicas para melhorar a saúde financeira do usuário. A ideia é que essas recomendações sejam práticas e fáceis de seguir, ajudando o usuário a 
melhorar sua situação financeira.

Insights disponíveis:
{insights}
"""

template_relatorio = """
Como especialista em comunicação financeira, crie um relatório completo e amigável que inclua:

1. Resumo Executivo
   - Principais números e conclusões
   - Destaques do período

2. Análise Detalhada
   - Breakdown por categorias
   - Tendências identificadas
   - Anomalias importantes

3. Recomendações
   - Sugestões práticas
   - Próximos passos sugeridos

Dados completos:
{dados_completos}
Insights:
{insights}
Recomendações:
{recomendacoes}

Crie um relatório em formato Markdown que seja informativo mas não intimidante.
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