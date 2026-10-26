"""SQLite-backed, deterministic rules for OFX transaction categories."""

from __future__ import annotations

import re
import sqlite3
import unicodedata
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator


DATABASE_PATH = Path(__file__).with_name("categorization.sqlite3")

CATEGORIES = {
    "Alimentação",
    "Casa e moradia",
    "Compras",
    "Educação",
    "Escritório",
    "Lazer",
    "Pessoal",
    "Receitas",
    "Saúde",
    "Serviços",
    "Transporte",
    "Transferência",
    "Outros",
}

# Common OFX descriptions. User-created rules take precedence over these.
DEFAULT_RULES = [
    ("RECEBIMENTO", "Receitas", 120),
    ("PAGAMENTO CLIENTE", "Receitas", 115),
    ("RECEITA", "Receitas", 110),
    ("VENDA", "Receitas", 105),
    ("CONTRATO CONSULTORIA", "Receitas", 100),
    ("PIX CLIENTE", "Receitas", 115),
    ("ALUGUEL", "Casa e moradia", 100),
    ("ENERGIA ELETRICA", "Casa e moradia", 100),
    ("CONTA DE LUZ", "Casa e moradia", 100),
    ("CONDOMINIO", "Casa e moradia", 100),
    ("AGUA", "Casa e moradia", 90),
    ("INTERNET", "Serviços", 100),
    ("TELEFONE", "Serviços", 95),
    ("ASSINATURA", "Serviços", 95),
    ("CLOUD STORAGE", "Serviços", 105),
    ("SOFTWARE", "Serviços", 90),
    ("HOSPEDAGEM", "Serviços", 90),
    ("MATERIAL ESCRITORIO", "Escritório", 110),
    ("MATERIAL LIMPEZA", "Escritório", 100),
    ("EQUIPAMENTOS TI", "Escritório", 110),
    ("COMPRA EQUIPAMENTOS", "Escritório", 100),
    ("FOLHA PAGAMENTO", "Pessoal", 110),
    ("SALARIO", "Pessoal", 100),
    ("PRO LABORE", "Pessoal", 100),
    ("INSS", "Pessoal", 90),
    ("FGTS", "Pessoal", 90),
    ("ESTACIONAMENTO", "Transporte", 100),
    ("COMBUSTIVEL", "Transporte", 100),
    ("MANUTENCAO VEICULO", "Transporte", 110),
    ("PEDAGIO", "Transporte", 100),
    ("UBER", "Transporte", 95),
    ("TAXI", "Transporte", 95),
    ("SUPERMERCADO", "Alimentação", 100),
    ("RESTAURANTE", "Alimentação", 100),
    ("FARMACIA", "Saúde", 100),
    ("CONSULTA MEDICA", "Saúde", 100),
    ("PIX", "Transferência", 60),
    ("TRANSFERENCIA", "Transferência", 90),
    ("TED", "Transferência", 90),
    ("DOC", "Transferência", 90),
]

_CREATE_RULES_TABLE = """
CREATE TABLE IF NOT EXISTS categorization_rules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pattern TEXT NOT NULL,
    category TEXT,
    source TEXT NOT NULL CHECK (source IN ('default', 'user')),
    priority INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    UNIQUE (source, pattern)
)
"""


def normalize_text(value: str | None) -> str:
    """Make matching case-, accent-, and punctuation-insensitive."""
    if not value:
        return ""
    decomposed = unicodedata.normalize("NFKD", value)
    without_accents = "".join(char for char in decomposed if not unicodedata.combining(char))
    return re.sub(r"[^A-Z0-9]+", " ", without_accents.upper()).strip()


def _connect() -> sqlite3.Connection:
    connection = sqlite3.connect(DATABASE_PATH, timeout=10)
    connection.row_factory = sqlite3.Row
    return connection


@contextmanager
def _connection() -> Iterator[sqlite3.Connection]:
    connection = _connect()
    try:
        with connection:
            yield connection
    finally:
        connection.close()


def _migrate_payment_type_column(connection: sqlite3.Connection) -> None:
    table = connection.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table' AND name = 'categorization_rules'"
    ).fetchone()
    if table is None:
        connection.execute(_CREATE_RULES_TABLE)
        return

    columns = {row["name"] for row in connection.execute("PRAGMA table_info(categorization_rules)")}
    if "payment_type" not in columns:
        return

    # Rebuild the table rather than retaining the unused column. Keep all
    # category rules and discard the former payment-only rules.
    connection.execute("DROP INDEX IF EXISTS idx_categorization_rules_source_priority")
    connection.execute("ALTER TABLE categorization_rules RENAME TO categorization_rules_with_payment_type")
    connection.execute(_CREATE_RULES_TABLE)
    connection.execute(
        """
        INSERT INTO categorization_rules (id, pattern, category, source, priority, created_at)
        SELECT id, pattern, category, source, priority, created_at
        FROM categorization_rules_with_payment_type
        WHERE category IS NOT NULL AND trim(category) <> ''
        """
    )
    connection.execute("DROP TABLE categorization_rules_with_payment_type")


def initialize_database() -> None:
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with _connection() as connection:
        _migrate_payment_type_column(connection)
        connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_categorization_rules_source_priority "
            "ON categorization_rules(source, priority DESC)"
        )
        connection.executemany(
            """
            INSERT OR IGNORE INTO categorization_rules
                (pattern, category, source, priority, created_at)
            VALUES (?, ?, 'default', ?, 'system')
            """,
            [(normalize_text(pattern), category, priority) for pattern, category, priority in DEFAULT_RULES],
        )


def get_rules() -> list[dict[str, Any]]:
    with _connection() as connection:
        rows = connection.execute(
            """
            SELECT pattern, category, source, priority
            FROM categorization_rules
            ORDER BY CASE source WHEN 'user' THEN 0 ELSE 1 END,
                     priority DESC,
                     length(pattern) DESC
            """
        ).fetchall()
    return [dict(row) for row in rows]


def classify_transaction(transaction: dict[str, Any], rules: list[dict[str, Any]]) -> dict[str, Any]:
    description = normalize_text(" ".join(filter(None, [transaction.get("memo"), transaction.get("payee")])))
    padded_description = f" {description} "
    category = None
    category_source = None

    for rule in rules:
        pattern = rule["pattern"]
        if pattern and f" {pattern} " in padded_description and rule["category"]:
            category = rule["category"]
            category_source = rule["source"]
            break

    return {**transaction, "category": category, "category_source": category_source}


def save_user_rule(memo: str | None, payee: str | None, category: str | None) -> dict[str, Any]:
    # Prefer the payee/merchant when present so the rule can cover its future
    # transactions; use the memo when the OFX does not provide a payee.
    pattern = normalize_text(payee) or normalize_text(memo)
    if not pattern:
        raise ValueError("Não foi possível criar uma regra sem descrição ou favorecido.")
    if category is None:
        raise ValueError("Selecione uma categoria antes de salvar a regra.")

    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    with _connection() as connection:
        connection.execute(
            """
            INSERT INTO categorization_rules (pattern, category, source, priority, created_at)
            VALUES (?, ?, 'user', 1000, ?)
            ON CONFLICT(source, pattern) DO UPDATE SET
                category = excluded.category,
                priority = excluded.priority,
                created_at = excluded.created_at
            """,
            (pattern, category, now),
        )
        row = connection.execute(
            """
            SELECT id, pattern, category, source
            FROM categorization_rules WHERE source = 'user' AND pattern = ?
            """,
            (pattern,),
        ).fetchone()

    return dict(row)
