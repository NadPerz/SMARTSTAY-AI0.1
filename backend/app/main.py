from fastapi import FastAPI

from app.api.v1.agents import router as agents_router
from app.api.v1.auth import router as auth_router
from app.api.v1.bookings import router as bookings_router
from app.api.v1.reviews import router as reviews_router

app = FastAPI(title='SmartStay AI — Backend')
app.include_router(agents_router)
app.include_router(auth_router, prefix="/auth", tags=["auth"])
app.include_router(bookings_router, prefix="/api", tags=["reservations"])
app.include_router(reviews_router, prefix="/api", tags=["feedback"])

@app.get('/health')
async def health():
    return {'status': 'ok'}
