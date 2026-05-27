from fastapi import Depends, HTTPException, status
from sqlmodel import Session, select

from auth.database import get_session
from auth.dependencies import get_current_user, RoleChecker
from auth.models import Teacher, UserRole
from admin.agents.models import Agent
from admin.agents.endpoints import router, logger


@router.delete(
    "/{agent_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(RoleChecker([UserRole.TEACHER]))]
)
def delete_agent(
    agent_id: int,
    teacher: Teacher = Depends(get_current_user),
    db: Session = Depends(get_session)
):
    """
    Delete an agent and all stored chunks.
    Only accessible by users with the TEACHER role.
    Can only delete agents created by this teacher.
    """
    statement = select(Agent).where(
        Agent.id == agent_id,
        Agent.created_by_id == teacher.id
    )
    agent = db.exec(statement).first()
    if not agent:
        logger.warning(
            "Agent deletion failed: id=%d not found or not managed by teacher_id=%d",
            agent_id, teacher.id,
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found or not managed by you"
        )

    db.delete(agent)
    db.commit()
    logger.info(
        "Agent deleted: id=%d name='%s' by teacher_id=%d",
        agent_id, agent.name, teacher.id
    )
    return None
