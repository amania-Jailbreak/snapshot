import os
import uuid
from fastapi import FastAPI, File, UploadFile, HTTPException, Depends, Request, status
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.security import APIKeyHeader
from pymongo import MongoClient
from gridfs import GridFS
from cryptography.fernet import Fernet, InvalidToken
from dotenv import load_dotenv
from bson import ObjectId

load_dotenv()


MONGO_URI = os.getenv("MONGO_URI", None)
client = MongoClient(MONGO_URI)
db = client[os.getenv("MONGO_DB", None)]
is_allow_register = os.getenv("ALLOW_REGISTER", "true").lower() == "true"
fs = GridFS(db)

app = FastAPI()


# アップロード/ダウンロードAPIキー認証
UPLOAD_KEY_HEADER = "X-Upload-Key"
DOWNLOAD_KEY_HEADER = "X-Download-Key"
upload_key_header = APIKeyHeader(name=UPLOAD_KEY_HEADER, auto_error=False)
download_key_header = APIKeyHeader(name=DOWNLOAD_KEY_HEADER, auto_error=False)


def get_user_by_uploadkey(api_key: str):
    return db.users.find_one({"upload_key": api_key})


def get_user_by_downloadkey(api_key: str):
    return db.users.find_one({"download_key": api_key})


async def require_upload_key(api_key: str = Depends(upload_key_header)):
    if not api_key:
        raise HTTPException(status_code=401, detail="Upload key required")
    user = get_user_by_uploadkey(api_key)
    if not user:
        raise HTTPException(status_code=403, detail="Invalid upload key")
    return user


async def require_download_key(api_key: str = Depends(download_key_header)):
    if not api_key:
        raise HTTPException(status_code=401, detail="Download key required")
    user = get_user_by_downloadkey(api_key)
    if not user:
        raise HTTPException(status_code=403, detail="Invalid download key")
    return user


# ユーザー登録（アップロード・ダウンロードキー両方発行）
@app.post("/register")
async def register(username: str, discord_id: str):
    if db.users.find_one({"discord_id": discord_id}):
        raise HTTPException(status_code=409, detail="Discord ID already registered")
    if not is_allow_register:
        raise HTTPException(status_code=403, detail="Registration is disabled")
    upload_key = Fernet.generate_key().decode()
    download_key = Fernet.generate_key().decode()
    db.users.insert_one(
        {
            "username": username,
            "discord_id": discord_id,
            "upload_key": upload_key,
            "download_key": download_key,
        }
    )
    return {"upload_key": upload_key, "download_key": download_key}


def get_fernet(api_key: str):
    return Fernet(api_key.encode())


# アップロードAPI（アップロードキー認証）
@app.post("/file")
async def upload_file(file: UploadFile = File(...), user=Depends(require_upload_key)):
    api_key = user["upload_key"]
    fernet = get_fernet(api_key)
    raw = await file.read()
    encrypted = fernet.encrypt(raw)
    file_id = fs.put(encrypted, filename=file.filename, owner=user["_id"])
    return {"fileID": str(file_id)}


# ダウンロードAPI（ダウンロードキー認証）
@app.get("/file")
async def get_file(id: str, user=Depends(require_download_key)):
    try:
        gridout = fs.get(ObjectId(id))
    except Exception:
        raise HTTPException(status_code=404, detail="File not found")
    if gridout.owner != user["_id"]:
        raise HTTPException(status_code=403, detail="Forbidden")
    api_key = user["download_key"]
    fernet = get_fernet(api_key)
    try:
        decrypted = fernet.decrypt(gridout.read())
    except InvalidToken:
        raise HTTPException(status_code=403, detail="Decryption failed")
    return StreamingResponse(
        iter([decrypted]),
        media_type="application/octet-stream",
        headers={"Content-Disposition": f"attachment; filename={gridout.filename}"},
    )


# 削除API（アップロードキー認証）
@app.delete("/file")
async def delete_file(id: str, user=Depends(require_upload_key)):

    try:
        gridout = fs.get(ObjectId(id))
    except Exception:
        raise HTTPException(status_code=404, detail="File not found")
    if gridout.owner != user["_id"]:
        raise HTTPException(status_code=403, detail="Forbidden")
    try:
        fs.delete(ObjectId(id))
        return JSONResponse(status_code=200, content={"detail": "Deleted"})
    except Exception:
        return JSONResponse(status_code=503, content={"detail": "Delete failed"})


# 更新API（アップロードキー認証）
@app.put("/file")
async def update_file(
    id: str, file: UploadFile = File(...), user=Depends(require_upload_key)
):

    try:
        gridout = fs.get(ObjectId(id))
    except Exception:
        raise HTTPException(status_code=404, detail="File not found")
    if gridout.owner != user["_id"]:
        raise HTTPException(status_code=403, detail="Forbidden")
    try:
        fs.delete(ObjectId(id))
    except Exception:
        return JSONResponse(status_code=503, content={"detail": "Delete failed"})
    api_key = user["api_key"]
    fernet = get_fernet(api_key)
    raw = await file.read()
    encrypted = fernet.encrypt(raw)
    new_id = fs.put(encrypted, filename=file.filename, owner=user["_id"])
    return {"fileID": str(new_id)}


@app.get("/files")
async def list_files(user=Depends(require_upload_key)):
    files = db.fs.files.find({"owner": user["_id"]})
    result = [{"fileID": str(f["_id"]), "filename": f["filename"]} for f in files]
    return result


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=5001)
