from fastmcp import FastMCP
import os
import json
import aiosqlite
import asyncio


# File paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DB_PATH = os.path.join(BASE_DIR, "expense.db")
CATEGORIES_PATH = os.path.join(BASE_DIR, "expense_categories.json")


# Create MCP server
mcp = FastMCP("ExpenseTracker")


# Initialize database
async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS expenses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                amount REAL NOT NULL,
                category TEXT NOT NULL,
                subcategory TEXT NOT NULL DEFAULT '',
                note TEXT DEFAULT ''
            )
        """)

        await db.commit()


# Tool 1: Add expense
@mcp.tool()
async def add_expense(
    date: str,
    amount: float,
    category: str,
    subcategory: str = "",
    note: str = ""
):
    """
    Add a new expense to the database.

    Use date format YYYY-MM-DD.
    Example: date='2026-10-26',
    amount=250, category='Transportation',
    subcategory='Taxi & Ride-hailing',
    note='Uber ride'.
    """

    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            """
            INSERT INTO expenses
            (date, amount, category, subcategory, note)
            VALUES (?, ?, ?, ?, ?)
            """,
            (date, amount, category, subcategory, note)
        )

        await db.commit()

        expense_id = cursor.lastrowid

        await cursor.close()

        return {
            "status": "success",
            "id": expense_id,
            "date": date,
            "amount": amount,
            "category": category,
            "subcategory": subcategory,
            "note": note
        }


# Tool 2: List expenses
@mcp.tool()
async def list_expenses(start_date: str, end_date: str):
    """
    List all expenses between two dates, inclusive.

    Dates must use YYYY-MM-DD format.
    """

    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row

        async with db.execute(
            """
            SELECT id, date, amount, category, subcategory, note
            FROM expenses
            WHERE date BETWEEN ? AND ?
            ORDER BY date ASC, id ASC
            """,
            (start_date, end_date)
        ) as cursor:

            rows = await cursor.fetchall()

            return [dict(row) for row in rows]


# Tool 3: Summarize expenses
@mcp.tool()
async def summarize_expenses(
    start_date: str,
    end_date: str,
    category: str | None = None
):
    """
    Summarize expenses by category for a date range.

    Optionally provide a category to summarize only
    that category.
    """

    query = """
        SELECT category, SUM(amount) AS total_amount
        FROM expenses
        WHERE date BETWEEN ? AND ?
    """

    params = [start_date, end_date]

    if category:
        query += " AND category = ?"
        params.append(category)

    query += " GROUP BY category ORDER BY category ASC"

    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row

        async with db.execute(query, params) as cursor:
            rows = await cursor.fetchall()

            return [dict(row) for row in rows]


# Resource: Expense categories
@mcp.resource(
    "expense://categories",
    mime_type="application/json"
)
async def categories():
    """
    Return the available expense categories
    and their subcategories from the JSON file.
    """

    with open(CATEGORIES_PATH, "r", encoding="utf-8") as file:
        return json.dumps(json.load(file), ensure_ascii=False, indent=2)


# Start server
if __name__ == "__main__":
    asyncio.run(init_db())

    mcp.run(
        transport="http",
        host="0.0.0.0",
        port=8000
    )