ESC = b'\x1b'
GS = b'\x1d'

def init_printer():
    return ESC + b'@'

def align_center():
    return ESC + b'a\x01'

def align_left():
    return ESC + b'a\x00'

def bold_on():
    return ESC + b'E\x01'

def bold_off():
    return ESC + b'E\x00'

def cut():
    return GS + b'V\x01'

def text(t: str):
    return t.encode("ascii", errors="ignore")