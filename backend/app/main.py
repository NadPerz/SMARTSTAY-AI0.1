from fastapi import FastAPI

from app.api.v1.agents import router as agents_router

app = FastAPI(title='SmartStay AI — Backend')
app.include_router(agents_router)

@app.get('/health')
async def health():
    return {'status': 'ok'}
