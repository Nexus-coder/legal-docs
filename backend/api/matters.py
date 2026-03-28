from fastapi import APIRouter
from typing import List
from models.domain import Matter

router = APIRouter()

@router.get("/", response_model=List[Matter])
def list_matters():
    return [
        Matter(
            id="ELC/E045/2024",
            division="Environment & Land Court",
            status="Drafting",
            verification_done=4,
            verification_total=12,
            last_activity="Retrieved Giella v. Cassman (1973)"
        )
    ]
