from fastapi import Depends
from redis import Redis
from app.utils.dashboard import get_dashboard
from app.api.deps.auth_dep import get_db, get_redis
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, case
from typing import List
from sqlalchemy import or_
from app.db.models.agent import Agent
from app.db.models.user import User
from app.db.models.conversation import Conversation
from app.db.models.message import Message
from app.api.deps.auth_dep import get_db, require_role, get_current_user
from sqlalchemy.orm import selectinload
from typing import Optional
from datetime import date

router = APIRouter()


@router.get("/sessions")
async def get_sessions(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("tenant_admin")),
    status: Optional[str] = None,
    agent_id: Optional[int] = None,
    user_id: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
):
    tenant_id = current_user.tenant_id

    stmt = (
        select(
            Conversation.session_id,
            case((Conversation.ended_at.is_(None), "active"), else_="closed").label(
                "status"
            ),
            Conversation.id.label("conversation_id"),
            Conversation.user_id,
            Conversation.started_at,
            Conversation.ended_at,
            Agent.name.label("agent_name"),
            func.count(Message.id).label("messages_count"),
        )
        .join(Agent, Agent.id == Conversation.agent_id)
        .outerjoin(Message, Message.conversation_id == Conversation.id)
        .where(Conversation.tenant_id == tenant_id)
    )

    # -----------------------
    # Optional Filters
    # -----------------------

    if status == "active":
        stmt = stmt.where(Conversation.ended_at.is_(None))

    if status == "closed":
        stmt = stmt.where(Conversation.ended_at.is_not(None))

    if agent_id:
        stmt = stmt.where(Conversation.agent_id == agent_id)

    if user_id:
        stmt = stmt.where(Conversation.user_id == user_id)

    if start_date:
        stmt = stmt.where(func.date(Conversation.started_at) >= start_date)

    if end_date:
        stmt = stmt.where(func.date(Conversation.started_at) <= end_date)

    stmt = stmt.group_by(
        Conversation.session_id,
        Conversation.id,
        Conversation.user_id,
        Conversation.started_at,
        Conversation.ended_at,
        Agent.name,
    ).order_by(Conversation.started_at.desc())

    result = await db.execute(stmt)

    sessions = [dict(row) for row in result.mappings().all()]

    return {"sessions": sessions}
