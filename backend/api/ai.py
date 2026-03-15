from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession
from core.database import get_db
from core.security import get_current_user
from services.ai import call_ai
from services.prompt_builder import build_dost_prompt, build_report_prompt
from api.analytics import portfolio_analytics
from core.limiter import limiter

router = APIRouter(prefix="/api/ai", tags=["AI"])


@router.get("/dost")
@limiter.limit("10/minute")
async def ai_dost(
    request: Request,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    analytics = await portfolio_analytics(user=user, db=db)
    summary = analytics["summary"]
    summary["holdings_count"] = len(analytics["holdings"])
    summary["asset_types"] = list(set(h["asset_type"] for h in analytics["holdings"]))
    system, user_prompt = build_dost_prompt(summary)
    reply = await call_ai(system, user_prompt)
    return {"response": reply}


@router.get("/report")
@limiter.limit("5/minute")
async def ai_report(
    request: Request,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    analytics = await portfolio_analytics(user=user, db=db)
    summary = analytics["summary"]
    summary["holdings_count"] = len(analytics["holdings"])
    summary["asset_types"] = list(set(h["asset_type"] for h in analytics["holdings"]))
    summary["holdings"] = [
        {"symbol": h["symbol"], "asset_type": h["asset_type"], "pnl_pct": h.get("pnl_pct")}
        for h in analytics["holdings"]
    ]
    system, user_prompt = build_report_prompt(summary)
    reply = await call_ai(system, user_prompt)
    return {"response": reply, "format": "markdown"}
