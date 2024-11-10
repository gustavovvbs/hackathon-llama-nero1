import os
from pymongo import MongoClient
from dotenv import load_dotenv
from fastapi import Form, FastAPI
from typing import Any
from datetime import datetime
from utils import process_pdf
from chains import chain_gera_relatorio
from twilio.rest import Client 

load_dotenv()

TWILIO_SID = os.getenv("TWILIO_SID")
TWILIO_AUTH = os.getenv("TWILIO_TOKEN")

MONGODB_ATLAS_CLUSTER_URI = os.getenv('MONGODB_URI')
twilio_client = Client(TWILIO_SID, TWILIO_AUTH)

app = FastAPI(
    title="Llama Hackathon",
    version="1.0",
    description="Uma API que ",
)

def db(collection : str):
    client = MongoClient(MONGODB_ATLAS_CLUSTER_URI)
    DB_NAME = "metahack"
    COLLECTION_NAME = collection
    db = client[DB_NAME][COLLECTION_NAME]
    return db

def respond(user_num):
    #VERIFICANDO SE O USUARIO EXISTE, SE SIM PEGA OS DADOS SE NAO CRIA COMO NONE
    user_db = db("userdb") 
    result = user_db.find_one_and_update(
    {"user_num": user_num},          # Filtro de busca
    {"$setOnInsert": {"user_num": user_num, "data" : {"freq" : None, "estado": None}}},  # Define o campo apenas na criação
    upsert=True,                           # Habilita o upsert para criar o documento
    return_document=True                   # Retorna o documento após a atualização ou criação
    )

    #VERIFICANDO ESTADO
    state = result["data"]["estado"]

from typing import Optional
@app.post('/')
async def receive_pdf(Body: Any = Form(...), From: str = Form(...), MediaUrl0: Optional[str] = Form(None),  MediaContentType0: Optional[str] = Form(None)):
    user_num = From[10:]
    #VERIFICANDO SE O USUARIO EXISTE, SE SIM PEGA OS DADOS SE NAO CRIA COMO NONE
    user_db = db("userdb") 
    result = user_db.find_one_and_update(
    {"user_num": user_num},          # Filtro de busca
    {"$setOnInsert": {"user_num": user_num, "data" : {"freq" : None, "estado": None}}},  # Define o campo apenas na criação
    upsert=True,                           # Habilita o upsert para criar o documento
    return_document=True                   # Retorna o documento após a atualização ou criação
    )

    if Body.lower() == "semanal" or Body.lower() == "mensal":
        result = user_db.update_one(
            {"user_num": user_num},        # Filtro para encontrar o usuário
            {"$set": {"data.freq": Body.lower(), "data.estado": "frequencia"}}    # Atualiza apenas o campo "freq" dentro de "data"
        )

        result = user_db.find_one(
            {"user_num": user_num}
        )

    if MediaUrl0 != None:
        result = user_db.update_one(
            {"user_num": user_num},        # Filtro para encontrar o usuário
            {"$set": {"data.estado": "extrato"}}    # Atualiza apenas o campo "freq" dentro de "data"
        )

        result = user_db.find_one(
            {"user_num": user_num}
        )


    # VERIFICANDO ESTADOS
    print(result)
    print('-------------------------------')
    print(type(result))
    state = result["data"]["estado"]

    if state == None:
        message = twilio_client.messages.create(
        from_='whatsapp:+15674852810',
        body="Mensagem inicial dando boas-vindas e pedindo a frequência de envio",
        to='whatsapp:+' + user_num
        )

        return ''

    elif state == "frequencia":
        message = twilio_client.messages.create(
        from_='whatsapp:+15674852810',
        body="Agora que sabemos a frequencia, pedimos o extrato mais recente para o usuário.",
        to='whatsapp:+' + user_num
        )

        return ''
    

    elif state == "extrato":
        message = twilio_client.messages.create(
            from_='whatsapp:+15674852810',
            body="Espere um pouco estamos processando seu extrato",
            to='whatsapp:+' + user_num
            )
        
        try:
            data = await process_pdf(MediaUrl0)
            extract = data['additional_kwargs']['tool_calls']
            data_antiga = extract[0]['function']['arguments']['data']
            
            # Converte a string para um objeto datetime
            data_obj = datetime.strptime(data, "%Y-%m-%d").date()

            # Obtém a data atual (apenas a data)
            data_hoje = datetime.today().date()

            # Calcula o delta (diferença) em dias
            delta = (data_obj - data_hoje).days

            # Verifica se o delta está dentro do intervalo desejado
            intervalo_tolerancia = 31  # Exemplo: 30 dias

            if abs(delta) <= intervalo_tolerancia:
                s = ""
                for i in range(len(extract)):
                    s += f"Transação: {extract[i]['function']['arguments']}\n --------------------------\n"

                relatorio = chain_gera_relatorio.invoke({'transacoes': s})
                print(relatorio)
                message = twilio_client.messages.create(
                from_='whatsapp:+15674852810',
                body=relatorio,
                to='whatsapp:+' + user_num
                )

                result = user_db.update_one(
                {"user_num": user_num},        # Filtro para encontrar o usuário
                {"$set": {"data.estado": "frequencia"}}    # Atualiza apenas o campo "freq" dentro de "data"
                )

                result = user_db.find_one(
                    {"user_num": user_num}
                )

            else:
                message = twilio_client.messages.create(
                from_='whatsapp:+15674852810',
                body="guardando seus dados no banco de dados para melhorar analises futuras.",
                to='whatsapp:+' + user_num
                )
        
        except Exception as err:
            print(err)
            message = twilio_client.messages.create(
            from_='whatsapp:+15674852810',
            body="Tivemos um problema ao processar seu extrato. Caso o problema persista, contate nosso suporte.",
            to='whatsapp:+' + user_num
            )

            return ''
        
        







                
                
                
        

        if datetime.now:
            message = twilio_client.messages.create(
            from_='whatsapp:+15674852810',
            body="envia o relatório e adiciona as infos no db",
            to='whatsapp:+' + user_num
            )

            return ''
        else:
            message = twilio_client.messages.create(
            from_='whatsapp:+15674852810',
            body="adiciona as infos no db e pede pro usuário enviar os dados mais atualizados",
            to='whatsapp:+' + user_num
            )

            return ''

    
