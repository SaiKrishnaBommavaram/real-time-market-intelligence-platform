from fastapi import APIRouter

from api.routes.market import router as market_router


router = APIRouter(prefix="/v1")
router.include_router(market_router)
