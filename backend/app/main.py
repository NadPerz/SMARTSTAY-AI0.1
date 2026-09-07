from fastapi import FastAPI
app = FastAPI(title='SmartStay AI — Backend')

@app.get('/health')
async def health():
    return {'status': 'ok'}
