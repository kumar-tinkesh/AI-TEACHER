# AI Teacher Platform API Reference

Base URL: `http://localhost:8000/api/v1`
Swagger UI: `http://localhost:8000/docs`

All authenticated endpoints require:
```
Authorization: Bearer <access_token>
```

---

## 1. Authentication

### POST /api/v1/auth/teacher/register
Register a new teacher (self-registration, no auth needed).

**Request Body:**
```json
{
  "username": "teacher1",
  "password": "securepassword123",
  "full_name": "Alice Smith"
}
```

**Response 201 Created:**
```json
{
  "id": 1,
  "username": "teacher1",
  "full_name": "Alice Smith",
  "role": "teacher",
  "created_by_id": null,
  "is_active": true,
  "created_at": "2026-05-25T10:00:00",
  "age": null,
  "class_name": null,
  "phone_number": null
}
```

**Response 400 Bad Request:**
```json
{"detail": "Username already registered"}
```

---

### POST /api/v1/auth/login
Login with username/password. Returns JWT access token.

**Request Body (JSON):**
```json
{
  "username": "teacher1",
  "password": "securepassword123"
}
```

**Response 200 OK:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

**Response 401 Unauthorized:**
```json
{"detail": "Incorrect username or password"}
```

**Response 403 Forbidden (deactivated):**
```json
{"detail": "Your account is deactivated"}
```

---

### GET /api/v1/users/me
Get current authenticated user profile.

**Headers:**
```
Authorization: Bearer <token>
```

**Response 200 OK:**
```json
{
  "id": 1,
  "username": "teacher1",
  "full_name": "Alice Smith",
  "role": "teacher",
  "created_by_id": null,
  "is_active": true,
  "created_at": "2026-05-25T10:00:00",
  "age": null,
  "class_name": null,
  "phone_number": null
}
```

**Response 401 Unauthorized:**
```json
{"detail": "Could not validate credentials"}
```

---

## 2. Admin - Students (Teacher only)

### POST /api/v1/admin/students
Create a new student account. Only teachers can call this.

**Headers:**
```
Authorization: Bearer <teacher_token>
Content-Type: application/json
```

**Request Body:**
```json
{
  "username": "student1",
  "password": "studentpassword",
  "student_name": "Student One",
  "age": 15,
  "class_name": "10th Grade",
  "phone_number": "9876543210"
}
```

**Response 201 Created:**
```json
{
  "id": 2,
  "username": "student1",
  "full_name": "Student One",
  "role": "student",
  "created_by_id": 1,
  "is_active": true,
  "created_at": "2026-05-25T10:05:00",
  "age": 15,
  "class_name": "10th Grade",
  "phone_number": "9876543210"
}
```

**Response 400 (duplicate username):**
```json
{"detail": "Username already taken"}
```

**Response 403 (student trying to create):**
```json
{"detail": "You do not have permission to access this resource"}
```

---

### GET /api/v1/admin/students
List all students created by the current teacher.

**Headers:**
```
Authorization: Bearer <teacher_token>
```

**Response 200 OK:**
```json
[
  {
    "id": 2,
    "username": "student1",
    "full_name": "Student One",
    "role": "student",
    "created_by_id": 1,
    "is_active": true,
    "created_at": "2026-05-25T10:05:00",
    "age": 15,
    "class_name": "10th Grade",
    "phone_number": "9876543210"
  }
]
```

---

### PUT /api/v1/admin/students/{student_id}
Update student details or password. Only the creating teacher can update.

**Headers:**
```
Authorization: Bearer <teacher_token>
Content-Type: application/json
```

**Request Body (all fields optional):**
```json
{
  "student_name": "Student One Updated",
  "password": "newpassword123",
  "age": 16,
  "class_name": "11th Grade",
  "phone_number": "1112223333",
  "is_active": true
}
```

**Response 200 OK:**
```json
{
  "id": 2,
  "username": "student1",
  "full_name": "Student One Updated",
  "role": "student",
  "created_by_id": 1,
  "is_active": true,
  "created_at": "2026-05-25T10:05:00",
  "age": 16,
  "class_name": "11th Grade",
  "phone_number": "1112223333"
}
```

**Response 404 (not found or not yours):**
```json
{"detail": "Student not found or not managed by you"}
```

---

### DELETE /api/v1/admin/students/{student_id}
Delete a student account. Only the creating teacher can delete.

**Headers:**
```
Authorization: Bearer <teacher_token>
```

**Response 204 No Content** (empty body)

**Response 404:**
```json
{"detail": "Student not found or not managed by you"}
```

---

## 3. Admin - Agents (Teacher only)

### POST /api/v1/admin/agents
Create a new AI agent with a file upload. File is processed in-memory, text is extracted and chunked for LLM retrieval.

**Headers:**
```
Authorization: Bearer <teacher_token>
Content-Type: multipart/form-data
```

**Form Fields:**
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| name | string | Yes | Unique agent name |
| subject | string | Yes | Subject specialization |
| description | string | No | Agent description |
| file | File | Yes | Any text file (.txt, .json, .csv, .py, .js, .html, .md, etc.) |

**cURL Example:**
```bash
curl -X POST 'http://localhost:8000/api/v1/admin/agents' \
  -H 'Authorization: Bearer eyJhbGci...' \
  -F 'name=Math Tutor' \
  -F 'subject=Mathematics' \
  -F 'description=AI agent for algebra' \
  -F 'file=@math_notes.txt'
```

**Response 201 Created:**
```json
{
  "id": 1,
  "name": "Math Tutor",
  "description": "AI agent for algebra",
  "subject": "Mathematics",
  "is_active": true,
  "created_by_id": 1,
  "created_at": "2026-05-25T10:10:00"
}
```

**Response 400 (duplicate name):**
```json
{"detail": "Agent name already taken"}
```

---

### GET /api/v1/admin/agents
List all agents created by the current teacher.

**Headers:**
```
Authorization: Bearer <teacher_token>
```

**Response 200 OK:**
```json
[
  {
    "id": 1,
    "name": "Math Tutor",
    "description": "AI agent for algebra",
    "subject": "Mathematics",
    "is_active": true,
    "created_by_id": 1,
    "created_at": "2026-05-25T10:10:00"
  }
]
```

---

### GET /api/v1/admin/agents/{agent_id}/chunks
Retrieve all text chunks for a given agent (for LLM context).

**Headers:**
```
Authorization: Bearer <teacher_token>
```

**Response 200 OK:**
```json
[
  {
    "id": 1,
    "agent_id": 1,
    "chunk_index": 0,
    "content": "Algebra is a branch of mathematics...",
    "created_at": "2026-05-25T10:10:00"
  },
  {
    "id": 2,
    "agent_id": 1,
    "chunk_index": 1,
    "content": "Linear equations are...",
    "created_at": "2026-05-25T10:10:00"
  }
]
```

**Response 404:**
```json
{"detail": "Agent not found or not managed by you"}
```

---

### PUT /api/v1/admin/agents/{agent_id}
Update an agent's metadata (not the file/chunks).

**Headers:**
```
Authorization: Bearer <teacher_token>
Content-Type: application/json
```

**Request Body (all fields optional):**
```json
{
  "name": "Advanced Math Tutor",
  "subject": "Advanced Mathematics",
  "description": "Updated description",
  "is_active": false
}
```

**Response 200 OK:**
```json
{
  "id": 1,
  "name": "Advanced Math Tutor",
  "description": "Updated description",
  "subject": "Advanced Mathematics",
  "is_active": false,
  "created_by_id": 1,
  "created_at": "2026-05-25T10:10:00"
}
```

---

### DELETE /api/v1/admin/agents/{agent_id}
Delete an agent and all its stored chunks.

**Headers:**
```
Authorization: Bearer <teacher_token>
```

**Response 204 No Content** (empty body)

---

## 4. Dashboards

### GET /api/v1/dashboard/teacher
Teacher-only dashboard.

**Headers:**
```
Authorization: Bearer <teacher_token>
```

**Response 200 OK:**
```json
{
  "message": "Welcome to the Teacher (Admin) Dashboard!",
  "actions_available": [
    "Create student accounts",
    "View student list",
    "Update student details",
    "Reset student passwords",
    "Deactivate/delete student accounts"
  ]
}
```

**Response 403 (student access):**
```json
{"detail": "You do not have permission to access this resource"}
```

---

### GET /api/v1/dashboard/student
Student-only dashboard.

**Headers:**
```
Authorization: Bearer <student_token>
```

**Response 200 OK:**
```json
{
  "message": "Welcome to the Student Dashboard!",
  "actions_available": [
    "View curriculum",
    "Submit assignments",
    "Check grading feedback"
  ]
}
```

---

### GET /api/v1/dashboard/shared
Shared dashboard accessible by both teachers and students.

**Response 200 OK:**
```json
{
  "message": "Welcome to the Shared Workspace!",
  "info": "This content is visible to both Teachers and Students."
}
```

---

## Error Codes Summary

| Status | Meaning | Common Causes |
|--------|---------|---------------|
| 200 | OK | Successful GET/PUT |
| 201 | Created | Successful POST |
| 204 | No Content | Successful DELETE |
| 400 | Bad Request | Duplicate username/agent name, validation error |
| 401 | Unauthorized | Missing/invalid token, wrong login credentials |
| 403 | Forbidden | Student accessing teacher endpoint, deactivated account |
| 404 | Not Found | Resource doesn't exist or doesn't belong to you |
| 413 | Payload Too Large | File too large (max 50MB) |
| 422 | Validation Error | Field too short, wrong type, missing required field |
| 500 | Server Error | File processing failed |

---

## Frontend Implementation Flow

### Teacher Flow:
1. **Register:** `POST /api/v1/auth/teacher/register` (no token)
2. **Login:** `POST /api/v1/auth/login` → store `access_token` in localStorage
3. **Create Students:** `POST /api/v1/admin/students` with `Authorization: Bearer <token>`
4. **Create Agents:** `POST /api/v1/admin/agents` as `multipart/form-data`
5. **List/Update/Delete:** Use `GET /api/v1/admin/students`, `PUT /api/v1/admin/students/{id}`, `DELETE /api/v1/admin/students/{id}`

### Student Flow:
1. Teacher creates student account (`POST /api/v1/admin/students`)
2. **Login:** `POST /api/v1/auth/login` with student credentials → store token
3. **View Profile:** `GET /api/v1/users/me`
4. **Dashboard:** `GET /api/v1/dashboard/student`

### Token Refresh:
Tokens expire after 30 minutes. On 401, redirect to login page.

### Role-Based UI:
- Decode the JWT payload (base64) to read the `role` field
- Show/hide admin menus based on `role === "teacher"`
