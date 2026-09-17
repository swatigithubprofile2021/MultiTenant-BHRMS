import asyncio
from sqlalchemy import select
from app.db.session import AsyncSessionLocal
from app.db.models.agent import Agent
from app.db.models.agent_config import AgentConfig

# Defaults
DEFAULT_TENANT_ID = 1  # System tenant for templates
SYSTEM_USER_ID = 1  # System admin user

# Template agents
DEFAULT_AGENTS = [
    {
        "name": "HR Assistant",
        "alias_name": "hr_assistant",
        "specialisation": "HR",
        "description": "Helps with HR policies, recruitment, onboarding, and employee queries.",
        "model_name": "qwen2.5:0.5b",
        "temperature": 0.3,
        "system_prompt": """
You are an HR assistant. Help with hiring, onboarding, leave policies, employee benefits, and workplace guidelines.
Be professional and compliant.
        """,
    },
    {
        "name": "General Assistant",
        "alias_name": "general_assistant",
        "specialisation": "GENERAL",
        "description": "General purpose AI assistant for common questions.",
        "model_name": "qwen2.5:0.5b",
        "temperature": 0.7,
        "system_prompt": """
You are a helpful general-purpose AI assistant. Answer clearly and concisely. Provide structured explanations when needed.
        """,
    },
    {
        "name": "Technical Support Agent",
        "alias_name": "tech_support",
        "specialisation": "TECHNICAL_SUPPORT",
        "description": "Provides IT and technical troubleshooting support.",
        "model_name": "qwen2.5:0.5b",
        "temperature": 0.2,
        "system_prompt": """
You are a technical support specialist. Help debug issues step-by-step. Ask clarifying questions before proposing solutions. Be precise and structured.
        """,
    },
]


async def seed_default_agents():
    async with AsyncSessionLocal() as session:
        for agent_data in DEFAULT_AGENTS:

            # Check if template already exists
            stmt = select(Agent).where(
                Agent.alias_name == agent_data["alias_name"], Agent.is_template == True
            )
            result = await session.execute(stmt)
            existing_agent = result.scalar_one_or_none()

            if existing_agent:
                print(f"✔ Template '{agent_data['name']}' already exists. Skipping.")
                continue

            # Create Agent
            new_agent = Agent(
                tenant_id=DEFAULT_TENANT_ID,
                created_by=SYSTEM_USER_ID,
                name=agent_data["name"],
                alias_name=agent_data["alias_name"],
                description=agent_data["description"],
                specialisation=agent_data["specialisation"],
                is_template=True,
                is_public=True,
            )
            session.add(new_agent)
            await session.flush()  # get agent.id

            # Create AgentConfig
            config = AgentConfig(
                agent_id=new_agent.id,
                model_name=agent_data["model_name"],
                temperature=agent_data["temperature"],
                system_prompt=agent_data["system_prompt"].strip(),
            )
            session.add(config)

        await session.commit()
        print("✅ Default template agents seeded successfully.")


if __name__ == "__main__":
    asyncio.run(seed_default_agents())
