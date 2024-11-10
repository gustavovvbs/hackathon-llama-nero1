from pydantic import BaseModel, Field 
from typing import Optional, Dict 

class UserState(BaseModel):
    user_id: str 
    state: str 
    data: Optional[Dict] = None