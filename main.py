from fastapi import APIRouter, FastAPI
from services.receive_file import router as receive_file_router


app = FastAPI()
api_router = APIRouter()

api_router.include_router(receive_file_router, prefix='/whatsapp')
app.include_router(api_router)

