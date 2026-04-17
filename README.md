# 🚀 YC Leads Intelligence

A full-stack automated data pipeline and dashboard that scrapes Y Combinator's live hiring page, uses an LLM to categorize startup industries in real-time, and presents the results through a clean, modern React dashboard.

---

## 🛠️ Tech Stack

- **Backend:** FastAPI, Python, Playwright (Headless Browser Scraping)
- **AI / LLM:** Groq API (Llama 3.1 8B) — zero-shot industry categorization
- **Database:** MongoDB Atlas
- **Frontend:** React, Vite, Tailwind CSS, Lucide Icons
- **Deployment:** Render (Backend via Docker), Vercel (Frontend)

---

## 🔐 Environment Variables

**Backend** — create a `.env` file in the project root:

```env
GROQ_API_KEY=your_groq_api_key
MONGO_URI=your_mongodb_atlas_connection_string
```

**Frontend** — create a `.env` file inside the `frontend/` directory:

```env
VITE_API_URL=https://your-backend-url.onrender.com
```

---

## 💻 Local Development Setup

### Backend

**Option 1 — Docker (Recommended)**

```bash
# Build the image
docker build -t yc-scraper .

# Run the container
docker run -p 8000:8000 --env-file .env yc-scraper
```

> ✅ This is the recommended approach as it bundles all Playwright browser dependencies automatically.

**Option 2 — Native Python**

```bash
pip install -r requirements.txt
playwright install chromium
uvicorn scrapper:app --reload
```

---

### Frontend

```bash
cd frontend
npm install
npm run dev
```

The frontend will be available at `http://localhost:5173`.

---

## 📡 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/pipeline/start` | Triggers the scraper and AI categorization pipeline in the background |
| `GET` | `/api/leads?skip=0&limit=20` | Fetches paginated leads from MongoDB |
| `GET` | `/api/analyze` | Uses Groq to generate a market trend analysis from the top 100 leads |

---

## ☁️ Deployment Guide

### Render (Backend)

> ⚠️ **Critical:** Do **not** deploy as a standard Python environment. Render's default Python runtime is missing the system-level dependencies required by Playwright (e.g., shared libraries, browser binaries). Your service **will crash** on startup.

**You must deploy as a Docker service:**

1. Push your code (including the `Dockerfile`) to GitHub.
2. On Render, create a new **Docker** service (not a Python/Web Service).
3. Point it to your repository.
4. Add your environment variables (`GROQ_API_KEY`, `MONGO_URI`) in the Render dashboard under **Environment**.
5. Deploy — Render will build and run the Docker image automatically.

---

### Vercel (Frontend)

1. Import your repository into Vercel.
2. Set the **Root Directory** to `frontend`.
3. Add the environment variable `VITE_API_URL` pointing to your live Render backend URL.
4. Deploy — Vercel will auto-detect the Vite framework and build correctly.

---

## 📝 Important Notes

- **Lazy-load bypass:** The scraper performs **40 consecutive page-down scrolls** with a 2-second delay between each to ensure YC's infinite-scroll company list is fully loaded before data extraction.
- **Fresh data guarantee:** Before inserting new leads, the pipeline **wipes all existing records** from the MongoDB collection. This ensures the database always reflects the current YC hiring list with no stale entries.
