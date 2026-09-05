"""
db.py — PostgreSQL connection handling.

A pool, not a single global connection: an agent can chain several tool
calls in one turn (search, then read, then update), so tools need to be
able to grab a connection concurrently without stepping on each other.

Install:
    pip install "psycopg[binary,pool]" python-dotenv
"""

import os
from psycopg_pool import ConnectionPool
from dotenv import load_dotenv

load_dotenv()  # reads a .env file if you have one

# Put real credentials in a .env file (DATABASE_URL=...), never hardcode them.
DB_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://user:password@localhost:5432/company_documents",
)

pool = ConnectionPool(conninfo=DB_URL, min_size=1, max_size=5, open=True)


def get_connection():
    """Usage: `with get_connection() as conn:` — borrows a connection from
    the pool and returns it automatically when the block exits."""
    return pool.connection()