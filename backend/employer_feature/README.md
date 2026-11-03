# NexAbility Employer Feature (Isolated)

## Purpose
This folder contains **new employer‑side functionality** that lives completely outside the existing `backend/app/` codebase.  All code is self‑contained so the current candidate‑side implementation remains untouched.

## How to integrate
1. **Import the routers** in `backend/app/main.py` (or wherever the global `api_router` is assembled) when the team is ready:
```python
from backend.employer_feature.api.job_posting import router as job_router
from backend.employer_feature.api.candidate_view import router as candidate_view_router
from backend.employer_feature.api.accommodation import router as accommodation_router

app.include_router(job_router, prefix="/api/v1")
app.include_router(candidate_view_router, prefix="/api/v1")
app.include_router(accommodation_router, prefix="/api/v1")
```
2. **Run migrations** only if the new models (`JobPosting`, `AccommodationRequest`) are added to the database.  Until that step the API will return **404** for the new endpoints.
3. Front‑end can start importing the services under `frontend/src/features/employer/` – they will hit the same URLs as the routers above.

## Folder structure
```
backend/employer_feature/
├─ api/                # FastAPI routers (job posting, candidate view, accommodation requests)
├─ models/             # New SQLAlchemy models (requires migration)
├─ schemas/            # Pydantic request/response models
├─ services/           # Business‑logic helpers
├─ tests/              # Isolated pytest suite
└─ README.md
```

**Only add code here** – do **not** edit any file under `backend/app/`.

