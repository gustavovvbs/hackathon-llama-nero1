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

1. **Calcular o total gasto em cada categoria**, utilizando emojis para representar cada uma delas e explicando de forma clara e visual.
   - 🥗 **Alimentação**: R$ valor
   - 🚗 **Transporte**: R$ valor
   - 🏠 **Moradia**: R$ valor
   - 🎉 **Lazer**: R$ valor
   - ... *(adicione outras categorias conforme necessário)*

2. **Destacar as maiores despesas individuais** e em quais categorias elas se concentram, utilizando gráficos simples ou representações visuais.
3. **Apresentar médias de gastos diárias, semanais e mensais** de maneira simples e direta.
4. **Identificar períodos de maior gasto** e ajudar o usuário a entender esses picos com exemplos concretos.
5. **Destacar hábitos financeiros positivos** que o usuário pode manter para melhorar sua saúde financeira.

Mantenha o tom leve e educativo, ajudando o usuário a se sentir no controle de suas finanças.

**Dados das transações:**
{transacoes}
"""

template_padroes = """
Como especialista em análise financeira, ajude o usuário a identificar seus hábitos financeiros ao:

1. **Descobrir padrões de gastos recorrentes**, utilizando emojis para cada categoria e explicações claras.
2. **Entender ciclos de despesas**, como aumentos no início ou fim do mês, destacando com gráficos ou ícones.
3. **Apontar categorias com tendências de aumento nos gastos** e que precisam de atenção, utilizando cores ou sinais de alerta.
4. **Mostrar como diferentes categorias de despesas estão conectadas**, usando diagramas simples ou fluxogramas.

Apresente as informações de forma clara e educativa para que o usuário veja valor em sua análise.

**Dados agregados:**
{dados_agregados}

"""

template_tendencias = """
Você é um especialista em projeções financeiras. Ajude o usuário a planejar melhor seus gastos ao:

1. **Estimar gastos futuros em categorias importantes**, representadas por emojis para facilitar a visualização.
2. **Identificar tendências de aumento ou redução em despesas** e explicar de forma acessível com gráficos de linha ou barras.
3. **Comparar os hábitos do usuário com padrões saudáveis** e dar contexto utilizando benchmarks ou médias de mercado.
4. **Avaliar se os gastos são sustentáveis** ou precisam de ajustes, destacando com ícones de semáforo (verde, amarelo, vermelho).

Use um tom claro e motivador, ajudando o usuário a visualizar um caminho financeiro positivo.

**Dados de padrões:**
{padroes}

"""


template_insights = """
Como consultor financeiro, gere insights claros e acionáveis com base nos dados do usuário:

1. **Áreas onde é possível economizar de forma prática**, destacadas com emojis e sugestões específicas.
2. **Comportamentos financeiros positivos** que o usuário deve manter, utilizando ícones de medalha ou estrelas.
3. **Hábitos que precisam de ajustes** com explicações claras e exemplos de como melhorar.
4. **Comparação com metas financeiras** para motivar o usuário a melhorar, mostrando progresso com barras de progresso ou gráficos.

Apresente os insights de forma acessível e motivadora, sugerindo passos concretos para o usuário.

**Tendências:**
{dados_completos}
"""

template_recomendacoes = """
Como consultor financeiro pessoal, ofereça recomendações práticas e amigáveis com base nos insights:

1. **Sugestões específicas para economizar em categorias importantes**, usando emojis para ilustrar cada recomendação.
2. **Alternativas viáveis para serviços caros ou despesas desnecessárias**, apresentadas de forma clara e direta.
3. **Estratégias simples para melhorar os hábitos financeiros**, com passos fáceis de seguir.
4. **Metas alcançáveis para o próximo período** com exemplos motivadores e sugestões de acompanhamento.

Use um tom amigável, explique de forma direta e **adicione emojis** para tornar a comunicação mais leve e engajante. 🎯💡👍

**Insights disponíveis:**
{insights}
"""

template_relatorio = """
Você é um especialista em criar relatórios financeiros claros e objetivos. Crie um relatório para o usuário que inclua:

1. **Resumo dos Gastos:**
   - **Números principais e conclusões** apresentadas de forma simples.
   - **Gastos por categoria organizados visualmente** com emojis e gráficos.
     - 🥗 **Alimentação**: R$ valor
     - 🚗 **Transporte**: R$ valor
     - 🏠 **Moradia**: R$ valor
     - 🎉 **Lazer**: R$ valor
     - ... *(adicione outras categorias conforme necessário)*
   - **Destaques de tendências de gastos** com gráficos de linha ou barras.

2. **Análise Detalhada:**
   - **Explicação de gastos por categorias** com exemplos claros e emojis.
   - **Tendências financeiras identificadas** utilizando gráficos e ícones.

3. **Recomendações:**
   - **Sugestões práticas para economizar**, ilustradas com emojis e passos concretos. Não de sugestões genéricas e vagas, mas sim recomendações específicas e acionáveis com base nos dados fornecidos.

Não faça o relatório em formato de markdown.

NÃO INCLUA GRÁFICOS OU INTENÇÃO DE INCLUIR UM GRÁFICO.

NÃO FALE NADA SOBRE ENTREGAR ALGO PARA O USUÁRIO, JÁ QUE O USUÁRIO QUE IRÁ RECEBER O RELATÓRIO.
Não faça nenhum tipo de presunção sobre o que foram os gastos, apenas forneca os dados de forma clara e objetiva, se baseando somente nos dados fornecidos. Por exemplo, não diga que o usuário gastou muito com educação por conta de cursos de especialização, já que é impossível saber.

Divida as seções do relatório com os seguintes caracteres:

---------------
"""

prompt_agregador = PromptTemplate.from_template(template_agregador)
prompt_padroes = PromptTemplate.from_template(template_padroes)
prompt_tendencias = PromptTemplate.from_template(template_tendencias)
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
chain_insights = prompt_insights | llm | StrOutputParser()
chain_recomendacoes = prompt_recomendacoes | llm | StrOutputParser()
chain_relatorio = prompt_relatorio | llm | StrOutputParser()

chain_analise_basica = {"dados_agregados": chain_agregador} | chain_padroes

chain_gera_relatorio = (
    {"padroes": chain_analise_basica} 
    | RunnablePassthrough() 
    | {"dados_completos": chain_tendencias, "padroes": itemgetter("padroes")} 
    | RunnablePassthrough() 
    | {"insights": chain_insights, "dados_completos": itemgetter("dados_completos")}
    | {"recomendacoes": chain_recomendacoes, "insights": itemgetter("insights"), "dados_completos": itemgetter("dados_completos")}
    | chain_relatorio
)