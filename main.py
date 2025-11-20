import os
from typing import Dict, Any, List, Type, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from bson import ObjectId

from database import db, create_document, get_documents
from schemas import (
    Receptionist,
    Doctor,
    Patient,
    Procedure,
    Appointment,
    Payment,
    Report,
    Consumable,
)

app = FastAPI(title="Dental Clinic Suite API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ----------------------------------------------------------
# Utilities
# ----------------------------------------------------------

def serialize_doc(doc: Dict[str, Any]) -> Dict[str, Any]:
    if not doc:
        return doc
    doc = dict(doc)
    if isinstance(doc.get("_id"), ObjectId):
        doc["_id"] = str(doc["_id"])
    # Convert nested ObjectIds if any
    for k, v in list(doc.items()):
        if isinstance(v, ObjectId):
            doc[k] = str(v)
    return doc

MODEL_MAP: Dict[str, Type[BaseModel]] = {
    "receptionist": Receptionist,
    "doctor": Doctor,
    "patient": Patient,
    "procedure": Procedure,
    "appointment": Appointment,
    "payment": Payment,
    "report": Report,
    "consumable": Consumable,
}

# ----------------------------------------------------------
# Root & Health
# ----------------------------------------------------------

@app.get("/")
def read_root():
    return {"message": "Dental Clinic Suite Backend is running"}

@app.get("/test")
def test_database():
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": [],
    }

    try:
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
            response["database_name"] = getattr(db, "name", "") or "✅ Connected"
            response["connection_status"] = "Connected"
            try:
                response["collections"] = db.list_collection_names()[:20]
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️ Connected but Error: {str(e)[:100]}"
        else:
            response["database"] = "⚠️ Available but not initialized"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:100]}"

    return response

# ----------------------------------------------------------
# Schema Introspection for Viewer
# ----------------------------------------------------------

@app.get("/schema")
def get_schema_definitions():
    defs = {}
    for name, model in MODEL_MAP.items():
        defs[name] = model.model_json_schema()
    return defs

# ----------------------------------------------------------
# Generic CRUD Endpoints per collection
# ----------------------------------------------------------

@app.get("/api/{collection}")
def list_documents(collection: str, limit: int = 100):
    collection = collection.lower()
    if collection not in MODEL_MAP:
        raise HTTPException(status_code=404, detail="Collection not found")
    docs = get_documents(collection, {}, min(limit, 500))
    return [serialize_doc(d) for d in docs]

@app.get("/api/{collection}/{doc_id}")
def get_document(collection: str, doc_id: str):
    collection = collection.lower()
    if collection not in MODEL_MAP:
        raise HTTPException(status_code=404, detail="Collection not found")
    try:
        doc = db[collection].find_one({"_id": ObjectId(doc_id)})
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid id")
    if not doc:
        raise HTTPException(status_code=404, detail="Not found")
    return serialize_doc(doc)

@app.post("/api/{collection}")
def create_new_document(collection: str, payload: dict):
    collection = collection.lower()
    if collection not in MODEL_MAP:
        raise HTTPException(status_code=404, detail="Collection not found")
    Model = MODEL_MAP[collection]
    try:
        validated: BaseModel = Model(**payload)
    except Exception as e:
        raise HTTPException(status_code=422, detail=str(e))
    inserted_id = create_document(collection, validated)
    doc = db[collection].find_one({"_id": ObjectId(inserted_id)})
    return serialize_doc(doc)

@app.put("/api/{collection}/{doc_id}")
def update_document(collection: str, doc_id: str, payload: dict):
    collection = collection.lower()
    if collection not in MODEL_MAP:
        raise HTTPException(status_code=404, detail="Collection not found")
    Model = MODEL_MAP[collection]
    try:
        # Allow partial updates: validate by merging existing with payload
        existing = db[collection].find_one({"_id": ObjectId(doc_id)})
        if not existing:
            raise HTTPException(status_code=404, detail="Not found")
        merged = {k: v for k, v in existing.items() if k != "_id"}
        merged.update(payload)
        Model(**merged)  # validate
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=422, detail=str(e))

    res = db[collection].update_one({"_id": ObjectId(doc_id)}, {"$set": payload})
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="Not found")
    updated = db[collection].find_one({"_id": ObjectId(doc_id)})
    return serialize_doc(updated)

@app.delete("/api/{collection}/{doc_id}")
def delete_document(collection: str, doc_id: str):
    collection = collection.lower()
    if collection not in MODEL_MAP:
        raise HTTPException(status_code=404, detail="Collection not found")
    try:
        res = db[collection].delete_one({"_id": ObjectId(doc_id)})
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid id")
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Not found")
    return {"deleted": True, "id": doc_id}


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
