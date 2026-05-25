import io
import pytest
from fastapi.testclient import TestClient
from sqlmodel import SQLModel, Session, create_engine
from sqlmodel.pool import StaticPool

from main import app
from auth import get_session
from core.embeddings import load_model

# ==========================================
# Pytest Fixtures & Database Overrides
# ==========================================

DATABASE_URL = "sqlite://"


@pytest.fixture(name="session")
def session_fixture():
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
    load_model()  # Pre-load embedding model for tests
    def get_session_override():
        return session

    app.dependency_overrides[get_session] = get_session_override
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


# ==========================================
# Helpers
# ==========================================

def register_teacher(client: TestClient, username: str, password: str, full_name: str):
    return client.post(
        "/api/v1/auth/teacher/register",
        json={"username": username, "password": password, "full_name": full_name}
    )


def login_user(client: TestClient, username: str, password: str):
    resp = client.post("/api/v1/auth/login", json={"username": username, "password": password})
    assert resp.status_code == 200
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def create_student(client: TestClient, headers: dict, username: str, password: str, student_name: str, age: int, class_name: str, phone_number: str):
    return client.post(
        "/api/v1/admin/students",
        json={
            "username": username,
            "password": password,
            "student_name": student_name,
            "age": age,
            "class_name": class_name,
            "phone_number": phone_number
        },
        headers=headers
    )


def create_agent(client: TestClient, headers: dict, name: str, subject: str, description: str | None, file_content: bytes, filename: str = "agent.txt"):
    files = {"file": (filename, io.BytesIO(file_content), "text/plain")}
    data = {"name": name, "subject": subject}
    if description:
        data["description"] = description
    return client.post("/api/v1/admin/agents", data=data, files=files, headers=headers)


# ==========================================
# Admin Student Tests
# ==========================================

def test_student_create_success(client: TestClient):
    register_teacher(client, "teach1", "pass123", "Teacher One")
    headers = login_user(client, "teach1", "pass123")

    resp = create_student(client, headers, "stud1", "pass123", "Student One", 15, "10th", "9876543210")
    assert resp.status_code == 201
    data = resp.json()
    assert data["username"] == "stud1"
    assert data["full_name"] == "Student One"
    assert data["role"] == "student"
    assert data["age"] == 15
    assert data["class_name"] == "10th"
    assert data["phone_number"] == "9876543210"


def test_student_create_duplicate_username(client: TestClient):
    register_teacher(client, "teach1", "pass123", "Teacher One")
    headers = login_user(client, "teach1", "pass123")

    create_student(client, headers, "stud1", "pass123", "Student One", 15, "10th", "9876543210")
    resp = create_student(client, headers, "stud1", "pass123", "Student Two", 16, "11th", "1234567890")
    assert resp.status_code == 400
    assert resp.json()["detail"] == "Username already taken"


def test_student_list_and_rbac(client: TestClient):
    register_teacher(client, "teach1", "pass123", "Teacher One")
    t_headers = login_user(client, "teach1", "pass123")

    create_student(client, t_headers, "stud1", "pass123", "Student One", 15, "10th", "9876543210")
    create_student(client, t_headers, "stud2", "pass123", "Student Two", 16, "11th", "1111111111")

    # Teacher lists students
    resp = client.get("/api/v1/admin/students", headers=t_headers)
    assert resp.status_code == 200
    students = resp.json()
    assert len(students) == 2
    assert {s["username"] for s in students} == {"stud1", "stud2"}

    # Student tries to list (Forbidden)
    s_headers = login_user(client, "stud1", "pass123")
    resp = client.get("/api/v1/admin/students", headers=s_headers)
    assert resp.status_code == 403


def test_student_update_and_delete(client: TestClient):
    register_teacher(client, "teach1", "pass123", "Teacher One")
    headers = login_user(client, "teach1", "pass123")

    create = create_student(client, headers, "stud1", "pass123", "Student One", 15, "10th", "9876543210")
    student_id = create.json()["id"]

    # Update
    update = client.put(
        f"/api/v1/admin/students/{student_id}",
        json={
            "student_name": "Updated Name",
            "age": 17,
            "class_name": "12th",
            "phone_number": "0000000000"
        },
        headers=headers
    )
    assert update.status_code == 200
    data = update.json()
    assert data["full_name"] == "Updated Name"
    assert data["age"] == 17
    assert data["class_name"] == "12th"

    # Delete
    delete = client.delete(f"/api/v1/admin/students/{student_id}", headers=headers)
    assert delete.status_code == 204

    # Verify deleted
    resp = client.get("/api/v1/admin/students", headers=headers)
    assert len(resp.json()) == 0


def test_student_update_password(client: TestClient):
    register_teacher(client, "teach1", "pass123", "Teacher One")
    headers = login_user(client, "teach1", "pass123")

    create = create_student(client, headers, "stud1", "oldpass", "Student One", 15, "10th", "9876543210")
    student_id = create.json()["id"]

    # Update password
    client.put(f"/api/v1/admin/students/{student_id}", json={"password": "newpass"}, headers=headers)

    # Old password fails
    old = client.post("/api/v1/auth/login", json={"username": "stud1", "password": "oldpass"})
    assert old.status_code == 401

    # New password works
    new = client.post("/api/v1/auth/login", json={"username": "stud1", "password": "newpass"})
    assert new.status_code == 200


def test_student_cannot_access_other_teacher_students(client: TestClient):
    # Teacher A creates student
    register_teacher(client, "teacha", "pass123", "Teacher A")
    h_a = login_user(client, "teacha", "pass123")
    create_student(client, h_a, "stud1", "pass123", "Student A", 15, "10th", "9876543210")

    # Teacher B cannot see or modify student
    register_teacher(client, "teachb", "pass123", "Teacher B")
    h_b = login_user(client, "teachb", "pass123")

    resp = client.get("/api/v1/admin/students", headers=h_b)
    assert resp.status_code == 200
    assert len(resp.json()) == 0

    resp = client.put(f"/api/v1/admin/students/1", json={"student_name": "Hacked"}, headers=h_b)
    assert resp.status_code == 404


# ==========================================
# Admin Agent Tests
# ==========================================

def test_agent_create_with_file_and_chunks(client: TestClient):
    register_teacher(client, "teach1", "pass123", "Teacher One")
    headers = login_user(client, "teach1", "pass123")

    long_text = "Algebra is a branch of mathematics. " * 200  # ~5000 chars -> multiple chunks
    resp = create_agent(client, headers, "Math Agent", "Mathematics", "Math tutor", long_text.encode("utf-8"), "math.txt")
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Math Agent"
    assert data["subject"] == "Mathematics"
    assert data["is_active"] is True
    agent_id = data["id"]

    # Verify chunks exist
    chunks_resp = client.get(f"/api/v1/admin/agents/{agent_id}/chunks", headers=headers)
    assert chunks_resp.status_code == 200
    chunks = chunks_resp.json()
    assert len(chunks) >= 3
    for idx, chunk in enumerate(chunks):
        assert chunk["chunk_index"] == idx
        assert "content" in chunk
        assert len(chunk["content"]) > 0


def test_agent_create_duplicate_name(client: TestClient):
    register_teacher(client, "teach1", "pass123", "Teacher One")
    headers = login_user(client, "teach1", "pass123")

    create_agent(client, headers, "Physics Agent", "Physics", "Physics tutor", b"physics rules", "physics.txt")
    resp = create_agent(client, headers, "Physics Agent", "Chemistry", "Duplicate", b"chem", "chem.txt")
    assert resp.status_code == 400
    assert resp.json()["detail"] == "Agent name already taken"


def test_agent_list_update_delete(client: TestClient):
    register_teacher(client, "teach1", "pass123", "Teacher One")
    headers = login_user(client, "teach1", "pass123")

    create_agent(client, headers, "Agent A", "Math", "Desc A", b"content a", "a.txt")
    create_agent(client, headers, "Agent B", "Science", "Desc B", b"content b", "b.txt")

    # List
    resp = client.get("/api/v1/admin/agents", headers=headers)
    assert resp.status_code == 200
    agents = resp.json()
    assert len(agents) == 2

    agent_id = agents[0]["id"]

    # Update
    update = client.put(
        f"/api/v1/admin/agents/{agent_id}",
        json={"name": "Agent A Updated", "subject": "Advanced Math"},
        headers=headers
    )
    assert update.status_code == 200
    assert update.json()["name"] == "Agent A Updated"

    # Delete
    delete = client.delete(f"/api/v1/admin/agents/{agent_id}", headers=headers)
    assert delete.status_code == 204

    # Verify
    resp = client.get("/api/v1/admin/agents", headers=headers)
    assert len(resp.json()) == 1

    # Chunks gone
    chunks = client.get(f"/api/v1/admin/agents/{agent_id}/chunks", headers=headers)
    assert chunks.status_code == 404


def test_agent_chunks_rbac(client: TestClient):
    register_teacher(client, "teach1", "pass123", "Teacher One")
    t_headers = login_user(client, "teach1", "pass123")

    create_student(client, t_headers, "stud1", "pass123", "Student One", 15, "10th", "9876543210")
    s_headers = login_user(client, "stud1", "pass123")

    resp = create_agent(client, t_headers, "Secret Agent", "Spy", "Secret", b"secret data", "secret.txt")
    agent_id = resp.json()["id"]

    # Student cannot access chunks
    resp = client.get(f"/api/v1/admin/agents/{agent_id}/chunks", headers=s_headers)
    assert resp.status_code == 403

    # Student cannot list agents
    resp = client.get("/api/v1/admin/agents", headers=s_headers)
    assert resp.status_code == 403


# ==========================================
# Cross-Module RBAC
# ==========================================

def test_student_cannot_create_agent(client: TestClient):
    register_teacher(client, "teach1", "pass123", "Teacher One")
    t_headers = login_user(client, "teach1", "pass123")
    create_student(client, t_headers, "stud1", "pass123", "Student One", 15, "10th", "9876543210")
    s_headers = login_user(client, "stud1", "pass123")

    resp = create_agent(client, s_headers, "Hacker", "Hacking", "x", b"x", "x.txt")
    assert resp.status_code == 403


def test_teacher_cannot_be_created_by_student(client: TestClient):
    register_teacher(client, "teach1", "pass123", "Teacher One")
    t_headers = login_user(client, "teach1", "pass123")
    create_student(client, t_headers, "stud1", "pass123", "Student One", 15, "10th", "9876543210")
    s_headers = login_user(client, "stud1", "pass123")

    # Student tries to create another student
    resp = create_student(client, s_headers, "stud2", "pass123", "Student Two", 16, "11th", "1111111111")
    assert resp.status_code == 403


# ==========================================
# Edge Cases
# ==========================================

def test_agent_with_empty_text_file(client: TestClient):
    register_teacher(client, "teach1", "pass123", "Teacher One")
    headers = login_user(client, "teach1", "pass123")

    resp = create_agent(client, headers, "Empty Agent", "Math", "Empty file", b"", "empty.txt")
    assert resp.status_code == 201
    agent_id = resp.json()["id"]

    # No chunks for empty file
    chunks = client.get(f"/api/v1/admin/agents/{agent_id}/chunks", headers=headers)
    assert chunks.status_code == 200
    assert len(chunks.json()) == 0


def test_agent_with_binary_file(client: TestClient):
    register_teacher(client, "teach1", "pass123", "Teacher One")
    headers = login_user(client, "teach1", "pass123")

    # Unknown binary extension -> no text extraction -> no chunks
    resp = create_agent(client, headers, "Binary Agent", "Data", "Binary file", b"\x89PNG\r\n\x1a\n", "image.png")
    assert resp.status_code == 201
    agent_id = resp.json()["id"]

    chunks = client.get(f"/api/v1/admin/agents/{agent_id}/chunks", headers=headers)
    assert chunks.status_code == 200
    assert len(chunks.json()) == 0


def test_agent_embeddings_route(client: TestClient):
    register_teacher(client, "teach1", "pass123", "Teacher One")
    headers = login_user(client, "teach1", "pass123")

    long_text = "Machine learning is a subset of artificial intelligence. " * 50
    resp = create_agent(client, headers, "ML Agent", "AI", "ML desc", long_text.encode("utf-8"), "ml.txt")
    assert resp.status_code == 201
    agent_id = resp.json()["id"]

    # Embeddings should be auto-generated on creation
    embed_resp = client.post(f"/api/v1/admin/agents/{agent_id}/embeddings", headers=headers)
    assert embed_resp.status_code == 200
    data = embed_resp.json()
    assert data["agent_id"] == agent_id
    assert data["embeddings_generated"] >= 3


def test_agent_semantic_chunk_search(client: TestClient):
    register_teacher(client, "teach1", "pass123", "Teacher One")
    headers = login_user(client, "teach1", "pass123")

    # Create content with clearly separated topics
    math_text = "Algebra is a branch of mathematics dealing with symbols and rules for manipulating them. " * 40
    physics_text = "Physics is the natural science that studies matter, energy, and the fundamental forces of nature. " * 35
    chem_text = "Chemistry is the scientific study of the properties and behavior of matter and chemical reactions. " * 35
    combined = math_text + "\n\n" + physics_text + "\n\n" + chem_text

    resp = create_agent(client, headers, "Science Agent", "Science", "Multi-topic", combined.encode("utf-8"), "science.txt")
    assert resp.status_code == 201
    agent_id = resp.json()["id"]

    # All chunks (no embeddings/scores)
    all_chunks = client.get(f"/api/v1/admin/agents/{agent_id}/chunks", headers=headers).json()
    assert len(all_chunks) >= 3
    assert all("embedding" not in c for c in all_chunks)
    assert all("score" not in c for c in all_chunks)

    # Semantic search for math
    math_results = client.get(
        f"/api/v1/admin/agents/{agent_id}/search?query=algebra and mathematics&top_k=3",
        headers=headers
    ).json()
    assert len(math_results) <= 3
    assert math_results[0]["score"] >= math_results[-1]["score"]
    # Top result should mention math-related content
    assert "mathematics" in math_results[0]["content"].lower() or "algebra" in math_results[0]["content"].lower()

    # Semantic search for physics
    physics_results = client.get(
        f"/api/v1/admin/agents/{agent_id}/search?query=forces of nature and energy&top_k=3",
        headers=headers
    ).json()
    assert len(physics_results) <= 3
    assert physics_results[0]["score"] >= physics_results[-1]["score"]
    assert "physics" in physics_results[0]["content"].lower() or "matter" in physics_results[0]["content"].lower()
