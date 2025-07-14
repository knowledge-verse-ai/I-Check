from fastapi import APIRouter
from controllers.i_check_controller import get_memory, save_memory

router = APIRouter()

router.post("/save_memory")(save_memory)
router.post("/get_memory")(get_memory)