import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from server import server_settings
from src.sample_paper.routes import sample_paper_router

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    return {"message": f"Hello World from {server_settings.APP_NAME}"}


app.include_router(sample_paper_router)

if __name__ == "__main__":
    uvicorn.run(
        "server.main:app",
        host=server_settings.HOST,
        port=server_settings.PORT,
        reload=server_settings.DEBUG_MODE,
    )
