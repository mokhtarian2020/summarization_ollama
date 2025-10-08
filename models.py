from pydantic import BaseModel
from typing import Dict, Optional

class SummarizeRequest(BaseModel):
    docs: Dict[str, str]
    modo: int
    sintesi_aggregata: Optional[int] = 0
