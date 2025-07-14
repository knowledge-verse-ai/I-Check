import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routes.i_check_router import router as i_check_router

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(i_check_router)

@app.get("/")
async def root():
    return {"message": "App running successfully"}

if __name__ == '__main__':
    uvicorn.run('main:app', port=5000)