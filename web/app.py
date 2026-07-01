"""FastAPI web interface for Telegram Forwarder Bot."""

import os
import secrets
import sys
from contextlib import asynccontextmanager
from datetime import datetime

# Add the parent directory to Python path so we can import from source
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from typing import Dict, List, Optional

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from starlette.requests import Request

from source.core.Telegram import Telegram
from source.model.Credentials import Credentials
from source.model.ForwardConfig import ForwardConfig

# Docker Compose substitutes .env into the container's real environment, but
# a plain `python web/app.py` run never reads .env on its own. Load it here
# so the .env file created via `cp .env.example .env` actually takes effect;
# real environment variables (e.g. set by docker-compose) still win.
load_dotenv()

# The dashboard controls a real Telegram account (listing chats, forwarding
# messages), so every API route requires a shared-secret API key. Refuse to
# serve requests if the operator hasn't set one, rather than defaulting to
# an open API.
API_KEY = os.getenv("API_KEY")


async def verify_api_key(x_api_key: Optional[str] = Header(default=None)) -> None:
    if not API_KEY:
        raise HTTPException(
            status_code=503,
            detail="Server is missing the API_KEY environment variable; refusing to serve API requests.",
        )
    if not x_api_key or not secrets.compare_digest(x_api_key, API_KEY):
        raise HTTPException(status_code=401, detail="Invalid or missing API key")


# Pydantic models for API
class ForwardConfigCreate(BaseModel):
    source_id: int
    source_name: str
    destination_id: int
    destination_name: str
    enabled: bool = True


class StatusResponse(BaseModel):
    status: str
    queue_size: int
    current_task: Optional[str]
    uptime: str
    active_forwards: int


class ChatInfo(BaseModel):
    id: int
    title: str
    type: str
    username: Optional[str]


class KeywordForwardRequest(BaseModel):
    source_id: int
    destination_id: int
    keyword: Optional[str] = None
    limit: int = 500
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    timezone_name: str = "UTC"
    dry_run: bool = False


# Global state
telegram_client: Optional[Telegram] = None
app_start_time = datetime.now()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    global telegram_client

    # Startup: reuse a session created by the CLI (`python main.py`). The web
    # dashboard never prompts for a login code itself, so this only succeeds
    # once an account has already been authenticated interactively and a
    # session file exists under sessions/.
    try:
        credentials_list = Credentials.get_all()
        if credentials_list:
            telegram_client = await Telegram.create(credentials_list[0])
        else:
            print(
                "No stored credentials found. Run `python main.py` once to "
                "authenticate an account before using the web dashboard."
            )
    except Exception as e:
        print(f"Failed to initialize Telegram client: {e}")
        telegram_client = None

    yield

    # Shutdown
    if telegram_client:
        await telegram_client.disconnect()


app = FastAPI(
    title="Telegram Forwarder Bot",
    description="Web interface for managing Telegram message forwarding",
    version="2.3.0",
    lifespan=lifespan,
)

# Mount static files and templates
# Use relative paths that work from both web/ directory and project root
script_dir = os.path.dirname(os.path.abspath(__file__))
static_dir = os.path.join(script_dir, "static")
templates_dir = os.path.join(script_dir, "templates")

# Ensure directories exist
os.makedirs(static_dir, exist_ok=True)
os.makedirs(templates_dir, exist_ok=True)

app.mount("/static", StaticFiles(directory=static_dir), name="static")
templates = Jinja2Templates(directory=templates_dir)


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Serve the main web interface."""
    return templates.TemplateResponse(request, "index.html")


@app.get(
    "/api/status", response_model=StatusResponse, dependencies=[Depends(verify_api_key)]
)
async def get_status():
    """Get bot status and queue metrics."""
    uptime_delta = datetime.now() - app_start_time
    uptime = str(uptime_delta).split(".")[0]

    if not telegram_client:
        return StatusResponse(
            status="Not Initialized",
            queue_size=0,
            current_task=None,
            uptime=uptime,
            active_forwards=0,
        )

    queue_status = telegram_client.get_queue_status()
    forwards = (
        ForwardConfig.read() if os.path.exists("resources/forwardConfig.json") else []
    )
    active_forwards = len([f for f in forwards if getattr(f, "enabled", True)])

    return StatusResponse(
        status=getattr(telegram_client, "status", "Idle"),
        queue_size=queue_status.get("queue_length", 0),
        current_task=queue_status.get("active_task"),
        uptime=uptime,
        active_forwards=active_forwards,
    )


@app.get(
    "/api/chats", response_model=List[ChatInfo], dependencies=[Depends(verify_api_key)]
)
async def get_chats():
    """Get available chats."""
    try:
        if not telegram_client:
            raise HTTPException(
                status_code=503, detail="Telegram client not initialized"
            )

        chats = await telegram_client.list_chats()
        return [
            ChatInfo(
                id=chat.id,
                title=chat.title or f"Chat {chat.id}",
                type=chat.type or "Unknown",
                username=getattr(chat, "username", None),
            )
            for chat in chats
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get(
    "/api/forwards", response_model=List[Dict], dependencies=[Depends(verify_api_key)]
)
async def get_forwards():
    """Get forwarding configurations."""
    try:
        forwards = (
            ForwardConfig.read()
            if os.path.exists("resources/forwardConfig.json")
            else []
        )
        return [
            {
                "source_id": f.sourceID,
                "source_name": f.sourceName,
                "destination_id": f.destinationID,
                "destination_name": f.destinationName,
                "enabled": getattr(f, "enabled", True),
            }
            for f in forwards
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/forwards", dependencies=[Depends(verify_api_key)])
async def create_forward(config: ForwardConfigCreate):
    """Create a new forwarding configuration."""
    try:
        # Read existing configs
        existing = (
            ForwardConfig.read()
            if os.path.exists("resources/forwardConfig.json")
            else []
        )

        # Create new config
        new_config = ForwardConfig(
            sourceID=config.source_id,
            sourceName=config.source_name,
            destinationID=config.destination_id,
            destinationName=config.destination_name,
        )

        # Add to existing and save
        existing.append(new_config)
        ForwardConfig.write(existing)

        return {"message": "Forward configuration created successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/forwards/{source_id}", dependencies=[Depends(verify_api_key)])
async def delete_forward(source_id: int):
    """Delete a forwarding configuration."""
    try:
        existing = ForwardConfig.read()
        filtered = [f for f in existing if f.sourceID != source_id]

        if len(filtered) == len(existing):
            raise HTTPException(
                status_code=404, detail="Forward configuration not found"
            )

        ForwardConfig.write(filtered)
        return {"message": "Forward configuration deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/forwards/{source_id}/toggle", dependencies=[Depends(verify_api_key)])
async def toggle_forward(source_id: int):
    """Toggle forwarding on/off."""
    try:
        existing = ForwardConfig.read()
        for config in existing:
            if config.sourceID == source_id:
                config.enabled = not getattr(config, "enabled", True)
                break
        else:
            raise HTTPException(
                status_code=404, detail="Forward configuration not found"
            )

        ForwardConfig.write(existing)
        return {"message": "Forward configuration updated successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/start-forwarding", dependencies=[Depends(verify_api_key)])
async def start_forwarding():
    """Start live message forwarding."""
    try:
        if not telegram_client:
            raise HTTPException(
                status_code=503, detail="Telegram client not initialized"
            )

        # This would need to be implemented based on your forwarding logic
        return {"message": "Live forwarding started"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/stop-forwarding", dependencies=[Depends(verify_api_key)])
async def stop_forwarding():
    """Stop live message forwarding."""
    try:
        if not telegram_client:
            raise HTTPException(
                status_code=503, detail="Telegram client not initialized"
            )

        # This would need to be implemented based on your forwarding logic
        return {"message": "Live forwarding stopped"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/keyword-forward", dependencies=[Depends(verify_api_key)])
async def keyword_forward(request: KeywordForwardRequest):
    """Search by keyword and forward matching messages."""
    try:
        if not telegram_client:
            raise HTTPException(
                status_code=503, detail="Telegram client not initialized"
            )

        sent_count = await telegram_client.forward_by_keyword(
            {
                "source_id": request.source_id,
                "destination_id": request.destination_id,
                "keyword": request.keyword,
                "limit": request.limit,
                "start_date": request.start_date,
                "end_date": request.end_date,
                "timezone_name": request.timezone_name,
                "dry_run": request.dry_run,
            }
        )

        mode = "previewed" if request.dry_run else "forwarded"
        keyword_label = f" for keyword '{request.keyword}'" if request.keyword else ""
        return {
            "message": (
                f"Keyword run completed: {sent_count} messages {mode}{keyword_label}."
            )
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn

    # Defaults to localhost-only; set WEB_HOST=0.0.0.0 explicitly (e.g. in a
    # container behind a reverse proxy) to expose it beyond this machine.
    uvicorn.run(
        app,
        host=os.getenv("WEB_HOST", "127.0.0.1"),
        port=int(os.getenv("WEB_PORT", "8000")),
    )
