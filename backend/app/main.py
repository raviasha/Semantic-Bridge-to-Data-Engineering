from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import interviews, schema, sql_generation

app = FastAPI(
    title="Semantic Bridge",
    description="Eliminating translation lag between domain experts and data engineers",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(interviews.router, prefix="/api/interviews", tags=["interviews"])
app.include_router(schema.router, prefix="/api/schema", tags=["schema"])
app.include_router(sql_generation.router, prefix="/api/generate", tags=["generation"])


@app.get("/api/health")
async def health():
    return {"status": "ok", "version": "0.1.0"}
