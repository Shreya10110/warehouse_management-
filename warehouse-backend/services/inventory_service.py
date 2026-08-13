from datetime import datetime, timezone

from core.exceptions import AppError
from cruds.base_crud import CRUDRepository
from models.inventory_model import Inventory
from models.inventory_transaction_model import InventoryTransaction
from models.user_model import User
from services.audit_service import record

inventory_repo = CRUDRepository("inventory")
transaction_repo = CRUDRepository("inventory_transactions")
product_repo = CRUDRepository("products")


def available(item: dict) -> int:
    """Calculate available units from a serialized inventory record."""
    return item.get("on_hand_quantity", 0) - item.get("reserved_quantity", 0) - item.get("damaged_quantity", 0) - item.get("quarantine_quantity", 0)


async def get_or_create(warehouse_id: str, sku: str) -> dict:
    """Return a warehouse SKU inventory record, creating a zero balance when absent."""
    item = await inventory_repo.find_one({"warehouse_id": warehouse_id, "sku": sku})
    if item:
        return item
    product = await product_repo.find_one({"sku": sku})
    if not product:
        raise AppError(404, "PRODUCT_NOT_FOUND", f"Product {sku} was not found.")
    model = Inventory(warehouse_id=warehouse_id, product_id=product["id"], sku=sku)
    return await inventory_repo.create(model.to_document())


async def change_quantities(warehouse_id: str, sku: str, changes: dict[str, int], transaction_type: str, reference_type: str, reference_id: str, user: User, transaction_quantity: int | None = None) -> dict:
    """Apply validated stock changes and create transaction and audit history."""
    item = await get_or_create(warehouse_id, sku)
    before = {key: item.get(key, 0) for key in ("on_hand_quantity", "reserved_quantity", "damaged_quantity", "quarantine_quantity")}
    after = {key: before[key] + changes.get(key, 0) for key in before}
    if any(value < 0 for value in after.values()) or after["reserved_quantity"] > after["on_hand_quantity"]:
        raise AppError(400, "INVALID_QUANTITY", "Inventory quantities cannot become invalid or negative.")
    after["updated_at"] = datetime.now(timezone.utc)
    updated = await inventory_repo.update(item["id"], after)
    transaction = InventoryTransaction(
        warehouse_id=warehouse_id, sku=sku, transaction_type=transaction_type,
        quantity=transaction_quantity if transaction_quantity is not None else sum(abs(value) for value in changes.values()), before_values=before,
        after_values={key: after[key] for key in before}, reference_type=reference_type,
        reference_id=reference_id, performed_by=user.id,
    )
    await transaction_repo.create(transaction.to_document())
    await record(user, transaction_type, "INVENTORY", item["id"], warehouse_id, before, after, {"sku": sku, "reference_id": reference_id})
    updated["available_quantity"] = available(updated)
    return updated


async def record_transaction(warehouse_id: str, sku: str, transaction_type: str, quantity: int, reference_type: str, reference_id: str, user: User) -> dict:
    """Record history for inventory already changed inside a wider database transaction."""
    item = await get_or_create(warehouse_id, sku)
    values = {key: item.get(key, 0) for key in ("on_hand_quantity", "reserved_quantity", "damaged_quantity", "quarantine_quantity")}
    transaction = InventoryTransaction(
        warehouse_id=warehouse_id, sku=sku, transaction_type=transaction_type, quantity=quantity,
        before_values=values | {"reserved_quantity": values["reserved_quantity"] - quantity},
        after_values=values, reference_type=reference_type, reference_id=reference_id, performed_by=user.id,
    )
    await transaction_repo.create(transaction.to_document())
    return await record(user, transaction_type, "INVENTORY", item["id"], warehouse_id, transaction.before_values, values, {"sku": sku, "reference_id": reference_id})


async def list_inventory(user: User, warehouse_id: str | None = None, search: str | None = None, sku: str | None = None, category: str | None = None, low_stock: bool = False, damaged: bool = False, quarantine: bool = False) -> list[dict]:
    """List inventory while enforcing logged-in warehouse isolation."""
    effective_warehouse = warehouse_id if user.role.value == "OWNER" else user.warehouse_id
    if user.role.value != "OWNER" and warehouse_id and warehouse_id != user.warehouse_id:
        raise AppError(403, "FORBIDDEN", "You cannot access another warehouse.")
    query = {"warehouse_id": effective_warehouse} if effective_warehouse else {}
    if search:
        query["sku"] = {"$regex": search, "$options": "i"}
    if sku:
        query["sku"] = sku.strip().upper()
    if category:
        products = await product_repo.list({"category": {"$regex": f"^{category}$", "$options": "i"}})
        query["sku"] = {"$in": [product["sku"] for product in products]}
    if damaged:
        query["damaged_quantity"] = {"$gt": 0}
    if quarantine:
        query["quarantine_quantity"] = {"$gt": 0}
    items = await inventory_repo.list(query)
    for item in items:
        item["available_quantity"] = available(item)
    if low_stock:
        items = [item for item in items if item["available_quantity"] <= 10]
    return items
