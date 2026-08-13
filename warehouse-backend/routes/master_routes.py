from fastapi import APIRouter, Depends

from controllers import master_controller
from cruds.base_crud import CRUDRepository
from dependencies.auth import get_current_user, require_owner
from models.user_model import User
from schemas.domain_schemas import ProductCreate, SellerCreate, StatusRequest, WarehouseCreate
from schemas.user_schemas import UserCreate, UserUpdate

router = APIRouter(tags=["Master Data"])
product_repo = CRUDRepository("products")


@router.post("/warehouses")
async def create_warehouse(payload: WarehouseCreate, user: User = Depends(require_owner)):
    """Create a warehouse as the company owner."""
    return await master_controller.create_warehouse(payload, user)


@router.get("/warehouses")
async def list_warehouses(search: str | None = None, is_active: bool | None = None, skip: int = 0, limit: int = 100, user: User = Depends(get_current_user)):
    """List warehouses visible to the logged-in user."""
    return await master_controller.list_warehouses(user, search, is_active, skip, limit)


@router.get("/warehouses/{warehouse_id}")
async def get_warehouse(warehouse_id: str, user: User = Depends(get_current_user)):
    """Read one visible warehouse."""
    return await master_controller.get_warehouse(warehouse_id, user)


@router.put("/warehouses/{warehouse_id}")
async def update_warehouse(warehouse_id: str, payload: WarehouseCreate, user: User = Depends(require_owner)):
    """Replace editable warehouse master fields."""
    return await master_controller.update_warehouse(warehouse_id, payload.model_dump(), user)


@router.patch("/warehouses/{warehouse_id}/status")
async def warehouse_status(warehouse_id: str, payload: StatusRequest, user: User = Depends(require_owner)):
    """Activate or deactivate a warehouse."""
    return await master_controller.update_warehouse(warehouse_id, payload.model_dump(), user)


@router.post("/products")
async def create_product(payload: ProductCreate, user: User = Depends(require_owner)):
    """Create a product SKU as the company owner."""
    return await master_controller.create_product(payload, user)


@router.get("/products")
async def list_products(search: str | None = None, category: str | None = None, is_active: bool | None = None, skip: int = 0, limit: int = 100, _: User = Depends(get_current_user)):
    """List the company-wide product master."""
    query = {}
    if search:
        query["$or"] = [{"sku": {"$regex": search, "$options": "i"}}, {"name": {"$regex": search, "$options": "i"}}]
    if category:
        query["category"] = category
    if is_active is not None:
        query["is_active"] = is_active
    return await product_repo.list(query, limit=limit, skip=skip)


@router.get("/products/{sku}")
async def get_product(sku: str, _: User = Depends(get_current_user)):
    """Read a product by SKU."""
    item = await product_repo.find_one({"sku": sku.upper()})
    if not item:
        from core.exceptions import AppError
        raise AppError(404, "PRODUCT_NOT_FOUND", "Product was not found.")
    return item


@router.put("/products/{sku}")
async def update_product(sku: str, payload: ProductCreate, user: User = Depends(require_owner)):
    """Update product master data by SKU."""
    item = await product_repo.find_one({"sku": sku.upper()})
    if not item:
        from core.exceptions import AppError
        raise AppError(404, "PRODUCT_NOT_FOUND", "Product was not found.")
    return await product_repo.update(item["id"], payload.model_dump() | {"sku": sku.upper()})


@router.patch("/products/{sku}/status")
async def product_status(sku: str, payload: StatusRequest, _: User = Depends(require_owner)):
    """Activate or deactivate a product SKU."""
    item = await product_repo.find_one({"sku": sku.upper()})
    if not item:
        from core.exceptions import AppError
        raise AppError(404, "PRODUCT_NOT_FOUND", "Product was not found.")
    return await product_repo.update(item["id"], payload.model_dump())


@router.post("/sellers")
async def create_seller(payload: SellerCreate, user: User = Depends(require_owner)):
    """Create a seller or supplier master as Admin."""
    return await master_controller.create_seller(payload, user)


@router.get("/sellers")
async def list_sellers(search: str | None = None, is_active: bool | None = None, _: User = Depends(get_current_user)):
    """List approved sellers available for operational documents."""
    query = {}
    if search:
        query["$or"] = [{"seller_code": {"$regex": search, "$options": "i"}}, {"name": {"$regex": search, "$options": "i"}}]
    if is_active is not None:
        query["is_active"] = is_active
    return await master_controller.seller_repo.list(query)


@router.patch("/sellers/{seller_id}/status")
async def seller_status(seller_id: str, payload: StatusRequest, user: User = Depends(require_owner)):
    """Activate or deactivate a seller master record."""
    old = await master_controller.seller_repo.get(seller_id)
    if not old:
        from core.exceptions import AppError
        raise AppError(404, "SELLER_NOT_FOUND", "Seller was not found.")
    updated = await master_controller.seller_repo.update(seller_id, payload.model_dump())
    await master_controller.record(user, "STATUS", "SELLER", seller_id, None, old, updated)
    return updated


@router.post("/users")
async def create_user(payload: UserCreate, user: User = Depends(require_owner)):
    """Create a manager, inbound employee, or outbound employee."""
    return await master_controller.create_team_user(payload, user)


@router.get("/users")
async def users(role: str | None = None, warehouse_id: str | None = None, search: str | None = None, skip: int = 0, limit: int = 100, user: User = Depends(get_current_user)):
    """List users visible to the logged-in identity."""
    return await master_controller.list_team(user, warehouse_id, role, search, skip, limit)


@router.get("/warehouses/{warehouse_id}/users")
async def warehouse_users(warehouse_id: str, user: User = Depends(get_current_user)):
    """List the team assigned to one visible warehouse."""
    return await master_controller.list_team(user, warehouse_id)


@router.get("/users/{user_id}")
async def get_user(user_id: str, user: User = Depends(get_current_user)):
    """Read one visible user record without password fields."""
    return await master_controller.get_team_user(user_id, user)


@router.put("/users/{user_id}")
async def update_user(user_id: str, payload: UserUpdate, user: User = Depends(require_owner)):
    """Update a staff member's profile, role and warehouse assignment."""
    return await master_controller.update_team_user(user_id, payload, user)


@router.patch("/users/{user_id}/status")
async def user_status(user_id: str, payload: StatusRequest, user: User = Depends(require_owner)):
    """Activate or deactivate a team member."""
    return await master_controller.set_user_status(user_id, payload, user)
