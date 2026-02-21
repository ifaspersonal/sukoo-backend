from datetime import datetime
from zoneinfo import ZoneInfo

LINE_WIDTH = 32  # 58mm thermal


def _rupiah(n: int) -> str:
    return f"{n:,}".replace(",", ".")


def _product_name(item) -> str:
    if hasattr(item, "product") and item.product:
        return item.product.name
    return "-"


def _calc_total(items) -> int:
    return sum(item.subtotal for item in items)


def _format_datetime(dt: datetime | None) -> str:
    if not dt:
        return "-"

    # Jika datetime tidak punya timezone → anggap UTC
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=ZoneInfo("UTC"))

    # Convert ke WIB
    dt_wib = dt.astimezone(ZoneInfo("Asia/Jakarta"))

    return dt_wib.strftime("%d-%m-%Y %H:%M")


def _separator(char: str = "-") -> str:
    return char * LINE_WIDTH


def _line_item(name: str, qty: int, subtotal: int) -> str:
    """
    Format 1 baris item supaya rapi 58mm
    """
    name = name[:16].ljust(16)
    qty_str = f"x{qty}".ljust(4)
    price_str = _rupiah(subtotal).rjust(8)
    return f"{name} {qty_str} {price_str}"


def build_receipt_preview(tx, items):
    """
    STRUK UNTUK RAWBT INTENT MODE (PLAIN TEXT)
    - 58mm friendly
    - Tanpa ESC/POS command
    - Loyalty info included
    - Timezone WIB
    """

    lines: list[str] = []

    # ==============================
    # HEADER (CENTER)
    # ==============================
    lines.append("SUKOO COFFEE".center(LINE_WIDTH))
    lines.append("Fresh Brew Everyday".center(LINE_WIDTH))
    lines.append(_separator())

    # ==============================
    # META INFO
    # ==============================
    created_at = getattr(tx, "created_at", None)

    cashier = (
        getattr(tx, "user", None).username
        if hasattr(tx, "user") and tx.user
        else "Kasir"
    )

    trx_no = f"#{str(tx.id).zfill(6)}"
    payment_method = getattr(tx, "payment_method", "-").upper()

    lines.append(f"Tanggal  : {_format_datetime(created_at)}")
    lines.append(f"Kasir    : {cashier}")
    lines.append(f"Transaksi: {trx_no}")
    lines.append(f"Metode   : {payment_method}")
    lines.append(_separator())

    # ==============================
    # ITEMS
    # ==============================
    for item in items:
        name = _product_name(item)
        lines.append(_line_item(name, item.qty, item.subtotal))

    lines.append(_separator())

    # ==============================
    # TOTAL
    # ==============================
    grand_total = _calc_total(items)
    total_str = _rupiah(grand_total).rjust(8)

    lines.append(f"{'TOTAL'.ljust(24)}{total_str}")
    lines.append(_separator())

    # ==============================
    # LOYALTY INFO
    # ==============================
    if hasattr(tx, "customer") and tx.customer:
        earned = 0
        redeemed = 0

        if hasattr(tx, "point_histories") and tx.point_histories:
            for ph in tx.point_histories:
                if ph.type == "earn":
                    earned += ph.points
                elif ph.type == "redeem":
                    redeemed += abs(ph.points)

        if earned > 0:
            lines.append(f"Poin Didapat : +{earned}")

        if redeemed > 0:
            lines.append(f"Poin Redeem  : -{redeemed}")

        # Safe fallback kalau points None
        remaining_points = tx.customer.points or 0
        lines.append(f"Sisa Poin    : {remaining_points}")

        lines.append(_separator())

    # ==============================
    # FOOTER
    # ==============================
    lines.append("Terima kasih 🙏".center(LINE_WIDTH))
    lines.append("Follow IG @sukoocoffee".center(LINE_WIDTH))

    # ==============================
    # AUTO FEED
    # ==============================
    lines.append("")
    lines.append("")
    lines.append("")

    return "\n".join(lines)