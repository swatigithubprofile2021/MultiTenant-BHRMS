from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from app.db.models.agent import Agent
from app.db.models.agent_config import AgentConfig


async def get_agent_by_id(agent_id: int, db: AsyncSession):
    """Fetch agent from the database by its ID."""
    async with db.begin():
        stmt = (
            select(Agent)
            .options(selectinload(Agent.config).selectinload(AgentConfig.tone))
            .options(selectinload(Agent.tenant))
            .options(selectinload(Agent.specialisation))
            .filter( Agent.is_template == False)  # Exclude templates
            .filter(Agent.id == agent_id)
        )
        print(f"Executing query: {stmt}")  # Debugging statement to check the generated SQL
        result = await db.execute(stmt)
        
        agent = result.scalar_one_or_none()  # Returns the agent or None
        print(f"Queried Agent: {agent}")  # Debugging statement

    return agent
