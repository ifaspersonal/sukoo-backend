from app.db.session import SessionLocal
from app.models.user import User
from app.utils.password import hash_password

def init():
    db = SessionLocal()

    if not db.query(User).filter(User.username == "owner").first():
        owner = User(
            username="owner",
            password=hash_password("owner123"),
            role="owner",
        )
        db.add(owner)

    if not db.query(User).filter(User.username == "kasir").first():
        kasir = User(
            username="kasir",
            password=hash_password("kasir123"),
            role="kasir",
        )
        db.add(kasir)

    db.commit()
    db.close()

if __name__ == "__main__":
    init()