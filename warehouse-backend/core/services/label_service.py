import base64
from html import escape
from io import BytesIO

import qrcode


def generate_qr_data_uri(value: str) -> str:
    """Create a PNG QR code data URI for a tracking identifier."""
    image = qrcode.make(value)
    stream = BytesIO()
    image.save(stream, format="PNG")
    return f"data:image/png;base64,{base64.b64encode(stream.getvalue()).decode()}"


def render_shipping_label(package: dict, order: dict, warehouse: dict) -> str:
    """Render a printable label containing customer, warehouse, parcel and QR details."""
    address = ", ".join(escape(str(value)) for value in order["shipping_address"].values())
    warehouse_address = ", ".join(
        escape(str(warehouse.get(key, "")))
        for key in ("address_line_1", "address_line_2", "city", "state", "postal_code", "country")
        if warehouse.get(key)
    )
    qr_uri = generate_qr_data_uri(package["tracking_number"])
    return f"""<!doctype html><html><head><title>{escape(package['package_id'])}</title><style>body{{font:16px Arial;margin:40px}}.label{{max-width:760px;border:3px solid #111;padding:28px}}h1{{margin:0}}.grid{{display:grid;grid-template-columns:1fr 1fr;gap:24px}}.tracking{{font-family:monospace;font-size:24px;letter-spacing:3px;border:1px solid;padding:12px;text-align:center}}img{{width:130px;height:130px}}</style></head><body><div class='label'><h1>SHIPPING LABEL</h1><p>{escape(package['carrier'])} · {escape(package['tracking_number'])}</p><hr><div class='grid'><div><b>SHIP TO</b><h2>{escape(order['customer_name'])}</h2><p>{escape(order['customer_phone'])}<br>{address}</p></div><div><b>FROM</b><h2>{escape(warehouse['name'])}</h2><p>{escape(warehouse['warehouse_code'])}<br>{warehouse_address}</p></div></div><div class='grid'><p>Order: {escape(order['order_id'])}<br>Package: {escape(package['package_id'])}<br>Weight: {package['weight']} kg</p><img alt='Tracking QR code' src='{qr_uri}'></div><div class='tracking'>{escape(package['tracking_number'])}</div></div><script>window.print()</script></body></html>"""
