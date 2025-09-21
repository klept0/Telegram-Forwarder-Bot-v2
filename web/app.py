"""FastAPI web interface for Telegram Forwarder Bot."""

import os
from contextlib import asynccontextmanager
from datetime import datetime
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
    version="2.0.0",
    lifespan=lifespan,
)

# Mount static files and templates
app.mount("/static", StaticFiles(directory="web/static"), name="static")
templates = Jinja2Templates(directory="web/templates")


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Serve the main web interface."""
    return templates.TemplateResponse("index.html", {"request": request})


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


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
