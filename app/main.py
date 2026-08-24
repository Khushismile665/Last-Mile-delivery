from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
import os

from app.database import engine, Base
from app.seed import seed_database
from app.routers import auth, zones, rates, agents, orders

# Initialize Database tables and Seed initial data
Base.metadata.create_all(bind=engine)
try:
    seed_database()
except Exception as e:
    print(f"[Main Startup] Warning during database seed: {e}")

app = FastAPI(
    title="Last-Mile Delivery Tracker Platform",
    description="Logistics Management Platform with Dynamic Rate Engine, Zone Detection, Intelligent Agent Auto-Assignment, Immutable Tracking Timeline, and Reschedule Workflows.",
    version="1.0.0"
)

# CORS Middleware setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount Routers
app.include_router(auth.router)
app.include_router(zones.router)
app.include_router(rates.router)
app.include_router(agents.router)
app.include_router(orders.router)

# Setup Templates & Static Assets
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATIC_DIR = os.path.join(BASE_DIR, "static")
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")

if not os.path.exists(STATIC_DIR):
    os.makedirs(STATIC_DIR)
if not os.path.exists(TEMPLATES_DIR):
    os.makedirs(TEMPLATES_DIR)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
templates = Jinja2Templates(directory=TEMPLATES_DIR)

@app.get("/", response_class=HTMLResponse)
def render_home(request: Request):
    index_path = os.path.join(TEMPLATES_DIR, "index.html")
    if os.path.exists(index_path):
        with open(index_path, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    return templates.TemplateResponse(request=request, name="index.html")

@app.get("/health")
def health_check():
    return {"status": "operational", "version": "1.0.0"}
