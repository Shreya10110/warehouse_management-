from datetime import datetime, timezone

from core.exceptions import AppError
from core.security import hash_password
from cruds.base_crud import CRUDRepository
from cruds.user_crud import create_user, find_user_by_email, find_user_by_id, list_users, update_user
from models.product_model import Product
from models.seller_model import Seller
from models.user_model import User
from models.warehouse_model import Warehouse
from schemas.domain_schemas import ProductCreate, StatusRequest, WarehouseCreate
from schemas.user_schemas import UserCreate, UserUpdate
from services.audit_service import record
from services.auth_service import public_user

warehouse_repo = CRUDRepository("warehouses")
product_repo = CRUDRepository("products")
seller_repo = CRUDRepository("sellers")


async def create_warehouse(payload: WarehouseCreate, user: User) -> dict:
    """Create a uniquely coded warehouse for the owner."""
    code = payload.warehouse_code.strip().upper()
    if await warehouse_repo.find_one({"warehouse_code": code}):
        raise AppError(409, "DUPLICATE_WAREHOUSE_CODE", "Warehouse code already exists.")
    created = await warehouse_repo.create(Warehouse(**(payload.model_dump() | {"warehouse_code": code})).to_document())
    await record(user, "CREATE", "WAREHOUSE", created["id"], created["id"], new=created)
    return created


async def list_warehouses(user: User, search: str | None = None, is_active: bool | None = None, skip: int = 0, limit: int = 100) -> list[dict]:
    """List all warehouses for owners or only the logged-in user's warehouse."""
    query = {} if user.role.value == "OWNER" else {"_id": __import__("bson").ObjectId(user.warehouse_id)}
    if search:
        query["$or"] = [{"name": {"$regex": search, "$options": "i"}}, {"warehouse_code": {"$regex": search, "$options": "i"}}, {"city": {"$regex": search, "$options": "i"}}]
    if is_active is not None:
        query["is_active"] = is_active
    return await warehouse_repo.list(query, limit=limit, skip=skip)


async def get_warehouse(record_id: str, user: User) -> dict:
    """Read a warehouse while enforcing staff warehouse isolation."""
    if user.role.value != "OWNER" and record_id != user.warehouse_id:
        raise AppError(403, "FORBIDDEN", "You cannot access another warehouse.")
    item = await warehouse_repo.get(record_id)
    if not item:
        raise AppError(404, "WAREHOUSE_NOT_FOUND", "Warehouse was not found.")
    return item


async def update_warehouse(record_id: str, values: dict, user: User) -> dict:
    """Update warehouse master data and create an audit event."""
    old = await warehouse_repo.get(record_id)
    if not old:
        raise AppError(404, "WAREHOUSE_NOT_FOUND", "Warehouse was not found.")
    manager_id = values.get("manager_id")
    if manager_id:
        manager = await find_user_by_id(manager_id)
        if not manager or manager.role.value != "MANAGER" or manager.warehouse_id != record_id:
            raise AppError(400, "INVALID_MANAGER_ASSIGNMENT", "Manager must be assigned to this warehouse.")
    values["updated_at"] = datetime.now(timezone.utc)
    updated = await warehouse_repo.update(record_id, values)
    await record(user, "UPDATE", "WAREHOUSE", record_id, record_id, old, updated)
    return updated


async def create_product(payload: ProductCreate, user: User) -> dict:
    """Create a globally unique SKU master record."""
    sku = payload.sku.strip().upper()
    barcode = payload.barcode.strip() if payload.barcode and payload.barcode.strip() else None
    if await product_repo.find_one({"sku": sku}):
        raise AppError(409, "DUPLICATE_SKU", "SKU already exists.")
    if barcode and await product_repo.find_one({"barcode": barcode}):
        raise AppError(409, "DUPLICATE_BARCODE", "Barcode already belongs to another product.")
    created = await product_repo.create(Product(**(payload.model_dump() | {"sku": sku, "barcode": barcode})).to_document())
    await record(user, "CREATE", "PRODUCT", created["id"], None, new=created)
    return created


async def create_seller(payload, user: User) -> dict:
    """Create a uniquely coded seller or supplier master record."""
    code = payload.seller_code.strip().upper()
    if await seller_repo.find_one({"seller_code": code}):
        raise AppError(409, "DUPLICATE_SELLER_CODE", "Seller code already exists.")
    created = await seller_repo.create(Seller(**(payload.model_dump() | {"seller_code": code})).to_document())
    await record(user, "CREATE", "SELLER", created["id"], None, new=created)
    return created


async def create_team_user(payload: UserCreate, owner: User) -> dict:
    """Create warehouse staff after verifying the assigned warehouse exists."""
    if payload.role.value == "OWNER":
        raise AppError(400, "INVALID_ROLE", "Additional owner creation is not supported here.")
    if not await warehouse_repo.get(payload.warehouse_id):
        raise AppError(404, "WAREHOUSE_NOT_FOUND", "Assigned warehouse was not found.")
    if await find_user_by_email(str(payload.email)):
        raise AppError(409, "DUPLICATE_EMAIL", "A user with this email already exists.")
    model = User(**payload.model_dump(exclude={"password"}), password_hash=hash_password(payload.password))
    await create_user(model)
    result = public_user(model).model_dump(mode="json")
    await record(owner, "CREATE", "USER", model.id, payload.warehouse_id, new=result)
    return result


async def get_team_user(record_id: str, current: User) -> dict:
    """Read a user while enforcing owner or same-warehouse visibility."""
    user = await find_user_by_id(record_id)
    if not user:
        raise AppError(404, "USER_NOT_FOUND", "User was not found.")
    if current.role.value != "OWNER" and user.warehouse_id != current.warehouse_id:
        raise AppError(403, "FORBIDDEN", "You cannot access another warehouse's team.")
    return public_user(user).model_dump(mode="json")


async def list_team(current: User, warehouse_id: str | None = None, role: str | None = None, search: str | None = None, skip: int = 0, limit: int = 100) -> list[dict]:
    """List company users for owners or the current warehouse team for staff."""
    effective = warehouse_id if current.role.value == "OWNER" else current.warehouse_id
    query = {"warehouse_id": effective} if effective else {}
    if role:
        query["role"] = role
    if search:
        query["$or"] = [{"first_name": {"$regex": search, "$options": "i"}}, {"last_name": {"$regex": search, "$options": "i"}}, {"email": {"$regex": search, "$options": "i"}}]
    users = await list_users(query)
    return [public_user(user).model_dump(mode="json") for user in users[skip:skip + min(limit, 500)]]


async def set_user_status(record_id: str, payload: StatusRequest, current: User) -> dict:
    """Activate or deactivate a staff account and audit the change."""
    old = await get_team_user(record_id, current)
    updated = await update_user(record_id, {"is_active": payload.is_active, "updated_at": datetime.now(timezone.utc)})
    result = public_user(updated).model_dump(mode="json")
    await record(current, "STATUS", "USER", record_id, updated.warehouse_id, old, result)
    return result


async def update_team_user(record_id: str, payload: UserUpdate, current: User) -> dict:
    """Update a staff profile and validated warehouse assignment."""
    old = await get_team_user(record_id, current)
    if not await warehouse_repo.get(payload.warehouse_id):
        raise AppError(404, "WAREHOUSE_NOT_FOUND", "Assigned warehouse was not found.")
    duplicate = await find_user_by_email(str(payload.email))
    if duplicate and duplicate.id != record_id:
        raise AppError(409, "DUPLICATE_EMAIL", "A user with this email already exists.")
    updated = await update_user(record_id, payload.model_dump() | {"email": str(payload.email).lower(), "updated_at": datetime.now(timezone.utc)})
    if not updated:
        raise AppError(404, "USER_NOT_FOUND", "User was not found.")
    result = public_user(updated).model_dump(mode="json")
    await record(current, "UPDATE", "USER", record_id, updated.warehouse_id, old, result)
    return result
