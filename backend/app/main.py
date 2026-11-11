# 	Tạo ứng dụng FastAPI và gắn các API vào ứng dụng
from fastapi import FastAPI
from app.api.router import api_router
from app.storage.static_media import register_static_media
app = FastAPI(title="HSK AI Backend")
app.include_router(api_router)
register_static_media(app)

@app.get("/")
def root():
    return {"message": "Backend HSK đang hoạt động"}