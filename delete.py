import psycopg2
import os

# Get this from Supabase Dashboard
DATABASE_URL = os.getenv("DATABASE_URL")

def save_leads(leads):
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    # Your SQL logic here
    cur.execute("INSERT INTO yc_leads ...")
    conn.commit()
    cur.close()
    conn.close()