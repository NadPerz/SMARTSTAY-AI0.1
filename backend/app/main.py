from fastapi import FastAPI

from app.api.v1.agents import router as agents_router
from app.api.v1.auth import router as auth_router

app = FastAPI(title='SmartStay AI — Backend')
app.include_router(agents_router)
app.include_router(auth_router, prefix="/auth", tags=["auth"])

@app.get('/health')
async def health():
    return {'status': 'ok'}
