from datetime import datetime

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
    return dt.strftime("%d-%m-%Y %H:%M")


def build_receipt_preview(tx, items):
    """
    STRUK UNTUK FRONTEND PREVIEW (POLISHED)
    - TANPA ESC/POS
    - 58mm friendly
    """

    lines: list[str] = []

    # ===== HEADER =====
    lines.append("SUKOO COFFEE".center(LINE_WIDTH))
    lines.append("Fresh Brew Everyday".center(LINE_WIDTH))
    lines.append("-" * LINE_WIDTH)

    # ===== META INFO =====
    created_at = getattr(tx, "created_at", None)
    cashier = (
        getattr(tx, "user", None).username
        if hasattr(tx, "user") and tx.user
        else "Kasir"
    )
    trx_no = f"#{str(tx.id).zfill(6)}"

    lines.append(f"Tanggal : {_format_datetime(created_at)}")
    lines.append(f"Kasir   : {cashier}")
    lines.append(f"Transaksi: {trx_no}")
    lines.append("-" * LINE_WIDTH)

    # ===== ITEMS =====
    for item in items:
        name = _product_name(item)[:16].ljust(16)
        qty = f"x{item.qty}".ljust(4)
        price = _rupiah(item.subtotal).rjust(8)
        lines.append(f"{name} {qty} {price}")

    lines.append("-" * LINE_WIDTH)

    # ===== TOTAL =====
    grand_total = _calc_total(items)
    total = _rupiah(grand_total).rjust(8)
    lines.append(f"{'TOTAL'.ljust(24)}{total}")

    payment = getattr(tx, "payment_method", "-").upper()
    lines.append(f"Bayar: {payment}")
    lines.append("")

    # ===== FOOTER =====
    lines.append("Terima kasih 🙏".center(LINE_WIDTH))
    lines.append("-" * LINE_WIDTH)

    return "\n".join(lines)