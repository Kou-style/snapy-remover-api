import asyncio
from fastapi import FastAPI, File, UploadFile, Form, HTTPException, Header
from fastapi.responses import StreamingResponse
from rembg import remove, new_session
from PIL import Image
import io
import os # osをインポート

# --- グローバル設定 ---
# Renderの環境変数からAPIキーを取得。設定されていなければデフォルト値を使用。
API_KEY_SECRET = os.environ.get("API_KEY_SECRET", "snapy-special-secret-2025")
MAX_FILE_SIZE = 15 * 1024 * 1024  # 15MB
MAX_RESOLUTION = 4000 * 4000      # 16メガピクセル (4000x4000)
PROCESSING_TIMEOUT = 45.0         # 45秒

MODELS = {
    "medium": "u2netp",
    "quality": "u2net_human_seg"
}

app = FastAPI(title="Snapy Background Remover")

@app.get("/", tags=["General"])
def read_root():
    return {"message": "Snapy Background Remover API is running."}

@app.post("/remove-background/", tags=["Image Processing"])
async def process_image(
    file: UploadFile = File(...),
    quality: str = Form("medium"),
    x_api_key: str = Header(None)
):
    if x_api_key != API_KEY_SECRET:
        raise HTTPException(status_code=401, detail="Unauthorized: Invalid API Key")

    if file.size > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail=f"File size exceeds limit.")

    try:
        input_bytes = await file.read()
        with Image.open(io.BytesIO(input_bytes)) as img:
            if img.width * img.height > MAX_RESOLUTION:
                raise HTTPException(status_code=413, detail="Image resolution is too high.")
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid image file.")

    if quality not in MODELS:
        raise HTTPException(status_code=400, detail="Invalid quality setting.")

    selected_model = MODELS[quality]

    try:
        async def remove_bg_task():
            session = new_session(model_name=selected_model)
            return remove(input_bytes, session=session)

        output_bytes = await asyncio.wait_for(remove_bg_task(), timeout=PROCESSING_TIMEOUT)
        return StreamingResponse(io.BytesIO(output_bytes), media_type="image/png")

    except asyncio.TimeoutError:
        raise HTTPException(status_code=504, detail="Processing timed out.")
    except Exception as e:
        print(f"Error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error.")
