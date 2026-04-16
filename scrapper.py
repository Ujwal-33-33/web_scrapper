from fastapi import FastAPI, BackgroundTasks
import asyncio
from playwright.async_api import async_playwright
import json
import os
import requests
import sqlite3
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from dotenv import load_dotenv

load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
DB_FILE = "leads.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute('''
        CREATE TABLE IF NOT EXISTS yc_leads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_name TEXT NOT NULL,
            yc_url TEXT,
            industry TEXT
        )
    ''')
    conn.commit()
    conn.close()

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield

app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

async def scrape_yc():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        try:
            await page.goto("https://www.ycombinator.com/companies?isHiring=true", timeout=60000)
            await asyncio.sleep(3) 

            for _ in range(40):
                await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                await asyncio.sleep(2)

            data = await page.evaluate('''() => {
                const links = Array.from(document.querySelectorAll('a'));
                const results = [];
                const seenUrls = new Set();
                
                for (const link of links) {
                    const href = link.href;
                    if (href && href.includes('/companies/') && link.innerText.trim().length > 2) {
                        if (!seenUrls.has(href)) {
                            seenUrls.add(href);
                            results.push({
                                name: link.innerText.split('\\n')[0].trim() || "N/A",
                                yc_url: href,
                                description: "N/A" 
                            });
                        }
                    }
                }
                return results;
            }''')
        except Exception:
            data = []
        finally:
            await browser.close()

    with open('yc_raw.json', 'w') as f:
        json.dump(data, f, indent=4)

def categorize_company(description):
    if description == "N/A" or not GROQ_API_KEY:
        return "Uncategorized"
    
    prompt = f"Reply with a single 1 to 3 word industry category for this company. Description: {description}"
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "llama-3.1-8b-instant",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.3
    }
    
    try:
        response = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=10
        )
        return response.json()["choices"][0]["message"]["content"].strip()
    except Exception:
        return "Uncategorized"

def process_data():
    if not os.path.exists('yc_raw.json'):
        return

    with open('yc_raw.json', 'r') as f:
        raw_data = json.load(f)

    cleaned = []
    for item in raw_data:
        name = item.get("name", "").strip()
        url = item.get("yc_url", "").strip()
        
        if name and url and len(name) <= 50:
            cleaned.append((name, url, categorize_company(name)))

    if cleaned:
        conn = sqlite3.connect(DB_FILE)
        cur = conn.cursor()
        cur.execute("DELETE FROM yc_leads")
        cur.executemany("INSERT INTO yc_leads (company_name, yc_url, industry) VALUES (?, ?, ?)", cleaned)
        conn.commit()
        conn.close()

async def run_pipeline():
    await scrape_yc()
    await asyncio.to_thread(process_data)

@app.post("/api/pipeline/start")
async def start_pipeline(background_tasks: BackgroundTasks):
    background_tasks.add_task(run_pipeline)
    return {"status": "success", "message": "YC Pipeline started in background."}

@app.get("/api/leads")
def get_leads(skip: int = 0, limit: int = 20):
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    
    total = cur.execute("SELECT count(*) FROM yc_leads").fetchone()[0]
    rows = cur.execute("SELECT company_name, yc_url, industry FROM yc_leads LIMIT ? OFFSET ?", (limit, skip)).fetchall()
    
    leads = [dict(row) for row in rows]
    conn.close()
    return {"metadata": {"total": total, "skip": skip, "limit": limit}, "data": leads}

@app.get("/api/analyze")
def analyze_data():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    rows = conn.cursor().execute("SELECT company_name, industry FROM yc_leads LIMIT 100").fetchall()
    conn.close()
    
    leads = [dict(row) for row in rows]
    if not leads:
        return {"analysis": "No data found. Run the pipeline first."}

    if not GROQ_API_KEY:
        return {"analysis": "Error: GROQ_API_KEY environment variable is missing."}

    prompt = f"You are a data analyst. Review this list of recent Y Combinator startups and their industries. Provide a concise, three paragraph summary of the current market trends and dominating sectors. Data: {leads}"
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "llama-3.1-8b-instant",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.5
    }
    
    try:
        response = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=30
        )
        analysis = response.json()["choices"][0]["message"]["content"]
    except Exception as e:
        analysis = f"LLM Error: {e}"
        
    return {"analysis": analysis}