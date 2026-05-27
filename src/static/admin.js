const API_BASE = '/api/v1';
let token = localStorage.getItem('token') || null;

function show(id) { document.getElementById(id).classList.remove('hidden'); }
function hide(id) { document.getElementById(id).classList.add('hidden'); }
function status(id, msg, type='info') {
    const el = document.getElementById(id);
    el.innerHTML = `<span class="status ${type}">${msg}</span>`;
}

function showLogin() {
    hide('registerSection');
    show('authSection');
}
function showRegister() {
    hide('authSection');
    show('registerSection');
}

function showTab(tab) {
    ['homeTab','teachersTab','studentsTab','agentsTab','profileTab'].forEach(t => hide(t));
    show(tab + 'Tab');
    if (tab === 'home') loadDashboard();
    if (tab === 'teachers') listTeachers();
    if (tab === 'students') { listStudents(); loadStudentAgentAssign(); }
    if (tab === 'agents') { listAgents(); loadAgentSelect(); clearChunks(); document.getElementById('searchResults').innerHTML = ''; }
    if (tab === 'profile') loadProfile();
}

async function loadDashboard() {
    const [tch, stu, agt] = await Promise.all([
        api('GET', '/auth/teachers'),
        api('GET', '/admin/students'),
        api('GET', '/admin/agents')
    ]);

    // Build teacher lookup map: id -> full_name
    const teacherMap = {};
    if (tch.ok && tch.data) {
        tch.data.forEach(t => teacherMap[t.id] = t.full_name || t.username);
    }

    // Update counts (global)
    const tchCount = (tch.ok && tch.data) ? tch.data.length : 0;
    const stuCount = (stu.ok && stu.data) ? stu.data.length : 0;
    const agtCount = (agt.ok && agt.data) ? agt.data.length : 0;
    document.getElementById('dashTeacherCount').textContent = tchCount;
    document.getElementById('dashStudentCount').textContent = stuCount;
    document.getElementById('dashAgentCount').textContent = agtCount;

    // Preview teachers (last 5)
    const tchBox = document.getElementById('dashTeachers');
    if (tch.ok && tch.data && tch.data.length) {
        tchBox.innerHTML = '<table><thead><tr><th>ID</th><th>Name</th><th>Username</th><th>Active</th></tr></thead><tbody>' +
            tch.data.slice(0, 5).map(t => `<tr><td>${t.id}</td><td>${t.full_name}</td><td>${t.username}</td><td>${t.is_active ? 'Yes' : 'No'}</td></tr>`).join('') +
            '</tbody></table>';
    } else {
        tchBox.innerHTML = '<p>No teachers found.</p>';
    }

    // Preview students (last 5) with teacher name
    const stuBox = document.getElementById('dashStudents');
    if (stu.ok && stu.data && stu.data.length) {
        stuBox.innerHTML = '<table><thead><tr><th>ID</th><th>Name</th><th>Class</th><th>Phone</th><th>Teacher</th></tr></thead><tbody>' +
            stu.data.slice(0, 5).map(s => `<tr><td>${s.id}</td><td>${s.full_name}</td><td>${s.class_name || '-'}</td><td>${s.phone_number || '-'}</td><td>${teacherMap[s.teacher_id] || '-'}</td></tr>`).join('') +
            '</tbody></table>';
    } else {
        stuBox.innerHTML = '<p>No students found. <button onclick="showTab(\'students\')">Create one</button></p>';
    }

    // Preview agents (last 5) with creator name
    const agtBox = document.getElementById('dashAgents');
    if (agt.ok && agt.data && agt.data.length) {
        agtBox.innerHTML = '<table><thead><tr><th>ID</th><th>Name</th><th>Subject><th>Class</th><th>Teacher</th><th>Chunks</th></tr></thead><tbody>' +
            agt.data.slice(0, 5).map(a => `<tr><td>${a.id}</td><td>${a.name}</td><td>${a.subject}</td><td>${a.class_name || 'General'}</td><td>${teacherMap[a.created_by_id] || '-'}</td><td><button onclick="viewChunks(${a.id})">View</button></td></tr>`).join('') +
            '</tbody></table>';
    } else {
        agtBox.innerHTML = '<p>No agents found. <button onclick="showTab(\'agents\')">Create one</button></p>';
    }
}

async function api(method, path, body=null, isForm=false) {
    const opts = { method, headers: {} };
    if (token) opts.headers['Authorization'] = 'Bearer ' + token;
    if (body && !isForm) {
        opts.headers['Content-Type'] = 'application/json';
        opts.body = JSON.stringify(body);
    }
    if (body && isForm) opts.body = body;
    const res = await fetch(API_BASE + path, opts);
    const data = res.status === 204 ? null : await res.json().catch(() => ({}));
    return { ok: res.ok, status: res.status, data };
}

async function login() {
    const u = document.getElementById('loginUsername').value;
    const p = document.getElementById('loginPassword').value;
    if (!u || !p) return status('loginStatus', 'Enter username and password', 'error');
    const r = await api('POST', '/auth/login', { username: u, password: p });
    if (r.ok && r.data.access_token) {
        token = r.data.access_token;
        localStorage.setItem('token', token);
        hide('authSection');
        hide('registerSection');
        show('dashboard');
        showTab('home');
        loadProfile();
    } else {
        status('loginStatus', r.data.detail || 'Login failed', 'error');
    }
}

async function register() {
    const u = document.getElementById('regUsername').value;
    const p = document.getElementById('regPassword').value;
    const n = document.getElementById('regFullName').value;
    if (!u || !p || !n) return status('registerStatus', 'Fill all fields', 'error');
    const r = await api('POST', '/auth/teacher/register', { username: u, password: p, full_name: n });
    if (r.ok) {
        status('registerStatus', 'Teacher registered! Please login.', 'success');
        setTimeout(showLogin, 1500);
    } else {
        status('registerStatus', r.data.detail || 'Registration failed', 'error');
    }
}

async function loadProfile() {
    const r = await api('GET', '/users/me');
    if (r.ok) {
        const u = r.data;
        document.getElementById('userInfo').textContent = `${u.full_name} (${u.role}) | ID: ${u.id}`;
        document.getElementById('profileContent').innerHTML = `
            <p><strong>Username:</strong> ${u.username}</p>
            <p><strong>Full Name:</strong> ${u.full_name}</p>
            <p><strong>Role:</strong> ${u.role}</p>
            <p><strong>ID:</strong> ${u.id}</p>
            <p><strong>Active:</strong> ${u.is_active}</p>
        `;
    }
}

async function loadStudentAgentAssign() {
    const r = await api('GET', '/admin/agents');
    const box = document.getElementById('stuAgentAssign');
    if (!r.ok || !r.data || !r.data.length) {
        box.innerHTML = '<p style="font-size:0.85rem;color:#636e72">No agents available. Create an agent first.</p>';
        return;
    }
    const selectedClass = document.getElementById('stuClass').value;
    const filtered = selectedClass
        ? r.data.filter(a => (a.class_name === selectedClass) || !a.class_name)
        : r.data.filter(a => !a.class_name);
    if (!filtered.length) {
        box.innerHTML = `<p style="font-size:0.85rem;color:#636e72">No agents for class ${selectedClass}. Create one first or select General agents.</p>`;
        return;
    }
    box.innerHTML = filtered.map(a => `
        <label style="display:flex;align-items:center;gap:6px;font-weight:400;font-size:0.9rem;margin-bottom:4px;cursor:pointer">
            <input type="checkbox" value="${a.id}" class="stuAgentCheckbox">
            ${a.name} (${a.subject}) — ${a.class_name || 'General'}
        </label>
    `).join('');
}

async function createStudent() {
    const assigned = Array.from(document.querySelectorAll('.stuAgentCheckbox:checked')).map(cb => parseInt(cb.value));
    const cls = document.getElementById('stuClass').value;
    const payload = {
        username: document.getElementById('stuUsername').value,
        password: document.getElementById('stuPassword').value,
        student_name: document.getElementById('stuName').value,
        age: parseInt(document.getElementById('stuAge').value) || 0,
        class_name: cls || 'General',
        phone_number: document.getElementById('stuPhone').value,
        assigned_agent_ids: assigned.length ? assigned : undefined,
    };
    if (!payload.username || !payload.password || !payload.student_name) {
        return status('stuCreateStatus', 'Username, password, and name required', 'error');
    }
    const r = await api('POST', '/admin/students', payload);
    if (r.ok) {
        status('stuCreateStatus', `Student created: ${r.data.full_name} (ID: ${r.data.id})`, 'success');
        listStudents();
        ['stuUsername','stuPassword','stuName','stuAge','stuClass','stuPhone'].forEach(id => document.getElementById(id).value = '');
        document.querySelectorAll('.stuAgentCheckbox:checked').forEach(cb => cb.checked = false);
    } else {
        status('stuCreateStatus', r.data.detail || 'Failed to create student', 'error');
    }
}

async function listTeachers() {
    const r = await api('GET', '/auth/teachers');
    const tbody = document.getElementById('teachersTable');
    if (!r.ok) { tbody.innerHTML = '<tr><td colspan="5">Failed to load</td></tr>'; return; }
    tbody.innerHTML = (r.data || []).map(t => `
        <tr>
            <td>${t.id}</td>
            <td>${t.full_name}</td>
            <td>${t.username}</td>
            <td>${t.is_active ? 'Yes' : 'No'}</td>
            <td>${new Date(t.created_at).toLocaleDateString()}</td>
        </tr>
    `).join('') || '<tr><td colspan="5">No teachers found</td></tr>';
}

async function listStudents() {
    const [r, tch, agt] = await Promise.all([
        api('GET', '/admin/students'),
        api('GET', '/auth/teachers'),
        api('GET', '/admin/agents')
    ]);
    const teacherMap = {};
    if (tch.ok && tch.data) tch.data.forEach(t => teacherMap[t.id] = t.full_name || t.username);
    const agentMap = {};
    if (agt.ok && agt.data) agt.data.forEach(a => agentMap[a.id] = a.name);

    const tbody = document.getElementById('studentsTable');
    if (!r.ok) { tbody.innerHTML = '<tr><td colspan="10">Failed to load</td></tr>'; return; }
    tbody.innerHTML = (r.data || []).map(s => {
        const agentLabels = (s.assigned_agent_ids || []).map(id => agentMap[id] || `ID ${id}`).join(', ');
        return `
        <tr>
            <td>${s.id}</td>
            <td>${s.full_name}</td>
            <td>${s.username}</td>
            <td>${s.age || '-'}</td>
            <td>${s.class_name || '-'}</td>
            <td>${s.phone_number || '-'}</td>
            <td>${agentLabels || '-'}</td>
            <td>${s.is_active ? 'Yes' : 'No'}</td>
            <td>${teacherMap[s.teacher_id] || '-'}</td>
            <td>
                <button class="danger" onclick="deleteStudent(${s.id})">Delete</button>
            </td>
        </tr>`;
    }).join('') || '<tr><td colspan="10">No students found</td></tr>';
}

async function deleteStudent(id) {
    if (!confirm('Delete student ' + id + '?')) return;
    const r = await api('DELETE', '/admin/students/' + id);
    if (r.ok) { listStudents(); }
    else { alert(r.data.detail || 'Delete failed'); }
}

async function createAgent() {
    const form = new FormData();
    form.append('name', document.getElementById('agentName').value);
    form.append('subject', document.getElementById('agentSubject').value);
    const cls = document.getElementById('agentClass').value;
    if (cls) form.append('class_name', cls);
    const desc = document.getElementById('agentDesc').value;
    if (desc) form.append('description', desc);
    const file = document.getElementById('agentFile').files[0];
    if (!file) return status('agentCreateStatus', 'Please select a file', 'error');
    if (!form.get('name') || !form.get('subject')) return status('agentCreateStatus', 'Name and subject required', 'error');
    form.append('file', file);
    const r = await api('POST', '/admin/agents', form, true);
    if (r.ok) {
        status('agentCreateStatus', `Agent created: ${r.data.name} (Class: ${r.data.class_name || 'General'}, ID: ${r.data.id})`, 'success');
        listAgents(); loadAgentSelect();
        ['agentName','agentSubject','agentDesc','agentFile','agentClass'].forEach(id => document.getElementById(id).value = '');
    } else {
        status('agentCreateStatus', r.data.detail || 'Failed to create agent', 'error');
    }
}

async function listAgents() {
    const [r, tch] = await Promise.all([
        api('GET', '/admin/agents'),
        api('GET', '/auth/teachers')
    ]);
    const teacherMap = {};
    if (tch.ok && tch.data) tch.data.forEach(t => teacherMap[t.id] = t.full_name || t.username);

    const tbody = document.getElementById('agentsTable');
    if (!r.ok) { tbody.innerHTML = '<tr><td colspan="8">Failed to load</td></tr>'; return; }
    tbody.innerHTML = (r.data || []).map(a => `
        <tr>
            <td>${a.id}</td>
            <td>${a.name}</td>
            <td>${a.subject}</td>
            <td>${a.class_name || 'General'}</td>
            <td>${a.is_active ? 'Yes' : 'No'}</td>
            <td>${new Date(a.created_at).toLocaleDateString()}</td>
            <td>${teacherMap[a.created_by_id] || '-'}</td>
            <td>
                <button onclick="viewChunks(${a.id})">Chunks</button>
                <button class="danger" onclick="deleteAgent(${a.id})">Delete</button>
            </td>
        </tr>
    `).join('') || '<tr><td colspan="8">No agents found</td></tr>';
}

async function loadAgentSelect() {
    const r = await api('GET', '/admin/agents');
    const sel = document.getElementById('searchAgentId');
    sel.innerHTML = '<option value="">Select Agent</option>';
    if (r.ok && r.data) {
        r.data.forEach(a => {
            const opt = document.createElement('option');
            opt.value = a.id;
            opt.textContent = `${a.name} (${a.class_name || 'General'}) (ID: ${a.id})`;
            sel.appendChild(opt);
        });
    }
}

async function viewChunks(agentId) {
    const r = await api('GET', '/admin/agents/' + agentId + '/chunks');
    const box = document.getElementById('chunkResults');
    let html = `<h4>Chunks for Agent ${agentId} (${r.data ? r.data.length : 0} total)</h4>`;
    if (r.ok && r.data && r.data.length) {
        html += r.data.map((c,i) => `<div class="chunk-item"><strong>#${i+1}</strong> [${c.chunk_index}] ${c.content.substring(0,200)}...</div>`).join('');
    } else {
        html += '<p>No chunks found</p>';
    }
    box.innerHTML = html;
    box.scrollTop = 0;
}

function clearChunks() {
    document.getElementById('chunkResults').innerHTML = '<p>Select an agent and click "Chunks" to view all chunks here.</p>';
}

async function searchChunks() {
    const agentId = document.getElementById('searchAgentId').value;
    const query = document.getElementById('searchQuery').value;
    const topK = document.getElementById('searchTopK').value;
    if (!agentId || !query) return alert('Select agent and enter query');
    const r = await api('GET', `/admin/agents/${agentId}/search?query=${encodeURIComponent(query)}&top_k=${topK}`);
    const box = document.getElementById('searchResults');
    if (r.ok && r.data && r.data.length) {
        box.innerHTML = r.data.map(c => `
            <div class="chunk-item">
                <span class="score">Score: ${c.score}</span> |
                <strong>Chunk ${c.chunk_index}</strong><br>
                ${c.content.substring(0,300)}...
            </div>
        `).join('');
    } else {
        box.innerHTML = '<p>No matching chunks</p>';
    }
}

async function deleteAgent(id) {
    if (!confirm('Delete agent ' + id + '?')) return;
    const r = await api('DELETE', '/admin/agents/' + id);
    if (r.ok) { listAgents(); loadAgentSelect(); }
    else { alert(r.data.detail || 'Delete failed'); }
}

function logout() {
    token = null;
    localStorage.removeItem('token');
    hide('dashboard');
    hide('studentsTab'); hide('agentsTab'); hide('profileTab');
    show('authSection');
    document.getElementById('loginUsername').value = '';
    document.getElementById('loginPassword').value = '';
}

// Validate token before showing dashboard
async function tryAutoLogin() {
    if (!token) return;
    const r = await api('GET', '/users/me');
    if (r.ok) {
        hide('authSection');
        hide('registerSection');
        show('dashboard');
        showTab('home');
        loadProfile();
    } else {
        token = null;
        localStorage.removeItem('token');
        show('authSection');
    }
}

// Re-filter assignable agents when class dropdown changes
document.addEventListener('DOMContentLoaded', () => {
    const cls = document.getElementById('stuClass');
    if (cls) cls.addEventListener('change', loadStudentAgentAssign);
    tryAutoLogin();
});
