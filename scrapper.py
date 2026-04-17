from fastapi import FastAPI, BackgroundTasks
import asyncio
from playwright.async_api import async_playwright
import json
import os
import requests
from pymongo import MongoClient
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")

app = FastAPI()

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

            for _ in range(15):
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
            cleaned.append({
                "company_name": name,
                "yc_url": url,
                "industry": categorize_company(name)
            })

    if cleaned:
        client = MongoClient(MONGO_URI)
        db = client["b2b_database"]
        collection = db["yc_leads"]
        collection.delete_many({}) 
        collection.insert_many(cleaned)

async def run_pipeline():
    await scrape_yc()
    await asyncio.to_thread(process_data)

@app.post("/api/pipeline/start")
async def start_pipeline(background_tasks: BackgroundTasks):
    background_tasks.add_task(run_pipeline)
    return {"status": "success", "message": "YC Pipeline started in background."}

@app.get("/api/leads")
def get_leads(skip: int = 0, limit: int = 20):
    client = MongoClient(MONGO_URI)
    db = client["b2b_database"]
    collection = db["yc_leads"]
    
    leads = list(collection.find({}, {"_id": 0}).skip(skip).limit(limit))
    total = collection.count_documents({})
    
    return {"metadata": {"total": total, "skip": skip, "limit": limit}, "data": leads}

@app.get("/api/analyze")
def analyze_data():
    client = MongoClient(MONGO_URI)
    db = client["b2b_database"]
    collection = db["yc_leads"]
    
    leads = list(collection.find({}, {"_id": 0, "company_name": 1, "industry": 1}).limit(100))
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