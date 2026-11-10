"""API routers, combined into a single ``router`` mounted under ``/api``."""

from fastapi import APIRouter

from app.api.routes import analysis, health, report, resume, review

router = APIRouter()
router.include_router(health.router)
router.include_router(resume.router)
router.include_router(analysis.router)
router.include_router(review.router)
router.include_router(report.router)

__all__ = ["router"]
