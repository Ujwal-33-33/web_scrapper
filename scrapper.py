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
MONGO_URI = os.getenv("MONGO_URI")

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

async def scrape_yc():
    print("[SCRAPER] Starting Playwright...")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        try:
            print("[SCRAPER] Navigating to YC page...")
            await page.goto("https://www.ycombinator.com/companies?isHiring=true", timeout=60000)
            await asyncio.sleep(3) 

            for i in range(40):
                print(f"[SCRAPER] Scrolling down... {i+1}/40")
                await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                await asyncio.sleep(2)

            print("[SCRAPER] Extracting data...")
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
            print(f"[SCRAPER] Successfully extracted {len(data)} raw leads.")
        except Exception as e:
            print(f"[SCRAPER ERROR] Playwright crashed: {e}")
            data = []
        finally:
            await browser.close()
            print("[SCRAPER] Browser closed.")

    print("[SCRAPER] Saving to yc_raw.json")
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
        category = response.json()["choices"][0]["message"]["content"].strip()
        print(f"[GROQ] Categorized: {category}")
        return category
    except Exception as e:
        print(f"[GROQ ERROR] Failed on '{description}': {e}")
        return "Uncategorized"

def process_data():
    print("[PROCESS] Starting data cleaning and categorization...")
    if not os.path.exists('yc_raw.json'):
        print("[PROCESS ERROR] yc_raw.json not found!")
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
        try:
            print(f"[DB] Connecting to MongoDB to insert {len(cleaned)} records...")
            client = MongoClient(MONGO_URI)
            db = client["b2b_database"]
            collection = db["yc_leads"]
            
            print("[DB] Deleting old records...")
            collection.delete_many({}) 
            
            print("[DB] Inserting new records...")
            collection.insert_many(cleaned)
            print("[DB] Insertion complete.")
        except Exception as e:
            print(f"[DB ERROR] MongoDB connection or insertion failed: {e}")
    else:
        print("[PROCESS] No valid data found to insert.")

async def run_pipeline():
    print("\n=== PIPELINE TRIGGERED ===")
    await scrape_yc()
    await asyncio.to_thread(process_data)
    print("=== PIPELINE FINISHED ===\n")

@app.post("/api/pipeline/start")
async def start_pipeline(background_tasks: BackgroundTasks):
    print("[API] Pipeline start requested by frontend.")
    background_tasks.add_task(run_pipeline)
    return {"status": "success", "message": "YC Pipeline started in background."}

@app.get("/api/leads")
def get_leads(skip: int = 0, limit: int = 20):
    try:
        client = MongoClient(MONGO_URI)
        db = client["b2b_database"]
        collection = db["yc_leads"]
        
        leads = list(collection.find({}, {"_id": 0}).skip(skip).limit(limit))
        total = collection.count_documents({})
        return {"metadata": {"total": total, "skip": skip, "limit": limit}, "data": leads}
    except Exception as e:
        print(f"[API ERROR] Failed to fetch leads: {e}")
        return {"metadata": {"total": 0, "skip": skip, "limit": limit}, "data": []}

@app.get("/api/analyze")
def analyze_data():
    print("[API] Analysis requested.")
    try:
        client = MongoClient(MONGO_URI)
        db = client["b2b_database"]
        collection = db["yc_leads"]
        
        leads = list(collection.find({}, {"_id": 0, "company_name": 1, "industry": 1}).limit(100))
    except Exception as e:
        print(f"[API ERROR] MongoDB fetch failed for analysis: {e}")
        return {"analysis": "Database error."}

    if not leads:
        return {"analysis": "No data found. Run the pipeline first."}

    if not GROQ_API_KEY:
        print("[API ERROR] GROQ_API_KEY is missing.")
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
        print("[GROQ] Generating market analysis...")
        response = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=30
        )
        analysis = response.json()["choices"][0]["message"]["content"]
        print("[GROQ] Analysis generated successfully.")
    except Exception as e:
        print(f"[GROQ ERROR] Analysis failed: {e}")
        analysis = f"LLM Error: {e}"
        
    return {"analysis": analysis}