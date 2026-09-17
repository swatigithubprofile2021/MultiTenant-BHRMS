import uuid
from contextlib import asynccontextmanager
import json
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from langchain_redis import RedisChatMessageHistory
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession
from torch import select

from app.core.logger import logger
from app.core.config import settings
from app.core.jwt import decode_access_token
from app.api.deps.auth_dep import get_current_user, get_db
from app.api.deps.helper_dep import (
    get_agent_service,
    get_llm,
    get_embed,
    get_rerank,
    get_vectordb,
)
import time
from app.utils.agent import get_agent_by_id
from app.schemas.request_response import QueryRequest
from app.db.models.conversation import Conversation
from app.db.models.message import Message
from app.db.models.usage_log import UsageLog
from app.db.models.user import User
from app.schemas.common import MessageRoleEnum
import uuid
from datetime import datetime, timezone

router = APIRouter()


@router.websocket("")
async def chat(websocket: WebSocket, db: AsyncSession = Depends(get_db)):
    await websocket.accept()
    agent_id = websocket.query_params.get("agent_id")
    print("WebSocket connection initiated with agent_id:", agent_id)
    agent_name = "demo"
    user_name = "anonymous"
    token = websocket.query_params.get("token")
    conversation_id = None
    try:
        if agent_id is None:
            await websocket.send_json({"type": "error", "msg": "agent_id required."})
            websocket.close(code=1008)
            return
        else:
            try:
                agent_id = int(agent_id)
            except:
                await websocket.send_json({"type": "error", "msg": "invalid agent_id."})
                websocket.close(code=1008)
                return

        # Fetch agent info from DB
        agent = await get_agent_by_id(agent_id, db)
        if not agent:
            await websocket.send_json({"type": "error", "msg": "agent not found."})
            websocket.close(code=1008)
            return

        # Check if token is required
        if not agent.is_public:
            # Token required for private agents
            if not token:
                await websocket.send_json(
                    {"type": "error", "msg": "access not for public"}
                )
                websocket.close(code=1008)
                return

            # Validate token
            payload = decode_access_token(token)
            print("PAYLOAD:", payload)
            print("USER_ID TYPE:", type(payload.get("user_id")))
            print("TENANT_ID TYPE:", type(payload.get("tenant_id")))
            print("AGENT TENANT:", agent.tenant_id, type(agent.tenant_id))
            if not payload:
                await websocket.send_json({"type": "error", "msg": "not valid token"})
                websocket.close(code=1008)
                return

            # Optionally, check tenant policy
            user_tenant_id = int(payload.get("tenant_id"))
            if agent.tenant_id != user_tenant_id:
                await websocket.send_json(
                    {"type": "error", "msg": "access not allowed."}
                )
                websocket.close(code=1008)
                return

            user_id = int(payload.get("user_id"))
        else:
            # Public bot is anonymous user
            user_id = f"public_user_{uuid.uuid4()}"

        tenant_id = agent.tenant_id
        agent_name = agent.name
        tenant_name = agent.tenant.name

        # set the user data
        session_id = uuid.uuid4()
        user_data = {
            "user_id": user_id,
            "tenant_id": tenant_id,
            "session_id": f"tnt_{tenant_id}_ag_{agent_id}_sid_{session_id}",
        }

        agent_config = agent.config

        async def get_service_instance():
            request = websocket
            llm = get_llm(
                request,
                temperature=agent_config.temperature,
                model=agent_config.model_name,
            )

            if llm is None:
                yield
            else:
                async for service in get_agent_service(
                    request=request,
                    is_chat_service=agent.is_chat_agent,
                    user=user_data,
                    llm=llm,
                    embed=get_embed(request),
                    vectordb=get_vectordb(request),
                    reranker=get_rerank(request),
                    allowed_sources=agent.config.allowed_sources or [],
                    agent_prompt=agent_config.system_prompt or "",
                    tone=agent.config.tone.description if agent.config.tone else ""
                    
                ):
                    yield service

        # 3. Enter the persistent session
        async with asynccontextmanager(get_service_instance)() as agent_service:
            if agent_service is None:
                msg = "model not available. contact to platfrom admin."
                await websocket.send_json({"type": "error", "msg": msg})
                websocket.close(code=1008, reason=msg)
                return

            await websocket.send_json(
                {"status": "ready", "data": {"welcome_message": agent_config.welcome_message if agent_config.welcome_message else f"Hi! I'm {agent_name}. How can I assist you today?"},"agent_name": agent_name}
            )

        redis_client = None
        if token is not None or agent.is_chat_agent:
            redis_client = websocket.app.state.sync_redis

        # if agent is chat agent then pass history
        if agent.is_chat_agent:
            chat_history = RedisChatMessageHistory(
                redis_client=redis_client,  # pass the shared client
                session_id=user_data["session_id"],
                ttl=settings.CHAT_HISTORY_TTL,
                session_length=settings.CHAT_HISTORY_LENGTH,
                key_prefix="message_store:",
            )
            agent_service.with_redis_chat_history(chat_history)

        
        while True:
            raw_data = await websocket.receive_text()

            # Check blacklist before processing each message
            if token is not None:
                if redis_client.get(f"blacklist:{token}"):
                    await websocket.close(code=4001)
                    break
            try:
                # 2. Parse JSON and validate against your Pydantic Model
                data_json = json.loads(raw_data)
                # This throws a ValidationError if 'query' is missing or wrong type
                query_request = QueryRequest(**data_json)
                query_request.session_id = user_data["session_id"]

            except (json.JSONDecodeError, ValidationError) as e:
                # 3. Handle bad data gracefully
                await websocket.send_json(
                    {
                        "type": "error",
                        "message": "Invalid request format. Expected 'question' field.",
                    }
                )
                continue

            question = query_request.question
            full_answer = ""

            # create conversation only once
            if conversation_id is None:
                conversation_id = uuid.uuid4()
                # Create conversation (simple version: new conversation per session)
                conversation = Conversation(
                    id=conversation_id,
                    tenant_id=user_data["tenant_id"],
                    user_id=f'tnt_{tenant_id}_usr_{user_data["user_id"]}',
                    session_id=user_data["session_id"],
                    agent_id=agent_id,
                    started_at=datetime.now(timezone.utc),
                )

                db.add(conversation)
                await db.flush()

            # 4. Stream the response using the 'warm' service
            start_time = time.time()
            usage_metadata = {}
            async for chunk in agent_service.stream_response(query_request):

                # Accumulate the answer for saving later
                if chunk["type"] == "token":
                    full_answer += chunk["content"]

                elif chunk["type"] == "final_metrics":
                    usage_metadata.update(chunk["usage_metadata"])

                # Send tokens/sources to frontend
                await websocket.send_json(chunk)

            await websocket.send_json({"type": "end"})

            if full_answer and question and agent.is_chat_agent:
                # We use the 'memory' object we initialized at the start of the loop
                chat_history.add_user_message(question)
                chat_history.add_ai_message(full_answer)
                print(f"✅ Saved to Redis: message_store:{user_data.get('session_id')}")

            if full_answer and question:
                # Save user message
                user_msg = Message(
                    id=uuid.uuid4(),
                    conversation_id=conversation.id,
                    tenant_id=user_data["tenant_id"],
                    role=MessageRoleEnum.USER,
                    content=question,
                    total_tokens=usage_metadata["input_tokens"],
                )

                # Save assistant message
                assistant_msg = Message(
                    id=uuid.uuid4(),
                    conversation_id=conversation.id,
                    tenant_id=user_data["tenant_id"],
                    role=MessageRoleEnum.ASSISTANT,
                    content=full_answer,
                    total_tokens=usage_metadata[
                        "output_tokens"
                    ],  # simple approximation
                )

                db.add(user_msg)
                db.add(assistant_msg)

                # Save usage log
                usage = UsageLog(
                    id=uuid.uuid4(),
                    tenant_id=tenant_id,
                    tenant_name=tenant_name,
                    user_id=f'tnt_{tenant_id}_usr_{user_data["user_id"]}',
                    user_name=user_name,
                    session_id=user_data["session_id"],
                    agent_id=agent_id,
                    agent_name=agent_name,
                    agent_category=agent.specialisation.name,
                    is_chat_agent=agent.is_chat_agent,
                    model=agent_config.model_name,
                    prompt_tokens=usage_metadata["input_tokens"],
                    completion_tokens=len(full_answer.split()),  # simple approximation
                    total_tokens=usage_metadata["total_tokens"],
                    estimated_cost=0.0,
                    response_time_ms=int((time.time() - start_time) * 1000),
                    created_at=datetime.now(timezone.utc),
                )
                db.add(usage)
                await db.commit()
    except WebSocketDisconnect:
        logger.info(f"Session {user_data.get('session_id')} closed.")
        # reason = f"Session {user_data.get('session_id')} closed."

    except Exception as e:
        logger.exception(
            f"/chat: {e}",
            stack_info=True,
            exc_info=True,
        )

    finally:
        if conversation_id and conversation and conversation.ended_at is None:
            conversation.ended_at = datetime.now(timezone.utc)
            await db.commit()
    # finally:
    #     await websocket.close(reason=reason)
