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


def _separator(char: str = "-") -> str:
    return char * LINE_WIDTH


def build_receipt_preview(tx, items):
    """
    STRUK PROFESSIONAL
    - 58mm friendly
    - Compatible RawBT (ESC/POS safe)
    - Loyalty info included
    """

    lines: list[str] = []

    # ==============================
    # ESC INIT (safe for RawBT)
    # ==============================
    lines.append("\x1B\x40")  # Initialize printer

    # ==============================
    # HEADER (CENTER)
    # ==============================
    lines.append("\x1B\x61\x01")  # center align
    lines.append("SUKOO COFFEE")
    lines.append("Fresh Brew Everyday")
    lines.append("\x1B\x61\x00")  # left align
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

    lines.append(f"Tanggal : {_format_datetime(created_at)}")
    lines.append(f"Kasir   : {cashier}")
    lines.append(f"Transaksi: {trx_no}")
    lines.append(f"Metode  : {getattr(tx, 'payment_method', '-').upper()}")
    lines.append(_separator())

    # ==============================
    # ITEMS
    # ==============================
    for item in items:
        name = _product_name(item)[:16].ljust(16)
        qty = f"x{item.qty}".ljust(4)
        price = _rupiah(item.subtotal).rjust(8)
        lines.append(f"{name} {qty} {price}")

    lines.append(_separator())

    # ==============================
    # TOTAL (BOLD)
    # ==============================
    grand_total = _calc_total(items)

    lines.append("\x1B\x45\x01")  # bold on
    lines.append(
        f"{'TOTAL'.ljust(24)}{_rupiah(grand_total).rjust(8)}"
    )
    lines.append("\x1B\x45\x00")  # bold off

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

        lines.append(f"Sisa Poin    : {tx.customer.points}")
        lines.append(_separator())

    # ==============================
    # FOOTER
    # ==============================
    lines.append("\x1B\x61\x01")  # center
    lines.append("Terima kasih 🙏")
    lines.append("Follow IG @sukoocoffee")
    lines.append("\x1B\x61\x00")

    # ==============================
    # AUTO FEED
    # ==============================
    lines.append("\n\n\n")

    return "\n".join(lines)