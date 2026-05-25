from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pymongo import MongoClient
from datetime import datetime
import os

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True
)

client = MongoClient(os.environ["MONGO_URI"])
db = client["ISIS2304A15202610"]

@app.get("/")
def inicio():
    return {"estado": "API Dann-Alpes funcionando"}

# ---- RESEÑAS ----

@app.get("/hoteles/{hotel_id}/reseñas")
def get_reseñas(hotel_id: str):
    reseñas = list(db["reseñas"].find({"hotel_id": hotel_id}, {"_id": 0}))
    return reseñas

@app.post("/hoteles/{hotel_id}/reseñas")
def post_reseña(hotel_id: str, datos: dict):
    datos["hotel_id"] = hotel_id
    datos["fecha"] = datetime.now().isoformat()
    datos["visible"] = True
    datos["destacada"] = False
    datos["votos_utilidad"] = 0
    db["reseñas"].insert_one(datos)
    datos.pop("_id", None)
    return {"mensaje": "Reseña guardada"}

@app.put("/hoteles/{hotel_id}/reseñas/{reseña_id}")
def put_reseña(hotel_id: str, reseña_id: str, datos: dict):
    db["reseñas"].update_one(
        {"_id": reseña_id},
        {"$set": {"calificacion": datos["calificacion"], "comentario": datos["comentario"]}}
    )
    return {"mensaje": "Reseña actualizada"}

@app.delete("/hoteles/{hotel_id}/reseñas/{reseña_id}")
def delete_reseña(reseña_id: str, hotel_id: str):
    db["reseñas"].delete_one({"_id": reseña_id})
    return {"mensaje": "Reseña eliminada"}

@app.put("/hoteles/{hotel_id}/reseñas/{reseña_id}/responder")
def responder_reseña(hotel_id: str, reseña_id: str, datos: dict):
    db["reseñas"].update_one(
        {"_id": reseña_id},
        {"$set": {"respuesta": {
            "administrador_id": datos["administrador_id"],
            "mensaje": datos["mensaje"],
            "fecha": datetime.now().isoformat()
        }}}
    )
    return {"mensaje": "Respuesta guardada"}

@app.put("/hoteles/{hotel_id}/reseñas/{reseña_id}/destacar")
def destacar_reseña(hotel_id: str, reseña_id: str):
    db["reseñas"].update_many({"hotel_id": hotel_id}, {"$set": {"destacada": False}})
    db["reseñas"].update_one({"_id": reseña_id}, {"$set": {"destacada": True}})
    return {"mensaje": "Reseña destacada"}

@app.put("/hoteles/{hotel_id}/reseñas/{reseña_id}/moderar")
def moderar_reseña(hotel_id: str, reseña_id: str, datos: dict):
    db["reseñas"].update_one(
        {"_id": reseña_id},
        {"$set": {"visible": datos["visible"]}}
    )
    return {"mensaje": "Reseña moderada"}

@app.put("/hoteles/{hotel_id}/reseñas/{reseña_id}/util")
def votar_util(hotel_id: str, reseña_id: str):
    db["reseñas"].update_one(
        {"_id": reseña_id},
        {"$inc": {"votos_utilidad": 1}}
    )
    return {"mensaje": "Voto registrado"}