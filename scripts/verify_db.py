import os
import sys
from pathlib import Path
from dotenv import load_dotenv
import psycopg2

# Ensure .env is loaded from project root
ROOT_DIR = Path(__file__).resolve().parent.parent
load_dotenv(ROOT_DIR / ".env")

db_url = os.getenv("DATABASE_URL")

if not db_url or "postgresql://" not in db_url:
    print("[ERROR] DATABASE_URL missing or invalid in .env file.")
    print("Format should be: DATABASE_URL=postgresql://user:password@host/dbname?sslmode=require")
    sys.exit(1)

print("[1/3] Connecting to PostgreSQL (Neon)...")
try:
    conn = psycopg2.connect(db_url)
    cur = conn.cursor()
    print("      SUCCESS: Connected to database!")

    print("[2/3] Enabling 'vector' extension...")
    cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
    conn.commit()
    print("      SUCCESS: 'vector' extension is enabled!")

    print("[3/3] Checking vector version...")
    cur.execute("SELECT extversion FROM pg_extension WHERE extname = 'vector';")
    version = cur.fetchone()
    if version:
        print(f"      SUCCESS: pgvector version installed: {version[0]}")
    else:
        print("      [WARNING] Extension installed, but could not read version.")

    cur.close()
    conn.close()
    print("\n All good! Database + pgvector is 100% ready for PulseOps AI!")
except Exception as e:
    print(f"\n[ERROR] Connection failed: {e}")
    sys.exit(1)
