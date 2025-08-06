import asyncio
from fastapi import FastAPI, File, UploadFile, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from rembg import remove
from PIL import Image
import io
import os

# --- グローバル設定 ---
API_KEY_SECRET = os.environ.get("API_KEY_SECRET", "snapy-special-secret-2025")
MAX_FILE_SIZE = 15 * 1024 * 1024  # 15MB
MAX_RESOLUTION = 4000 * 4000      # 16メガピクセル
PROCESSING_TIMEOUT = 90.0         # 90秒

# ★★★ モデルを最も軽量な u2netp 一本に絞る ★★★
STABLE_MODEL = "u2netp"

app = FastAPI(title="Snapy Background Remover")

# --- CORS設定 ---
origins = [
    "https://empathywriting.com",
    "http://localhost",
    "http://localhost:8080",
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/", tags=["General"])
def read_root():
    return {"message": "Snapy Background Remover API is running."}

@app.post("/remove-background/", tags=["Image Processing"])
async def process_image(
    file: UploadFile = File(...),
    x_api_key: str = Header(None)
):
    print("--- Request received ---")
    if x_api_key != API_KEY_SECRET:
        raise HTTPException(status_code=401, detail="Unauthorized")

    if file.size > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail=f"ファイルサイズが上限({MAX_FILE_SIZE // 1024 // 1024}MB)を超えています。")

    try:
        input_bytes = await file.read()
        with Image.open(io.BytesIO(input_bytes)) as img:
            if img.width * img.height > MAX_RESOLUTION:
                raise HTTPException(status_code=413, detail="画像の解像度が高すぎます。")
    except Exception:
        raise HTTPException(status_code=400, detail="無効な画像ファイルです。")

    print(f"--- Starting background removal with stable model: {STABLE_MODEL} ---")
    try:
        output_bytes = await asyncio.wait_for(
            asyncio.to_thread(remove, input_bytes, session_factory=lambda: new_session(STABLE_MODEL)),
            timeout=PROCESSING_TIMEOUT
        )
        print("--- Background removal complete. Sending response. ---")
        return StreamingResponse(io.BytesIO(output_bytes), media_type="image/png")
    except asyncio.TimeoutError:
        print("--- ERROR: Processing timed out. ---")
        raise HTTPException(status_code=504, detail="処理がタイムアウトしました。")
    except Exception as e:
        print(f"--- ERROR: An unexpected error occurred: {e} ---")
        raise HTTPException(status_code=500, detail="サーバー内部でエラーが発生しました。")
