import socket
import logging

logger = logging.getLogger(__name__)

def send_to_printer(data, printer_ip, printer_port=9100):
    try:
        s = socket.socket()
        s.settimeout(3)  # ⏱️ jangan block lama
        s.connect((printer_ip, printer_port))
        s.sendall(data)
        s.close()
    except Exception as e:
        logger.error(f"PRINT FAILED: {e}")
        # ❗ JANGAN raise exception
        return False

    return True