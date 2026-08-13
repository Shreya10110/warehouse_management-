from fastapi import APIRouter, Depends, Query

from controllers.inventory_controller import adjust, history
from dependencies.auth import get_current_user, require_owner_or_manager
from models.user_model import User
from schemas.domain_schemas import InventoryAdjustment
from services.inventory_service import inventory_repo, list_inventory

router = APIRouter(tags=["Inventory"])


@router.get("/inventory")
async def inventory(search: str | None = None, sku: str | None = None, category: str | None = None, warehouse: str | None = None, low_stock: bool = False, damaged: bool = False, quarantine: bool = False, user: User = Depends(get_current_user)):
    """List filtered inventory visible to the logged-in user."""
    return await list_inventory(user, warehouse_id=warehouse, search=search, sku=sku, category=category, low_stock=low_stock, damaged=damaged, quarantine=quarantine)


@router.get("/inventory/{sku}")
async def inventory_sku(sku: str, user: User = Depends(get_current_user)):
    """List visible inventory balances for one SKU."""
    return [item for item in await list_inventory(user) if item["sku"] == sku.upper()]


@router.get("/warehouses/{warehouse_id}/inventory")
async def warehouse_inventory(warehouse_id: str, user: User = Depends(get_current_user)):
    """List inventory for one authorized warehouse."""
    return await list_inventory(user, warehouse_id=warehouse_id)


@router.get("/warehouses/{warehouse_id}/inventory/{sku}")
async def warehouse_inventory_sku(warehouse_id: str, sku: str, user: User = Depends(get_current_user)):
    """Read a warehouse inventory balance for one SKU."""
    items = await list_inventory(user, warehouse_id=warehouse_id)
    return next((item for item in items if item["sku"] == sku.upper()), None)


@router.post("/inventory/adjust")
async def inventory_adjust(payload: InventoryAdjustment, user: User = Depends(require_owner_or_manager)):
    """Apply an authorized manual inventory adjustment."""
    return await adjust(payload, user)


@router.get("/inventory-transactions")
async def transactions(user: User = Depends(get_current_user)):
    """List inventory movement history visible to the user."""
    return await history(user)
