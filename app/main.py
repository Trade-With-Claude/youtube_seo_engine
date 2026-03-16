from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.database import init_db
from app.routers import auth, competitors, dashboard, metadata, reports, seo, trends, vph

app = FastAPI(title="YouTube SEO Engine")

app.mount("/static", StaticFiles(directory="app/static"), name="static")
app.include_router(dashboard.router)
app.include_router(auth.router)
app.include_router(trends.router)
app.include_router(competitors.router)
app.include_router(metadata.router)
app.include_router(reports.router)
app.include_router(vph.router)
app.include_router(seo.router)


@app.on_event("startup")
def on_startup():
    init_db()
