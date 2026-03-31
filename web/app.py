"""FastAPI web interface for Telegram Forwarder Bot."""

import os
import sys
from contextlib import asynccontextmanager
from datetime import datetime

# Add the parent directory to Python path so we can import from source
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from typing import Dict, List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from starlette.requests import Request

from source.core.Telegram import Telegram
from source.model.ForwardConfig import ForwardConfig


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
    keyword: str
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

    # Startup
    try:
        # Initialize Telegram client if credentials are available
        if all(
            [
                os.getenv("TELEGRAM_API_ID"),
                os.getenv("TELEGRAM_API_HASH"),
                os.getenv("TELEGRAM_PHONE"),
            ]
        ):
            # This would need to be adapted based on your credential system
            pass
    except Exception as e:
        print(f"Failed to initialize Telegram client: {e}")

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
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/api/status", response_model=StatusResponse)
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


@app.get("/api/chats", response_model=List[ChatInfo])
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


@app.get("/api/forwards", response_model=List[Dict])
async def get_forwards():
    """Get forwarding configurations."""
    try:
        forwards = ForwardConfig.read()
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


@app.post("/api/forwards")
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


@app.delete("/api/forwards/{source_id}")
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


@app.post("/api/forwards/{source_id}/toggle")
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


@app.post("/api/start-forwarding")
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


@app.post("/api/stop-forwarding")
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


@app.post("/api/keyword-forward")
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
        return {
            "message": (
                f"Keyword run completed: {sent_count} messages {mode} "
                f"for keyword '{request.keyword}'."
            )
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
