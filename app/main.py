from fastapi import FastAPI
from app.routers import auth, users, products, transactions, stocks, print
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="SUKOO POS API")

origins = [
    "http://localhost:3000",
    "https://sukoo-pos-frontend.vercel.app",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(products.router)
app.include_router(transactions.router)
app.include_router(stocks.router)
app.include_router(print.router)

@app.get("/")
def root():
    return {"status": "SUKOO POS API RUNNING"}