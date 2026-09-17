import json
from sqlalchemy import select, func, union_all, literal_column, or_
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from datetime import date, timedelta
from redis import Redis
from app.db.models.message import Message
from app.db.models.conversation import Conversation
from app.db.models.usage_log import UsageLog
from app.db.models.daily_usage_summary import DailyUsageSummary
from app.db.models.agent import Agent
from app.db.models.agent_config import AgentConfig

CACHE_TTL_SECONDS = 60  # cache today metrics for 1 minute


async def get_today_metrics_redis(
    redis: Redis, db, role: str, tenant_id: Optional[str] = None, top_limit: int = 5
):
    key = f"dashboard:{role}:{tenant_id}:{date.today()}"

    cached = await redis.get(key)
    if cached:
        return json.loads(cached)

    # Filters
    today_filters_msg = []
    today_filters_conv = []
    today_filters_usage = []
    if role == "tenant_admin" and tenant_id:
        today_filters_msg.append(Message.tenant_id == tenant_id)
        today_filters_conv.append(Conversation.tenant_id == tenant_id)
        today_filters_usage.append(UsageLog.tenant_id == tenant_id)
    today_filters_msg.append(func.date(Message.created_at) == date.today())
    today_filters_conv.append(func.date(Conversation.started_at) == date.today())
    today_filters_usage.append(func.date(UsageLog.created_at) == date.today())

    # Conversations & Messages today
    today_convs = (
        await db.execute(select(func.count(Conversation.id)).where(*today_filters_conv))
    ).scalar() or 0
    today_msgs = (
        await db.execute(select(func.count(Message.id)).where(*today_filters_msg))
    ).scalar() or 0
    avg_messages = today_msgs / today_convs if today_convs else 0

    # Top users today (tenant only)
    top_users = []
    if role == "tenant_admin":
        top_users_stmt = (
            select(
                UsageLog.user_id,
                UsageLog.user_name,
                func.count(UsageLog.id).label("total_requests"),
            )
            .where(*today_filters_usage)
            .group_by(UsageLog.user_id, UsageLog.user_name)
            .order_by(func.count(UsageLog.id).desc())
            .limit(top_limit)
        )
        top_users = (await db.execute(top_users_stmt)).all()

    # Top agents today
    top_agents_today_stmt = (
        select(
            UsageLog.agent_id,
            UsageLog.agent_name,
            func.sum(UsageLog.total_tokens).label("total_tokens"),
        )
        .where(*today_filters_usage)
        .group_by(UsageLog.agent_id, UsageLog.agent_name)
        .order_by(func.sum(UsageLog.total_tokens).desc())
        .limit(top_limit)
    )
    top_agents_today = (await db.execute(top_agents_today_stmt)).all()

    print(top_agents_today)

    result = {
        "today_conversations": today_convs,
        "today_messages": today_msgs,
        "avg_messages_per_conversation_today": avg_messages,
        "top_users_today": top_users,
        "top_agents_today": top_agents_today,
    }

    # Cache in Redis
    await redis.set(key, json.dumps(result, default=str), ex=CACHE_TTL_SECONDS)
    return result


async def get_dashboard(
    redis: Redis,
    db: AsyncSession,
    role: str,
    tenant_id: Optional[str] = None,
    time_filter: str = "max",
    top_limit: int = 5,
):
    today = date.today()

    # ================================
    # 🚨 FLOW TEST MODE (Temporary)
    # Senior historical logic commented
    # ================================

    # -------------------------------
    # ORIGINAL HISTORICAL LOGIC (COMMENTED)
    # -------------------------------

    # --- Date ranges ---
    if time_filter == "day":
        start_date, end_date = today, today
    elif time_filter == "week":
        start_date, end_date = today - timedelta(days=today.weekday()), today
    elif time_filter == "month":
        start_date, end_date = today.replace(day=1), today
    elif time_filter == "year":
        start_date, end_date = today.replace(month=1, day=1), today
    elif time_filter == "max":
        start_date, end_date = None, None
    else:
        raise ValueError("Invalid time_filter")

    filters = []
    if role == "tenant_admin" and tenant_id:
        filters.append(UsageLog.tenant_id == tenant_id)

    # ---- Total Conversations ----
    conv_filters = []
    if role == "tenant_admin" and tenant_id:
        conv_filters.append(Conversation.tenant_id == tenant_id)

    total_conversations = (
        await db.execute(select(func.count(Conversation.id)).where(*conv_filters))
    ).scalar() or 0

    # ---- Total Messages ----
    msg_filters = []
    if role == "tenant_admin" and tenant_id:
        msg_filters.append(Message.tenant_id == tenant_id)

    total_messages = (
        await db.execute(select(func.count(Message.id)).where(*msg_filters))
    ).scalar() or 0

    avg_messages_per_conversation = (
        total_messages / total_conversations if total_conversations else 0
    )

    # ---- Active Conversations ----
    active_conv_filters = []
    if role == "tenant_admin" and tenant_id:
        active_conv_filters.append(Conversation.tenant_id == tenant_id)

    active_conv_filters.append(Conversation.ended_at.is_(None))

    active_conversations = (
        await db.execute(
            select(func.count(Conversation.id)).where(*active_conv_filters)
        )
    ).scalar() or 0

    # ---- Active Users ----
    active_user_filters = []
    if role == "tenant_admin" and tenant_id:
        active_user_filters.append(Conversation.tenant_id == tenant_id)

    active_user_filters.append(Conversation.ended_at.is_(None))

    active_users = (
        await db.execute(
            select(func.count(func.distinct(Conversation.user_id))).where(
                *active_user_filters
            )
        )
    ).scalar() or 0

    # ---- Total Agents ----
    total_agents = (
        await db.execute(
            select(func.count(func.distinct(UsageLog.agent_id))).where(*filters)
        )
    ).scalar() or 0

    # ---- Top Agents ----

    historical_agents = select(
        DailyUsageSummary.agent_id,
        DailyUsageSummary.agent_name,
        DailyUsageSummary.total_tokens.label("total_tokens"),
        DailyUsageSummary.tenant_name,
    )

    # 🔧 APPLY TENANT FILTER
    if role == "tenant_admin" and tenant_id:
        historical_agents = historical_agents.where(
            DailyUsageSummary.tenant_id == tenant_id
        )

    # 🔧 APPLY DATE FILTER
    if start_date:
        historical_agents = historical_agents.where(
            DailyUsageSummary.date.between(start_date, end_date)
        )

    live_agents = select(
        UsageLog.agent_id,
        UsageLog.agent_name,
        func.sum(UsageLog.total_tokens).label("total_tokens"),
        UsageLog.tenant_name,
    ).where(*filters)

    # 🔧 APPLY DATE FILTER
    if start_date:
        live_agents = live_agents.where(
            func.date(UsageLog.created_at).between(start_date, end_date)
        )

    live_agents = live_agents.group_by(
        UsageLog.agent_id, UsageLog.agent_name, UsageLog.tenant_name
    )

    combined_agents = union_all(historical_agents, live_agents).subquery()

    top_agents_stmt = (
        select(
            combined_agents.c.agent_id,
            combined_agents.c.agent_name,
            func.sum(combined_agents.c.total_tokens).label("total_tokens"),
            combined_agents.c.tenant_name,
        )
        .group_by(
            combined_agents.c.agent_id,
            combined_agents.c.agent_name,
            combined_agents.c.tenant_name,
        )
        .order_by(func.sum(combined_agents.c.total_tokens).desc())
        .limit(top_limit)
    )

    result = await db.execute(top_agents_stmt)

    rows = result.mappings().all()

    top_agents = [
        {
            "agent_id": row["agent_id"],
            "name": row["agent_name"],
            "total_tokens": row["total_tokens"],
            "tenant_name": row["tenant_name"],
        }
        for row in rows
    ]  # top_agents = (await db.execute(top_agents_stmt)).all()

    response = {
        "total_agents": total_agents,
        "top_agents": top_agents,
        "total_conversations": total_conversations,
        "total_messages": total_messages,
        "avg_messages_per_conversation": avg_messages_per_conversation,
        "active_conversations": active_conversations,
        "active_users": active_users,
    }

    # ---- Role Specific ----

    # ORIGINAL (COMMENTED)

    # --- Historical Top Organizations ---
    if role in ["super_admin", "platform_admin"]:
        historical_orgs = select(
            DailyUsageSummary.tenant_id,
            DailyUsageSummary.tenant_name,
            DailyUsageSummary.total_tokens.label("total_tokens"),
        )

        # 🔧 APPLY TENANT FILTER
        if role == "tenant_admin" and tenant_id:
            historical_orgs = historical_orgs.where(
                DailyUsageSummary.tenant_id == tenant_id
            )

        # 🔧 APPLY DATE FILTER
        if start_date:
            historical_orgs = historical_orgs.where(
                DailyUsageSummary.date.between(start_date, end_date)
            )

        live_orgs = select(
            UsageLog.tenant_id,
            UsageLog.tenant_name,
            func.sum(UsageLog.total_tokens).label("total_tokens"),
        )

        # 🔧 APPLY DATE FILTER
        if start_date:
            live_orgs = live_orgs.where(
                func.date(UsageLog.created_at).between(start_date, end_date)
            )

        live_orgs = live_orgs.group_by(UsageLog.tenant_id, UsageLog.tenant_name)

        combined_orgs = union_all(historical_orgs, live_orgs).subquery()

        top_org_stmt = (
            select(
                combined_orgs.c.tenant_id,
                combined_orgs.c.tenant_name.label("name"),
                func.sum(combined_orgs.c.total_tokens).label("total_tokens"),
            )
            .group_by(combined_orgs.c.tenant_id, combined_orgs.c.tenant_name)
            .order_by(func.sum(combined_orgs.c.total_tokens).desc())
            .limit(top_limit)
        )

        result = await db.execute(top_org_stmt)

        response["top_organizations"] = [dict(row) for row in result.mappings().all()]

    # ---- Tenant Top Users ----
    if role == "tenant_admin":
        historical_users = select(
            DailyUsageSummary.user_id,
            DailyUsageSummary.user_name,
            DailyUsageSummary.total_requests.label("total_requests"),
        )

        # 🔧 APPLY TENANT FILTER
        if role == "tenant_admin" and tenant_id:
            historical_users = historical_users.where(
                DailyUsageSummary.tenant_id == tenant_id
            )

        # 🔧 APPLY DATE FILTER
        if start_date:
            historical_users = historical_users.where(
                DailyUsageSummary.date.between(start_date, end_date)
            )

        live_users = select(
            UsageLog.user_id,
            UsageLog.user_name,
            func.count(UsageLog.id).label("total_requests"),
        ).where(*filters)

        # 🔧 APPLY DATE FILTER
        if start_date:
            live_users = live_users.where(
                func.date(UsageLog.created_at).between(start_date, end_date)
            )

        live_users = live_users.group_by(UsageLog.user_id, UsageLog.user_name)

        combined_users = union_all(historical_users, live_users).subquery()

        top_users_stmt = (
            select(
                combined_users.c.user_id,
                combined_users.c.user_name,
                func.sum(combined_users.c.total_requests).label("total_requests"),
            )
            .group_by(combined_users.c.user_id, combined_users.c.user_name)
            .order_by(func.sum(combined_users.c.total_requests).desc())
            .limit(top_limit)
        )

        result = await db.execute(top_users_stmt)

        response["top_users"] = [dict(row) for row in result.mappings().all()]
    return response
