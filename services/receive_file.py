from twilio.rest import Client 
from fastapi import FastAPI, Form, Depends, UploadFile, File, APIRouter
from fastapi.responses import JSONResponse
import os 
from dotenv import load_dotenv 
from typing import Any
import httpx 


load_dotenv()

TWILIO_SID = os.getenv('TWILIO_SID')
TWILIO_AUTH = os.getenv("TWILIO_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

twilio_client = Client(TWILIO_SID, TWILIO_AUTH)

router = APIRouter()


@router.post('/')
async def receive_pdf(Body: Any = Form(...), From: str = Form(...), MediaUrl0: str = Form(...),  MediaContentType0: str = Form(...)):
    
    print(MediaUrl0)
    if MediaContentType0 == "application/pdf":
        async with httpx.AsyncClient() as client:
            response = await client.get(MediaUrl0)
            pdf_bytes = response.content
        return JSONResponse(content={"message": "PDF recebido com sucesso."})
    else:
        return JSONResponse(content={"message": "O arquivo recebido não é um PDF."}, status_code=400)