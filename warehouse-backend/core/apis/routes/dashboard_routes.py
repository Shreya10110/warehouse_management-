from fastapi import APIRouter, Depends, Query

from core.exceptions import AppError
from dependencies.auth import get_current_user
from models.user_model import User
from services.dashboard_service import global_search, summary

router = APIRouter(tags=["Dashboards and Search"])


@router.get("/dashboard/admin")
async def admin_dashboard(user: User = Depends(get_current_user)):
    """Return company KPIs, warehouse summary and recent activity for owners."""
    if user.role.value != "OWNER":
        raise AppError(403, "FORBIDDEN", "The admin dashboard is owner-only.")
    return await summary(user, "admin")


@router.get("/dashboard/manager")
async def manager_dashboard(user: User = Depends(get_current_user)):
    """Return assigned-warehouse KPIs and activity for managers."""
    if user.role.value != "MANAGER":
        raise AppError(403, "FORBIDDEN", "The manager dashboard is manager-only.")
    return await summary(user, "manager")


@router.get("/dashboard/inbound")
async def inbound_dashboard(user: User = Depends(get_current_user)):
    """Return today's receiving workload and assigned warehouse information."""
    if user.role.value != "INBOUND":
        raise AppError(403, "FORBIDDEN", "The inbound dashboard is inbound-only.")
    return await summary(user, "inbound")


@router.get("/dashboard/outbound")
async def outbound_dashboard(user: User = Depends(get_current_user)):
    """Return the assigned warehouse outbound fulfillment queue metrics."""
    if user.role.value != "OUTBOUND":
        raise AppError(403, "FORBIDDEN", "The outbound dashboard is outbound-only.")
    return await summary(user, "outbound")


@router.get("/search")
async def search(q: str = Query(min_length=2), user: User = Depends(get_current_user)):
    """Search permitted warehouse records across operational modules."""
    return await global_search(q, user)
