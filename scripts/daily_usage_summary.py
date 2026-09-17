import asyncio
from datetime import date, timedelta
import schedule
import time

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func

from app.db.session import AsyncSessionLocal
from app.models import UsageLog, Conversation, Message, Agent, Tenant, DailyUsageSummary


async def aggregate_daily_usage(target_date: date = None):
    """
    Aggregate daily usage for all tenants and agents.
    """
    async with AsyncSessionLocal() as db:
        if not target_date:
            target_date = date.today() - timedelta(days=1)

        # Fetch all tenants
        orgs_result = await db.execute(select(Tenant.id))
        org_ids = [r[0] for r in orgs_result.all()]

        for org_id in org_ids:
            # Fetch all agents for tenant
            agents_result = await db.execute(
                select(Agent.id).where(Agent.tenant_id == org_id)
            )
            agent_ids = [r[0] for r in agents_result.all()]

            for agent_id in agent_ids:
                # Aggregate usage logs
                usage_result = await db.execute(
                    select(
                        func.count(UsageLog.id),
                        func.sum(UsageLog.total_tokens),
                        func.sum(UsageLog.estimated_cost),
                        func.avg(UsageLog.response_time_ms),
                    ).where(
                        UsageLog.tenant_id == org_id,
                        UsageLog.agent_id == agent_id,
                        func.date(UsageLog.created_at) == target_date,
                    )
                )
                usage_count, total_tokens, total_cost, avg_response_time = (
                    usage_result.scalar_one_or_none() or (0, 0, 0, 0)
                )

                # Aggregate conversations
                conv_result = await db.execute(
                    select(func.count(Conversation.id)).where(
                        Conversation.tenant_id == org_id,
                        Conversation.agent_id == agent_id,
                        func.date(Conversation.started_at) == target_date,
                    )
                )
                total_conversations = conv_result.scalar() or 0

                # Aggregate messages
                msg_result = await db.execute(
                    select(func.count(Message.id)).where(
                        Message.tenant_id == org_id,
                        Message.agent_id == agent_id,
                        func.date(Message.created_at) == target_date,
                    )
                )
                total_messages = msg_result.scalar() or 0

                avg_conv_length = (
                    total_messages / total_conversations if total_conversations else 0
                )

                # Insert or update daily summary
                summary = DailyUsageSummary(
                    date=target_date,
                    tenant_id=org_id,
                    agent_id=agent_id,
                    total_conversations=total_conversations,
                    total_messages=total_messages,
                    total_tokens=total_tokens or 0,
                    estimated_cost=total_cost or 0.0,
                    avg_conversation_length=avg_conv_length,
                    avg_response_time_ms=avg_response_time or 0.0,
                )
                db.add(summary)

        await db.commit()
    print(f"Daily usage summary aggregated for {target_date}")


def run_scheduler():
    # Schedule to run daily at 00:05 AM
    schedule.every().day.at("00:05").do(lambda: asyncio.run(aggregate_daily_usage()))

    print("Scheduler started...")
    while True:
        schedule.run_pending()
        time.sleep(60)  # check every minute


if __name__ == "__main__":
    run_scheduler()
