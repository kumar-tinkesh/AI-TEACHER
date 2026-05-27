from fastapi import Depends, HTTPException, status
from sqlmodel import Session, select

from auth.database import get_session
from auth.dependencies import get_current_user, RoleChecker
from auth.models import Teacher, Student, UserRole
from admin.students.endpoints import router, logger


@router.delete(
    "/{student_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(RoleChecker([UserRole.TEACHER]))]
)
def delete_student(
    student_id: int,
    teacher: Teacher = Depends(get_current_user),
    db: Session = Depends(get_session)
):
    """
    Delete a student account.
    Only accessible by users with the TEACHER role.
    Can only delete students created by this teacher.
    """
    statement = select(Student).where(
        Student.id == student_id,
        Student.teacher_id == teacher.id
    )
    student = db.exec(statement).first()
    if not student:
        logger.warning(
            "Student deletion failed: id=%d not found or not managed by teacher_id=%d",
            student_id, teacher.id,
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Student not found or not managed by you"
        )

    db.delete(student)
    db.commit()
    logger.info("Student deleted: id=%d username='%s' by teacher_id=%d", student_id, student.username, teacher.id)
    return None
