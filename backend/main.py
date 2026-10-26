from contextlib import asynccontextmanager
from io import BytesIO

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from ofxparse import OfxParser

try:
    from .categorization import (
        CATEGORIES,
        classify_transaction,
        get_rules,
        initialize_database,
        save_user_rule,
    )
except ImportError:  # Supports `uvicorn main:app --app-dir backend` as well.
    from categorization import (
        CATEGORIES,
        classify_transaction,
        get_rules,
        initialize_database,
        save_user_rule,
    )


@asynccontextmanager
async def lifespan(_: FastAPI):
    initialize_database()
    yield


app = FastAPI(title="OFX Category - API (By FastAPI)", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class CategorizationRuleRequest(BaseModel):
    memo: str | None = None
    payee: str | None = None
    category: str | None = None


@app.get("/api/health")
def health():
    return {"status": "ok", "message": "API está rodando com sucesso!"}


@app.post("/api/upload/")
async def upload_file(file: UploadFile = File(...)):
    try:
        contents = await file.read()
        ofx = OfxParser.parse(BytesIO(contents))
        account = ofx.account
        statement = account.statement

        raw_transactions = [
            {
                "date": str(transaction.date),
                "amount": float(transaction.amount),
                "memo": transaction.memo,
                "payee": transaction.payee,
                "id": transaction.id,
            }
            for transaction in statement.transactions
        ]
        rules = get_rules()
        transactions = [classify_transaction(transaction, rules) for transaction in raw_transactions]

        return {
            "account_id": account.account_id,
            "balance": float(statement.balance) if statement.balance is not None else None,
            "start_date": str(statement.start_date),
            "end_date": str(statement.end_date),
            "transactions": transactions,
        }

    except Exception as exc:
        raise HTTPException(
            status_code=400,
            detail=f"Falha ao processar arquivo OFX: {str(exc)}",
        ) from exc


@app.post("/api/rules/")
def create_categorization_rule(rule: CategorizationRuleRequest):
    category = (rule.category or "").strip() or None
    if category is not None and category not in CATEGORIES:
        raise HTTPException(status_code=422, detail="A categoria informada não é válida.")

    try:
        saved_rule = save_user_rule(rule.memo, rule.payee, category)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    return {"message": "Regra salva para os próximos extratos.", "rule": saved_rule}
