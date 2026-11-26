"""API routers, combined into a single ``router`` mounted under ``/api``."""

from fastapi import APIRouter, Depends

from app.api.routes import analysis, auth, health, report, resume, review
from app.api.routes.auth import require_sign_in

router = APIRouter()
router.include_router(health.router)
router.include_router(auth.router)

# Everything that reads or writes user data, or calls Claude, needs a Google sign-in when GOOGLE_CLIENT_ID is set.
protected = APIRouter(dependencies=[Depends(require_sign_in)])
protected.include_router(resume.router)
protected.include_router(analysis.router)
protected.include_router(review.router)
protected.include_router(report.router)
router.include_router(protected)

__all__ = ["router"]
