"""Central registry for all versioned FastAPI routers."""

from core.apis.routes.approval_routes import router as approval_router
from core.apis.routes.audit_routes import router as audit_router
from core.apis.routes.auth_routes import router as auth_router
from core.apis.routes.dashboard_routes import router as dashboard_router
from core.apis.routes.inbound_routes import router as inbound_router
from core.apis.routes.inventory_routes import router as inventory_router
from core.apis.routes.issue_routes import router as issue_router
from core.apis.routes.master_routes import router as master_router
from core.apis.routes.order_routes import router as order_router

api_routers = (
    auth_router,
    approval_router,
    master_router,
    inventory_router,
    inbound_router,
    order_router,
    issue_router,
    audit_router,
    dashboard_router,
)

__all__ = ["api_routers"]
