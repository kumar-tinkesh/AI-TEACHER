from fastapi import Depends, HTTPException, status
from sqlmodel import Session, select

from auth.database import get_session
from auth.dependencies import get_current_user, RoleChecker
from auth.models import Teacher, UserRole
from admin.agents.models import Agent, AgentUpdate, AgentResponse
from admin.agents.endpoints import router, logger


@router.put(
    "/{agent_id}",
    response_model=AgentResponse,
    dependencies=[Depends(RoleChecker([UserRole.TEACHER]))]
)
def update_agent(
    agent_id: int,
    agent_in: AgentUpdate,
    teacher: Teacher = Depends(get_current_user),
    db: Session = Depends(get_session)
):
    """
    Update an agent's details.
    Only accessible by users with the TEACHER role.
    Can only update agents created by this teacher.
    """
    statement = select(Agent).where(
        Agent.id == agent_id,
        Agent.created_by_id == teacher.id
    )
    agent = db.exec(statement).first()
    if not agent:
        logger.warning(
            "Agent update failed: id=%d not found or not managed by teacher_id=%d",
            agent_id, teacher.id,
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found or not managed by you"
        )

    if agent_in.name is not None:
        agent.name = agent_in.name
    if agent_in.description is not None:
        agent.description = agent_in.description
    if agent_in.subject is not None:
        agent.subject = agent_in.subject
    if agent_in.class_name is not None:
        agent.class_name = agent_in.class_name
    if agent_in.is_active is not None:
        agent.is_active = agent_in.is_active

    db.add(agent)
    db.commit()
    db.refresh(agent)
    logger.info("Agent updated: id=%d by teacher_id=%d", agent.id, teacher.id)
    return agent
