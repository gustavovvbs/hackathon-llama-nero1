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


@app.post('/')
async def receive_pdf(
    Body: Any = Form(...),
    From: str = Form(...),
    MediaUrl0: Optional[str] = Form(None),
    MediaContentType0: Optional[str] = Form(None)
):
    user_num = From[10:]
    user_db = db("userdb")
    result = user_db.find_one_and_update(
        {"user_num": user_num},
        {"$setOnInsert": {"user_num": user_num, "data": {"freq": None, "estado": None}}},
        upsert=True,
        return_document=True
    )

    state = result["data"]["estado"]
    Body_lower = Body.lower() if Body else ""

    # **Map old state names to new state names for backward compatibility**
    old_to_new_state_map = {
        None: "aguardando_frequencia",
        "frequencia": "aguardando_extrato",
        "extrato": "aguardando_extrato",
    }
    if state in old_to_new_state_map:
        new_state = old_to_new_state_map[state]
        user_db.update_one(
            {"user_num": user_num},
            {"$set": {"data.estado": new_state}}
        )
        state = new_state

    # **Handle user input based on the current state**
    if state == "aguardando_frequencia":
        if Body_lower in ["semanal", "mensal"]:
            user_db.update_one(
                {"user_num": user_num},
                {"$set": {"data.freq": Body_lower, "data.estado": "aguardando_extrato"}}
            )
            message = twilio_client.messages.create(
                from_='whatsapp:+YourTwilioNumber',
                body="Por favor, envie o extrato bancário mais recente em formato PDF.",
                to='whatsapp:+' + user_num
            )
        else:
            message = twilio_client.messages.create(
                from_='whatsapp:+YourTwilioNumber',
                body="Desculpe, não entendi. Por favor, responda com 'semanal' ou 'mensal'.",
                to='whatsapp:+' + user_num
            )

    elif state == "aguardando_extrato":
        if MediaUrl0:
            user_db.update_one(
                {"user_num": user_num},
                {"$set": {"data.estado": "processando_extrato"}}
            )
            message = twilio_client.messages.create(
                from_='whatsapp:+YourTwilioNumber',
                body="Espere um pouco! Estamos processando seu extrato 😊.",
                to='whatsapp:+' + user_num
            )
            try:
                # **Include your existing processing logic here**
                data = await process_pdf(MediaUrl0)
                extract = data.additional_kwargs['tool_calls']
                data_antiga = eval(extract[0]['function']['arguments'])['data']

                # **Date processing logic**
                from datetime import datetime
                data_obj = datetime.strptime(data_antiga, "%Y-%m-%d").date()
                data_hoje = datetime.today().date()
                delta = (data_obj - data_hoje).days
                intervalo_tolerancia = 31  # Example: 31 days

                if abs(delta) <= intervalo_tolerancia:
                    s = ""
                    for i in range(len(extract)):
                        s += f"Transação: {extract[i]['function']['arguments']}\n --------------------------\n"

                    relatorio = chain_gera_relatorio.invoke({'transacoes': s})

                    # **Split the report into smaller messages**
                    limite_caracteres = 1500
                    secoes = relatorio.split('\n\n')
                    mensagens = []
                    mensagem_atual = ''

                    for secao in secoes:
                        if len(mensagem_atual) + len(secao) + 2 <= limite_caracteres:
                            if mensagem_atual:
                                mensagem_atual += '\n\n' + secao
                            else:
                                mensagem_atual = secao
                        else:
                            mensagens.append(mensagem_atual)
                            mensagem_atual = secao

                    if mensagem_atual:
                        mensagens.append(mensagem_atual)

                    # **Send each message via WhatsApp**
                    for texto_mensagem in mensagens:
                        message = twilio_client.messages.create(
                            from_='whatsapp:+YourTwilioNumber',
                            body=texto_mensagem,
                            to='whatsapp:+' + user_num
                        )

                    # **Update the user's state to 'relatorio_enviado'**
                    user_db.update_one(
                        {"user_num": user_num},
                        {"$set": {"data.estado": "relatorio_enviado"}}
                    )

                else:
                    # **Prompt the user to send a recent bank statement**
                    message = twilio_client.messages.create(
                        from_='whatsapp:+YourTwilioNumber',
                        body="""Para fornecer recomendações precisas, precisamos do extrato bancário mais recente. Por favor, envie um extrato atualizado.""",
                        to='whatsapp:+' + user_num
                    )
                    user_db.update_one(
                        {"user_num": user_num},
                        {"$set": {"data.estado": "aguardando_extrato"}}
                    )
            except Exception as err:
                print(err)
                message = twilio_client.messages.create(
                    from_='whatsapp:+YourTwilioNumber',
                    body="Tivemos um problema ao processar seu extrato. Por favor, envie novamente.",
                    to='whatsapp:+' + user_num
                )
                user_db.update_one(
                    {"user_num": user_num},
                    {"$set": {"data.estado": "aguardando_extrato"}}
                )
        else:
            message = twilio_client.messages.create(
                from_='whatsapp:+YourTwilioNumber',
                body="Por favor, envie o extrato bancário em formato PDF.",
                to='whatsapp:+' + user_num
            )

    elif state == "processando_extrato":
        # **Inform the user that processing is ongoing**
        message = twilio_client.messages.create(
            from_='whatsapp:+YourTwilioNumber',
            body="Estamos processando seu extrato. Por favor, aguarde.",
            to='whatsapp:+' + user_num
        )

    elif state == "relatorio_enviado":
        # **Interaction is complete; optionally reset state**
        message = twilio_client.messages.create(
            from_='whatsapp:+YourTwilioNumber',
            body="Seu relatório foi enviado. Precisa de mais alguma coisa?",
            to='whatsapp:+' + user_num
        )
        user_db.update_one(
            {"user_num": user_num},
            {"$set": {"data.estado": "aguardando_frequencia", "data.freq": None}}
        )

    else:
        # **Handle unexpected states by resetting**
        user_db.update_one(
            {"user_num": user_num},
            {"$set": {"data.estado": "aguardando_frequencia", "data.freq": None}}
        )
        message = twilio_client.messages.create(
            from_='whatsapp:+YourTwilioNumber',
            body="""Olá! 👋 Eu sou o Finn.AI, o bot que ajuda você a cuidar das suas finanças! 😊

Para começar, com qual frequência você prefere receber nossas mensagens? As opções são:
- Semanal
- Mensal
Escolha a que for mais conveniente para você! 📅✨""",
            to='whatsapp:+' + user_num
        )

    return ''