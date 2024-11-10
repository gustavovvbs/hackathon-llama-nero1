import os
from pymongo import MongoClient
from dotenv import load_dotenv
from fastapi import Form, FastAPI
from typing import Any, Optional
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

def db(collection: str):
    client = MongoClient(MONGODB_ATLAS_CLUSTER_URI)
    DB_NAME = "metahack"
    COLLECTION_NAME = collection
    return client[DB_NAME][COLLECTION_NAME]


@app.post('/')
async def receive_pdf(
    Body: Any = Form(...),
    From: str = Form(...),
    MediaUrl0: Optional[str] = Form(None),
    MediaContentType0: Optional[str] = Form(None)
):
    user_num = From[10:]
    user_db = db("userdb")
    transactions_db = db("transactions")
    reports_db = db("reports")

    # Fetch or initialize user state
    result = user_db.find_one_and_update(
        {"user_num": user_num},
        {"$setOnInsert": {"user_num": user_num, "data": {"freq": None, "estado": None}}},
        upsert=True,
        return_document=True
    )

    state = result["data"]["estado"]
    freq = result["data"].get("freq", None)
    Body_lower = Body.lower() if Body else ""

    # Map old state names to new state names for backward compatibility
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

    # Handle user input based on the current state
    if state == "aguardando_frequencia":
        if Body_lower in ["semanal", "mensal"]:
            user_db.update_one(
                {"user_num": user_num},
                {"$set": {"data.freq": Body_lower, "data.estado": "aguardando_extrato"}}
            )
            message = twilio_client.messages.create(
                from_='whatsapp:+15674852810',
                body="Por favor, envie o extrato bancário mais recente em formato PDF.",
                to='whatsapp:+' + user_num
            )
        else:
            message = twilio_client.messages.create(
                from_='whatsapp:+15674852810',
                body="Oi! 👋 Envia um extrato pra eu fazer um relatório, ou envie 'Semanal' ou 'Mensal' para mudar a frequência dos lembretes.",
                to='whatsapp:+' + user_num
            )

    elif state == "aguardando_extrato":
        if MediaUrl0:
            user_db.update_one(
                {"user_num": user_num},
                {"$set": {"data.estado": "processando_extrato"}}
            )
            message = twilio_client.messages.create(
                from_='whatsapp:+15674852810',
                body="Espere um pouco! Estamos processando seu extrato 😊. Pode demorar de um a dois minutos.",
                to='whatsapp:+' + user_num
            )
            try:
                # Process the PDF and extract transactions
                data = await process_pdf(MediaUrl0)
                extract = data.additional_kwargs['tool_calls']

                # Filter transactions by frequency
                interval_days = 7 if freq == "semanal" else 30
                data_hoje = datetime.today().date()
                filtered_transactions = []

                for transaction in extract:
                    transaction_data = eval(transaction['function']['arguments'])
                    transaction_date = datetime.strptime(transaction_data['data'], "%Y-%m-%d").date()
                    delta = (data_hoje - transaction_date).days

                    if delta <= interval_days:
                        filtered_transactions.append({
                            "user_id": user_num,
                            "tipo": transaction_data["tipo"],
                            "data": transaction_date.isoformat(),
                            "entrada_ou_saida": transaction_data["entrada_ou_saida"],
                            "valor": transaction_data["valor"],
                        })

                # Save transactions to the database
                if filtered_transactions:
                    transactions_db.insert_many(filtered_transactions)

                # Generate a financial report
                transacao_formatada = "\n".join(
                    f"Transação: {t}" for t in filtered_transactions
                )
                relatorio = chain_gera_relatorio.invoke({'transacoes': transacao_formatada})

                # Save report to the database
                reports_db.insert_one({
                    "user_id": user_num,
                    "report": relatorio,
                    "generated_at": datetime.now()
                })

                # Split the report into smaller messages and send via WhatsApp
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

                for texto_mensagem in mensagens:
                    message = twilio_client.messages.create(
                        from_='whatsapp:+15674852810',
                        body=texto_mensagem,
                        to='whatsapp:+' + user_num
                    )

                # Update user's state
                user_db.update_one(
                    {"user_num": user_num},
                    {"$set": {"data.estado": "relatorio_enviado"}}
                )

            except Exception as err:
                print(err)
                message = twilio_client.messages.create(
                    from_='whatsapp:+15674852810',
                    body="Tivemos um problema ao processar seu extrato. Por favor, envie novamente.",
                    to='whatsapp:+' + user_num
                )
                user_db.update_one(
                    {"user_num": user_num},
                    {"$set": {"data.estado": "aguardando_extrato"}}
                )
        else:
            message = twilio_client.messages.create(
                from_='whatsapp:+15674852810',
                body="Por favor, envie o extrato bancário em formato PDF.",
                to='whatsapp:+' + user_num
            )

    elif state == "processando_extrato":
        message = twilio_client.messages.create(
            from_='whatsapp:+15674852810',
            body="Estamos processando seu extrato. Por favor, aguarde.",
            to='whatsapp:+' + user_num
        )

    elif state == "relatorio_enviado":
        message = twilio_client.messages.create(
            from_='whatsapp:+15674852810',
            body="Se você precisar de mais um relatório, é só enviar o extrato novamente! 😊",
            to='whatsapp:+' + user_num
        )
        user_db.update_one(
            {"user_num": user_num},
            {"$set": {"data.estado": "aguardando_extrato", "data.freq": None}}
        )

    else:
        user_db.update_one(
            {"user_num": user_num},
            {"$set": {"data.estado": "aguardando_frequencia", "data.freq": None}}
        )
        message = twilio_client.messages.create(
            from_='whatsapp:+15674852810',
            body="""Olá! 👋 Eu sou o Finn.AI, o bot que ajuda você a cuidar das suas finanças! 😊

Para começar, com qual frequência você prefere receber nossas mensagens? As opções são:
- Semanal
- Mensal
Escolha a que for mais conveniente para você! 🗓️✨""",
            to='whatsapp:+' + user_num
        )

    return ''
