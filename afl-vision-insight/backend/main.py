# main.py
from dotenv import load_dotenv
load_dotenv()
from fastapi import FastAPI
from routes import upload, inference, metrics
from config.cors import add_cors
from storage import init_db  # <-- add this

app = FastAPI(title="AFL Vision Backend", version="1.0.0")

# init database
init_db()  # <-- ensure the 'uploads' table exists

add_cors(app)

@app.middleware("http")
async def api_version_header(request, call_next):
    resp = await call_next(request)
    resp.headers["X-API-Version"] = "1"
    return resp

@app.get("/")
def read_root():
    return {"message": "AFL Vision Backend Running"}

app.include_router(upload.router,   prefix="/api/v1/upload",   tags=["Upload"])
app.include_router(inference.router, prefix="/api/v1/inference", tags=["Inference"])
app.include_router(metrics.router,   prefix="/api/v1/metrics",  tags=["Metrics"])
