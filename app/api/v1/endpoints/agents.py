from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import List
from sqlalchemy import or_
from app.api.deps.auth_dep import get_db, require_role
from app.api.deps.helper_dep import get_llm_manager
from app.db.models.agent import Agent
from app.db.models.user import User
from app.db.models.agent_config import AgentConfig
from app.schemas.agent import (
    AgentCreate,
    AgentUpdate,
    AgentResponse,
    AgentResponseList,
    Pageination,
    AgentConfigResponse,
)
from sqlalchemy.orm import selectinload
from app.ai.llm.llm_manager import LLMManager
from app.db.models.tone import Tone

router = APIRouter()

# =====================================================
# CREATE AGENT
# =====================================================


@router.post("/", response_model=AgentResponse)
async def create_agent(
    payload: AgentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("tenant_admin")),
):
    if not current_user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Agents must be created under a tenant.",
        )
    """
    # Duplicate name check
    stmt = select(Agent).where(
        Agent.tenant_id == current_user.tenant_id,
        Agent.name == payload.name,
    )
    result = await db.execute(stmt)
    existing_agent = result.scalar_one_or_none()

    if existing_agent:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Agent with name '{payload.name}' already exists.",
        )
    """   
    if not payload.tone_id or payload.tone_id == 0:
        result = await db.execute(select(Tone).where(Tone.is_default))
        default_tone = result.scalar_one()
        
        if not default_tone:
            raise HTTPException(500, "Default tone not configured")
        tone_id = default_tone.id
        print(f"Using default tone_id: {tone_id}")
        
        
    else:
        tone_id = payload.tone_id    

    # Create Agent
    agent = Agent(
        tenant_id=current_user.tenant_id,
        created_by=current_user.id,
        name=payload.name,
        alias_name=payload.alias_name,
        specialisation_id=payload.specialisation_id,
        description=payload.description,
        is_public=payload.is_public,
        is_chat_agent=payload.is_chat_agent,
    )

    # Create Structured Config (1-to-1)
    agent.config = AgentConfig(
        model_name=payload.model_name,
        temperature=payload.temperature,
        system_prompt=payload.system_prompt,
        allowed_sources=payload.allowed_sources,
        tone_id=tone_id,
        welcome_message=payload.welcome_message,
        theme_id =  payload.theme_id
    )

    db.add(agent)
    await db.commit()
    stmt = (
        select(Agent)
        .options(selectinload(Agent.config), selectinload(Agent.specialisation))
        .where(Agent.id == agent.id)
    )
    result = await db.execute(stmt)
    agent = result.scalar_one()
    return agent

    # return AgentResponse(
    #     id=agent.id,
    #     name=agent.name,
    #     is_public=agent.is_public,
    #     is_chat_agent=agent.is_chat_agent,
    #     alias_name=agent.alias_name,
    #     description=agent.description,
    #     specialisation_id=agent.specialisation_id,
    #     specialisation=agent.specialisation.name if agent.specialisation else None,
    #     created_at=agent.created_at,
    #     config=agent.config
    # )


# =====================================================
# LIST AGENTS (Tenant Scoped)
# =====================================================
@router.get("/", response_model=AgentResponseList)
async def list_agents(
    is_template: bool = False,
    limit: int = Query(10, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("tenant_admin")),
):
    # Base query
    base_query = select(Agent).where(Agent.is_template == is_template)

    if not is_template:
        base_query = base_query.filter(Agent.tenant_id == current_user.tenant_id)

    # Total count
    count_stmt = select(func.count()).select_from(base_query.subquery())
    total_result = await db.execute(count_stmt)
    total = total_result.scalar_one()

    # Apply eager loading + ordering + pagination
    stmt = (
        base_query.options(
            selectinload(Agent.config), selectinload(Agent.specialisation)
        )
        .order_by(Agent.created_at.desc())
        .offset(offset)
        .limit(limit)
    )

    result = await db.execute(stmt)
    agents = result.scalars().all()

    return AgentResponseList(
        data=agents,
        pagination=Pageination(
            total=total,
            limit=limit,
            offset=offset,
            has_more=offset + limit < total,
        ),
    )


# =====================================================
# UPDATE AGENT
# =====================================================
@router.patch("/{agent_id}", response_model=AgentResponse)
async def update_agent(
    agent_id: int,
    payload: AgentUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("tenant_admin")),
):
    stmt = (
        select(Agent)
        .options(selectinload(Agent.config))
        .where(
            Agent.id == agent_id,
            Agent.tenant_id == current_user.tenant_id,
        )
    )
    result = await db.execute(stmt)
    agent = result.scalar_one_or_none()

    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found in your tenant.",
        )

    # Duplicate check if name is changing
    if payload.name and payload.name != agent.name:
        duplicate_stmt = select(Agent).where(
            Agent.tenant_id == current_user.tenant_id,
            Agent.name == payload.name,
        )
        duplicate_result = await db.execute(duplicate_stmt)
        duplicate_agent = duplicate_result.scalar_one_or_none()

        if duplicate_agent:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Agent with name '{payload.name}' already exists.",
            )

        agent.name = payload.name

    if payload.is_chat_agent is not None:
        agent.is_chat_agent = payload.is_chat_agent

    if payload.specialisation_id is not None:
        agent.specialisation_id = payload.specialisation_id

    if payload.alias_name is not None:
        agent.alias_name = payload.alias_name

    # config related updates
    if payload.model_name is not None:
        agent.config.model_name = payload.model_name

    if payload.temperature is not None:
        agent.config.temperature = payload.temperature

    if payload.system_prompt is not None:
        agent.config.system_prompt = payload.system_prompt

    if payload.is_public is not None:
        agent.is_public = payload.is_public

    if payload.allowed_sources is not None:
        agent.config.allowed_sources = payload.allowed_sources
        
    if payload.tone_id is not None:
        agent.config.tone_id = payload.tone_id

    if payload.welcome_message is not None:
        agent.config.welcome_message = payload.welcome_message 
        
    if payload.theme_id is not None:
        agent.config.theme_id = payload.theme_id       

    await db.commit()

    stmt = (
        select(Agent)
        .options(selectinload(Agent.config), selectinload(Agent.specialisation))
        .where(Agent.id == agent.id)
    )
    result = await db.execute(stmt)
    return result.scalar_one()


# =====================================================
# DELETE AGENT
# =====================================================
@router.delete("/{agent_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_agent(
    agent_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("tenant_admin")),
):
    stmt = select(Agent).where(
        Agent.id == agent_id,
        Agent.tenant_id == current_user.tenant_id,
    )
    result = await db.execute(stmt)
    agent = result.scalar_one_or_none()

    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found in your tenant.",
        )

    await db.delete(agent)
    await db.commit()

    return {"message": "Agent deleted successfully"}


@router.get("/models")
async def get_available_models(llm_manager: LLMManager = Depends(get_llm_manager)):

    models = llm_manager.get_available_models()
    return {"models": models}
