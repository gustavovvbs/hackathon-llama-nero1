from fastapi import Form, FastAPI
from typing import Any, Optional
from datetime import datetime
from pymongo import MongoClient
from dotenv import load_dotenv
from twilio.rest import Client
from utils import process_pdf
from chains import chain_gera_relatorio
import os

load_dotenv()

TWILIO_SID = os.getenv("TWILIO_SID")
TWILIO_AUTH = os.getenv("TWILIO_TOKEN")
MONGODB_ATLAS_CLUSTER_URI = os.getenv('MONGODB_URI')

twilio_client = Client(TWILIO_SID, TWILIO_AUTH)
app = FastAPI(
    title="Llama Hackathon",
    version="1.0",
    description="Uma API para automação financeira com Twilio e MongoDB.",
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

    # Retrieve or initialize user data
    result = user_db.find_one_and_update(
        {"user_num": user_num},
        {"$setOnInsert": {"user_num": user_num, "data": {"freq": None, "estado": None}}},
        upsert=True,
        return_document=True
    )
    state = result["data"]["estado"]
    freq = result["data"].get("freq", None)
    Body_lower = Body.lower() if Body else ""

    # Map old states to new ones for backward compatibility
    old_to_new_state_map = {
        None: "aguardando_frequencia",
        "frequencia": "aguardando_extrato",
        "extrato": "aguardando_extrato",
    }
    if state in old_to_new_state_map:
        new_state = old_to_new_state_map[state]
        user_db.update_one({"user_num": user_num}, {"$set": {"data.estado": new_state}})
        state = new_state

    # Handle different states
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
                body="Por favor, envie 'Semanal' ou 'Mensal' para configurar sua frequência.",
                to='whatsapp:+' + user_num
            )

    elif state == "aguardando_extrato":
        if MediaUrl0:
            user_db.update_one({"user_num": user_num}, {"$set": {"data.estado": "processando_extrato"}})
            message = twilio_client.messages.create(
                from_='whatsapp:+YourTwilioNumber',
                body="Processando seu extrato, por favor, aguarde! 😊",
                to='whatsapp:+' + user_num
            )
            try:
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
                            "data": transaction_date,
                            "entrada_ou_saida": transaction_data["entrada_ou_saida"],
                            "valor": transaction_data["valor"],
                        })

                if filtered_transactions:
                    transactions_db.insert_many(filtered_transactions)

                # Generate report
                formatted_transactions = "\n".join(
                    f"Transação: {t}" for t in filtered_transactions
                )
                relatorio = chain_gera_relatorio.invoke({'transacoes': formatted_transactions})

                # Save report to database
                reports_db.insert_one({
                    "user_id": user_num,
                    "report": relatorio,
                    "generated_at": datetime.now()
                })

                # Send the report via WhatsApp
                messages = [relatorio[i:i + 1500] for i in range(0, len(relatorio), 1500)]
                for message in messages:
                    twilio_client.messages.create(
                        from_='whatsapp:+YourTwilioNumber',
                        body=message,
                        to='whatsapp:+' + user_num
                    )

                user_db.update_one({"user_num": user_num}, {"$set": {"data.estado": "relatorio_enviado"}})

            except Exception as e:
                print(e)
                user_db.update_one({"user_num": user_num}, {"$set": {"data.estado": "aguardando_extrato"}})
                twilio_client.messages.create(
                    from_='whatsapp:+YourTwilioNumber',
                    body="Erro ao processar o extrato. Tente novamente.",
                    to='whatsapp:+' + user_num
                )
        else:
            twilio_client.messages.create(
                from_='whatsapp:+YourTwilioNumber',
                body="Por favor, envie o extrato bancário em formato PDF.",
                to='whatsapp:+' + user_num
            )

    elif state == "processando_extrato":
        twilio_client.messages.create(
            from_='whatsapp:+YourTwilioNumber',
            body="Seu extrato está sendo processado. Por favor, aguarde!",
            to='whatsapp:+' + user_num
        )

    elif state == "relatorio_enviado":
        twilio_client.messages.create(
            from_='whatsapp:+YourTwilioNumber',
            body="Seu relatório foi enviado. Envie outro extrato para continuar! 😊",
            to='whatsapp:+' + user_num
        )
        user_db.update_one({"user_num": user_num}, {"$set": {"data.estado": "aguardando_frequencia"}})

    else:
        user_db.update_one({"user_num": user_num}, {"$set": {"data.estado": "aguardando_frequencia"}})
        twilio_client.messages.create(
            from_='whatsapp:+YourTwilioNumber',
            body="Bem-vindo ao Finn.AI! Escolha a frequência: 'Semanal' ou 'Mensal'.",
            to='whatsapp:+' + user_num
        )

    return ''
