from fastapi import FastAPI, Request, Response
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, PlainTextResponse
import uvicorn
import argparse
import os
from prometheus_client import Counter, Gauge, generate_latest, CONTENT_TYPE_LATEST
from starlette.middleware.base import BaseHTTPMiddleware
from collections import deque

# Metrics
REQUEST_COUNT = Counter("request_count", "Total request count", ["app_name", "endpoint"])
ACTIVE_REQUESTS = Gauge("active_requests", "Number of active requests", ["app_name"])

app = FastAPI()
name = None

templates = Jinja2Templates(directory=os.path.join(os.path.dirname(__file__), "templates"))

# Middleware to track active requests
class MetricsMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        ACTIVE_REQUESTS.labels(app_name="fastapi").inc()
        try:
            response = await call_next(request)
            return response
        finally:
            ACTIVE_REQUESTS.labels(app_name="fastapi").dec()

app.add_middleware(MetricsMiddleware)

@app.get("/", response_class=HTMLResponse)
async def get_homepage(request: Request):
    REQUEST_COUNT.labels(app_name="fastapi", endpoint="/").inc()
    return templates.TemplateResponse("index.html", {"request": request, "name": name})

@app.get("/metrics", response_class=PlainTextResponse)
async def metrics():
    metrics_data = generate_latest()
    return Response(content=metrics_data, media_type=CONTENT_TYPE_LATEST)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the FastAPI application")
    parser.add_argument("--name", type=str, help="Name to display on the homepage")
    parser.add_argument("--port", type=str, help="Port to spawn the server at")
    args = parser.parse_args()
    name = args.name
    uvicorn.run(app, host="0.0.0.0", port=int(args.port))
