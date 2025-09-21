# Commodex Backend

FastAPI app with three endpoints:
- GET /api/v1/materials
- GET /api/v1/prices?material_id=1
- GET /api/v1/forecast?material_id=1&horizon=30

Run locally (if you ever need to):
uvicorn app.main:app --host 0.0.0.0 --port 10000
