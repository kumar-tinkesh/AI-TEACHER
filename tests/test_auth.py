import io
import pytest
from fastapi.testclient import TestClient
from sqlmodel import SQLModel, Session, create_engine
from sqlmodel.pool import StaticPool

from main import app
from auth import get_session, User, UserRole

# ==========================================
# Pytest Fixtures & Database Overrides
# ==========================================

# In-memory SQLite database configuration for isolated tests
DATABASE_URL = "sqlite://"

@pytest.fixture(name="session")
def session_fixture():
    # Use StaticPool to maintain a single connection in memory across threads
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session

@pytest.fixture(name="client")
def client_fixture(session: Session):
    def get_session_override():
        return session

    # Override database dependency injection
    app.dependency_overrides[get_session] = get_session_override
    client = TestClient(app)
    yield client
    # Clear overrides to avoid leaking test configurations
    app.dependency_overrides.clear()


# ==========================================
# Teacher (Admin) Sign Up & Login Tests
# ==========================================

def test_teacher_registration(client: TestClient):
    response = client.post(
        "/api/v1/auth/teacher/register",
        json={"username": "teacher1", "password": "securepassword123", "full_name": "Alice Smith"}
    )
    assert response.status_code == 201
    data = response.json()
    assert data["username"] == "teacher1"
    assert data["full_name"] == "Alice Smith"
    assert data["role"] == "teacher"
    assert "id" in data
    assert "hashed_password" not in data

def test_teacher_registration_duplicate_username(client: TestClient):
    # Register once
    client.post(
        "/api/v1/auth/teacher/register",
        json={"username": "teacher1", "password": "securepassword123", "full_name": "Alice Smith"}
    )
    # Register again with same username
    response = client.post(
        "/api/v1/auth/teacher/register",
        json={"username": "teacher1", "password": "anotherpassword", "full_name": "Alice Smith"}
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Username already registered"

def test_login_success(client: TestClient):
    # Pre-register teacher
    client.post(
        "/api/v1/auth/teacher/register",
        json={"username": "teacher1", "password": "securepassword123", "full_name": "Alice Smith"}
    )

    # Login
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "teacher1", "password": "securepassword123"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"

def test_login_invalid_credentials(client: TestClient):
    # Login non-existent user
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "unknown", "password": "somepassword"}
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Incorrect username or password"

    # Pre-register teacher
    client.post(
        "/api/v1/auth/teacher/register",
        json={"username": "teacher1", "password": "securepassword123", "full_name": "Alice Smith"}
    )

    # Login with wrong password
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "teacher1", "password": "wrongpassword"}
    )
    assert response.status_code == 401

def test_get_current_user_profile(client: TestClient):
    # Register
    client.post(
        "/api/v1/auth/teacher/register",
        json={"username": "teacher1", "password": "securepassword123", "full_name": "Alice Smith"}
    )
    # Login to get token
    login_resp = client.post(
        "/api/v1/auth/login",
        json={"username": "teacher1", "password": "securepassword123"}
    )
    token = login_resp.json()["access_token"]

    # Get profile
    response = client.get(
        "/api/v1/users/me",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == "teacher1"
    assert data["role"] == "teacher"

def test_get_profile_unauthorized(client: TestClient):
    # No auth header
    response = client.get("/api/v1/users/me")
    assert response.status_code == 401

    # Invalid token
    response = client.get(
        "/api/v1/users/me",
        headers={"Authorization": "Bearer invalidtoken123"}
    )
    assert response.status_code == 401


# ==========================================
# Student Management & RBAC Flows
# ==========================================

def test_student_management_flow(client: TestClient):
    # 1. Register Teacher
    teacher_reg = client.post(
        "/api/v1/auth/teacher/register",
        json={"username": "teacher1", "password": "teacherpassword", "full_name": "Teacher One"}
    )
    assert teacher_reg.status_code == 201

    # 2. Login Teacher to get access token
    teacher_login = client.post(
        "/api/v1/auth/login",
        json={"username": "teacher1", "password": "teacherpassword"}
    )
    assert teacher_login.status_code == 200
    teacher_token = teacher_login.json()["access_token"]
    teacher_headers = {"Authorization": f"Bearer {teacher_token}"}

    # 3. Teacher creates a student
    student_create = client.post(
        "/api/v1/admin/students",
        json={
            "username": "student1",
            "password": "studentpassword",
            "student_name": "Student One",
            "age": 15,
            "class_name": "10th Grade",
            "phone_number": "9876543210"
        },
        headers=teacher_headers
    )
    assert student_create.status_code == 201
    student_data = student_create.json()
    assert student_data["username"] == "student1"
    assert student_data["full_name"] == "Student One"
    assert student_data["role"] == "student"
    assert student_data["age"] == 15
    assert student_data["class_name"] == "10th Grade"
    assert student_data["phone_number"] == "9876543210"
    assert student_data["created_by_id"] == teacher_reg.json()["id"]
    student_id = student_data["id"]

    # 4. Attempt to create duplicate student
    student_duplicate = client.post(
        "/api/v1/admin/students",
        json={
            "username": "student1",
            "password": "studentpassword",
            "student_name": "Student One",
            "age": 15,
            "class_name": "10th Grade",
            "phone_number": "9876543210"
        },
        headers=teacher_headers
    )
    assert student_duplicate.status_code == 400

    # 5. Student logins with credentials
    student_login = client.post(
        "/api/v1/auth/login",
        json={"username": "student1", "password": "studentpassword"}
    )
    assert student_login.status_code == 200
    student_token = student_login.json()["access_token"]
    student_headers = {"Authorization": f"Bearer {student_token}"}

    # 6. Student views profile
    student_me = client.get("/api/v1/users/me", headers=student_headers)
    assert student_me.status_code == 200
    assert student_me.json()["username"] == "student1"
    assert student_me.json()["role"] == "student"

    # 7. Student tries to create another student (Forbidden)
    forbidden_create = client.post(
        "/api/v1/admin/students",
        json={
            "username": "student2",
            "password": "studentpassword",
            "student_name": "Student Two",
            "age": 16,
            "class_name": "11th Grade",
            "phone_number": "1234567890"
        },
        headers=student_headers
    )
    assert forbidden_create.status_code == 403

    # 8. List students as teacher
    list_students = client.get("/api/v1/admin/students", headers=teacher_headers)
    assert list_students.status_code == 200
    assert len(list_students.json()) == 1
    assert list_students.json()[0]["username"] == "student1"

    # 9. List students as student (Forbidden)
    list_students_student = client.get("/api/v1/admin/students", headers=student_headers)
    assert list_students_student.status_code == 403

    # 10. Teacher updates student details and password
    update_student = client.put(
        f"/api/v1/admin/students/{student_id}",
        json={
            "student_name": "Student One Updated",
            "password": "newstudentpassword",
            "age": 16,
            "class_name": "11th Grade",
            "phone_number": "1112223333"
        },
        headers=teacher_headers
    )
    assert update_student.status_code == 200
    updated = update_student.json()
    assert updated["full_name"] == "Student One Updated"
    assert updated["age"] == 16
    assert updated["class_name"] == "11th Grade"
    assert updated["phone_number"] == "1112223333"

    # 11. Student logins with OLD password (fails)
    old_login = client.post(
        "/api/v1/auth/login",
        json={"username": "student1", "password": "studentpassword"}
    )
    assert old_login.status_code == 401

    # 12. Student logins with NEW password (succeeds)
    new_login = client.post(
        "/api/v1/auth/login",
        json={"username": "student1", "password": "newstudentpassword"}
    )
    assert new_login.status_code == 200

    # 13. Teacher deletes student
    delete_student = client.delete(f"/api/v1/admin/students/{student_id}", headers=teacher_headers)
    assert delete_student.status_code == 204

    # 14. Verify student is deleted and cannot login anymore
    deleted_login = client.post(
        "/api/v1/auth/login",
        json={"username": "student1", "password": "newstudentpassword"}
    )
    assert deleted_login.status_code == 401

def test_role_based_dashboard_access(client: TestClient):
    # Create Teacher
    client.post(
        "/api/v1/auth/teacher/register",
        json={"username": "teacher_t1", "password": "password", "full_name": "Teacher One"}
    )
    t_token = client.post("/api/v1/auth/login", json={"username": "teacher_t1", "password": "password"}).json()["access_token"]
    t_headers = {"Authorization": f"Bearer {t_token}"}

    # Create Student
    client.post(
        "/api/v1/admin/students",
        json={
            "username": "student_s1",
            "password": "password",
            "student_name": "Student One",
            "age": 14,
            "class_name": "9th Grade",
            "phone_number": "9998887777"
        },
        headers=t_headers
    )
    s_token = client.post("/api/v1/auth/login", json={"username": "student_s1", "password": "password"}).json()["access_token"]
    s_headers = {"Authorization": f"Bearer {s_token}"}

    # Test Teacher Dashboard
    assert client.get("/api/v1/dashboard/teacher", headers=t_headers).status_code == 200
    assert client.get("/api/v1/dashboard/teacher", headers=s_headers).status_code == 403

    # Test Student Dashboard
    assert client.get("/api/v1/dashboard/student", headers=s_headers).status_code == 200
    assert client.get("/api/v1/dashboard/student", headers=t_headers).status_code == 403

    # Test Shared Dashboard
    assert client.get("/api/v1/dashboard/shared", headers=t_headers).status_code == 200
    assert client.get("/api/v1/dashboard/shared", headers=s_headers).status_code == 200


# ==========================================
# Agent Management & RBAC Flows
# ==========================================

def test_agent_management_flow(client: TestClient):
    # 1. Register Teacher
    client.post(
        "/api/v1/auth/teacher/register",
        json={"username": "teacher_agent", "password": "password", "full_name": "Teacher Agent"}
    )
    t_token = client.post("/api/v1/auth/login", json={"username": "teacher_agent", "password": "password"}).json()["access_token"]
    t_headers = {"Authorization": f"Bearer {t_token}"}

    # 2. Create an agent with a file (text file so it gets chunked)
    long_text = "This is a math tutoring agent. " * 100  # ~2700 chars to create multiple chunks
    agent_create = client.post(
        "/api/v1/admin/agents",
        data={
            "name": "Math Tutor",
            "description": "AI agent for math tutoring",
            "subject": "Mathematics"
        },
        files={"file": ("math_config.txt", io.BytesIO(long_text.encode("utf-8")), "text/plain")},
        headers=t_headers
    )
    assert agent_create.status_code == 201
    agent_data = agent_create.json()
    assert agent_data["name"] == "Math Tutor"
    assert agent_data["subject"] == "Mathematics"
    assert agent_data["is_active"] is True
    assert "original_filename" not in agent_data
    assert "file_path" not in agent_data
    agent_id = agent_data["id"]

    # 3. Retrieve chunks for the agent
    chunks_resp = client.get(f"/api/v1/admin/agents/{agent_id}/chunks", headers=t_headers)
    assert chunks_resp.status_code == 200
    chunks = chunks_resp.json()
    assert len(chunks) >= 2  # Long text should split into multiple chunks
    assert chunks[0]["agent_id"] == agent_id
    assert chunks[0]["chunk_index"] == 0
    assert "content" in chunks[0]

    # 4. Create duplicate agent (fails)
    dup = client.post(
        "/api/v1/admin/agents",
        data={
            "name": "Math Tutor",
            "description": "Duplicate",
            "subject": "Physics"
        },
        files={"file": ("dup.txt", io.BytesIO(b"dup"), "text/plain")},
        headers=t_headers
    )
    assert dup.status_code == 400

    # 5. List agents
    agents_list = client.get("/api/v1/admin/agents", headers=t_headers)
    assert agents_list.status_code == 200
    assert len(agents_list.json()) == 1
    assert agents_list.json()[0]["name"] == "Math Tutor"

    # 6. Update agent
    update = client.put(
        f"/api/v1/admin/agents/{agent_id}",
        json={
            "name": "Advanced Math Tutor",
            "subject": "Advanced Mathematics"
        },
        headers=t_headers
    )
    assert update.status_code == 200
    updated = update.json()
    assert updated["name"] == "Advanced Math Tutor"
    assert updated["subject"] == "Advanced Mathematics"

    # 7. Delete agent (cascades chunks)
    delete = client.delete(f"/api/v1/admin/agents/{agent_id}", headers=t_headers)
    assert delete.status_code == 204

    # 8. Verify agent is deleted
    agents_after = client.get("/api/v1/admin/agents", headers=t_headers)
    assert agents_after.status_code == 200
    assert len(agents_after.json()) == 0

    # 9. Verify chunks are also deleted
    chunks_after = client.get(f"/api/v1/admin/agents/{agent_id}/chunks", headers=t_headers)
    assert chunks_after.status_code == 404  # Agent not found, chunks gone too

def test_agent_rbac_as_student(client: TestClient):
    # Register teacher and create student
    client.post(
        "/api/v1/auth/teacher/register",
        json={"username": "teacher_rbac", "password": "password", "full_name": "Teacher RBAC"}
    )
    t_token = client.post("/api/v1/auth/login", json={"username": "teacher_rbac", "password": "password"}).json()["access_token"]
    t_headers = {"Authorization": f"Bearer {t_token}"}

    client.post(
        "/api/v1/admin/students",
        json={
            "username": "student_rbac",
            "password": "password",
            "student_name": "Student RBAC",
            "age": 16,
            "class_name": "11th Grade",
            "phone_number": "1112223333"
        },
        headers=t_headers
    )
    s_token = client.post("/api/v1/auth/login", json={"username": "student_rbac", "password": "password"}).json()["access_token"]
    s_headers = {"Authorization": f"Bearer {s_token}"}

    # Student tries to create agent (Forbidden)
    forbidden = client.post(
        "/api/v1/admin/agents",
        data={"name": "Hacker Agent", "description": "x", "subject": "Hacking"},
        files={"file": ("hack.txt", io.BytesIO(b"x"), "text/plain")},
        headers=s_headers
    )
    assert forbidden.status_code == 403

    # Student tries to list agents (Forbidden)
    list_forbidden = client.get("/api/v1/admin/agents", headers=s_headers)
    assert list_forbidden.status_code == 403
