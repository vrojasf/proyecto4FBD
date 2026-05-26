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


@app.get("/rfc1/top-hoteles")
def rfc1_top_hoteles():
    pipeline = [
        {"$group": {
            "_id": "$hotel_id",
            "calificacionPromedio": {"$avg": "$calificacion"},
            "totalReseñas": {"$sum": 1}
        }},
        {"$sort": {"calificacionPromedio": -1}},
        {"$limit": 10},
        {"$lookup": {
            "from": "hoteles",
            "localField": "_id",
            "foreignField": "_id",
            "as": "hotel"
        }},
        {"$project": {
            "nombreHotel": {"$arrayElemAt": ["$hotel.nombre", 0]},
            "ciudad": {"$arrayElemAt": ["$hotel.ciudad", 0]},
            "calificacionPromedio": 1,
            "totalReseñas": 1
        }}
    ]
    resultado = list(db["reseñas"].aggregate(pipeline))
    return resultado

@app.get("/rfc2/evolucion/{hotel_id}/{anio}")
def rfc2_evolucion(hotel_id: str, anio: int):
    pipeline = [
        {"$match": {
            "hotel_id": hotel_id,
            "fecha": {"$regex": f"^{anio}"}
        }},
        {"$group": {
            "_id": {"$substr": ["$fecha", 0, 7]},
            "calificacionPromedio": {"$avg": "$calificacion"},
            "totalReseñas": {"$sum": 1}
        }},
        {"$sort": {"_id": 1}},
        {"$project": {
            "mes": "$_id",
            "calificacionPromedio": 1,
            "totalReseñas": 1
        }}
    ]
    resultado = list(db["reseñas"].aggregate(pipeline))
    return resultado

@app.get("/rfc3/comparativo/{ciudad}")
def rfc3_comparativo(ciudad: str):
    pipeline = [
        {"$lookup": {
            "from": "hoteles",
            "localField": "hotel_id",
            "foreignField": "_id",
            "as": "hotel"
        }},
        {"$match": {"hotel.ciudad": ciudad}},
        {"$group": {
            "_id": "$hotel_id",
            "calificacionPromedio": {"$avg": "$calificacion"},
            "totalReseñas": {"$sum": 1},
            "conRespuesta": {"$sum": {"$cond": [{"$ifNull": ["$respuesta", False]}, 1, 0]}},
            "destacadas": {"$sum": {"$cond": ["$destacada", 1, 0]}},
            "nombreHotel": {"$first": {"$arrayElemAt": ["$hotel.nombre", 0]}}
        }},
        {"$project": {
            "nombreHotel": 1,
            "calificacionPromedio": 1,
            "totalReseñas": 1,
            "pctConRespuesta": {"$multiply": [{"$divide": ["$conRespuesta", "$totalReseñas"]}, 100]},
            "pctDestacadas": {"$multiply": [{"$divide": ["$destacadas", "$totalReseñas"]}, 100]}
        }}
    ]
    resultado = list(db["reseñas"].aggregate(pipeline))
    return resultado

@app.post("/hoteles/{hotel_id}/resenas")
def post_resena(hotel_id: str, datos: dict):
    existe = db["resenas"].find_one({
        "reserva_id": datos.get("reserva_id")
    })
    if existe:
        return {"error": "Ya existe una reseña para esta reserva"}
    
    datos["hotel_id"] = hotel_id
    datos["fecha"] = datetime.now().isoformat()
    datos["visible"] = True
    datos["destacada"] = False
    datos["votos_utilidad"] = 0
    db["resenas"].insert_one(datos)
    datos.pop("_id", None)
    return {"mensaje": "Reseña guardada"}

@app.get("/hoteles/{hotel_id}/resenas")
def get_resenas(hotel_id: str):
    resenas = list(db["resenas"].find({"hotel_id": hotel_id}, {"_id": 0}))
    return resenas

@app.put("/hoteles/{hotel_id}/resenas/{resena_id}")
def put_resena(hotel_id: str, resena_id: str, datos: dict):
    db["resenas"].update_one(
        {"reserva_id": resena_id},
        {"$set": {"calificacion": datos["calificacion"], "comentario": datos["comentario"]}}
    )
    return {"mensaje": "Reseña actualizada"}

@app.delete("/hoteles/{hotel_id}/resenas/{resena_id}")
def delete_resena(hotel_id: str, resena_id: str):
    db["resenas"].delete_one({"reserva_id": resena_id})
    return {"mensaje": "Reseña eliminada"}

@app.put("/hoteles/{hotel_id}/resenas/{resena_id}/util")
def votar_util_resena(hotel_id: str, resena_id: str):
    db["resenas"].update_one(
        {"reserva_id": resena_id},
        {"$inc": {"votos_utilidad": 1}}
    )
    return {"mensaje": "Voto registrado"}

@app.put("/hoteles/{hotel_id}/resenas/{resena_id}/responder")
def responder_resena(hotel_id: str, resena_id: str, datos: dict):
    db["resenas"].update_one(
        {"reserva_id": resena_id},
        {"$set": {"respuesta": {
            "administrador_id": datos["administrador_id"],
            "mensaje": datos["mensaje"],
            "fecha": datetime.now().isoformat()
        }}}
    )
    return {"mensaje": "Respuesta guardada"}

@app.put("/hoteles/{hotel_id}/resenas/{resena_id}/destacar")
def destacar_resena(hotel_id: str, resena_id: str):
    db["resenas"].update_many({"hotel_id": hotel_id}, {"$set": {"destacada": False}})
    db["resenas"].update_one({"reserva_id": resena_id}, {"$set": {"destacada": True}})
    return {"mensaje": "Reseña destacada"}

@app.put("/hoteles/{hotel_id}/resenas/{resena_id}/moderar")
def moderar_resena(hotel_id: str, resena_id: str, datos: dict):
    db["resenas"].update_one(
        {"reserva_id": resena_id},
        {"$set": {"visible": datos["visible"]}}
    )
    return {"mensaje": "Reseña moderada"}

@app.get("/clientes/{cliente_id}/resenas")
def get_resenas_cliente(cliente_id: str):
    resenas = list(db["resenas"].find({"cliente_id": cliente_id}, {"_id": 0}))
    return resenas