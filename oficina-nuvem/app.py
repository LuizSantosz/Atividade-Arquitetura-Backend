import os

from fastapi import FastAPI

app = FastAPI()
AMBIENTE = os.environ.get("APP_ENV", "desconhecido")

@app.get("/health/live")
def live():
    return {"status": "live"}

@app.get("/health/ready")
def ready():
    return {"status": "ready"}

@app.get("/elegibilidades/{numero}")
def consultar(numero: str):
    return {"numero": numero, "elegivel": True, "ambiente": AMBIENTE}