const API_BASE = import.meta.env.PROD
  ? 'https://expert-system-431h.onrender.com'
  : '';

const AUTH = `${API_BASE}/auth`;
const CONTENT = `${API_BASE}/content`;
const TESTS = `${API_BASE}/tests`;
const SESSIONS = `${API_BASE}/sessions`;

function authHeaders() {
  const token = localStorage.getItem('token');
  return token ? { Authorization: `Bearer ${token}` } : {};
}

const WAKE_URL = 'https://expert-system-431h.onrender.com/';
const WAKE_POLL_INTERVAL = 3000;
const WAKE_DELAY = 5000;

let _wakeUpVisible = false;

function _showWakeUp() {
  if (!_wakeUpVisible) {
    _wakeUpVisible = true;
    window.dispatchEvent(new Event('server-waking-up'));
  }
}

function _hideWakeUp() {
  if (_wakeUpVisible) {
    _wakeUpVisible = false;
    window.dispatchEvent(new Event('server-ready'));
  }
}

function _needsWakeUp(res) {
  return !res || res.status === 520 || res.status === 502 || res.status === 503;
}

async function _waitForServer() {
  _showWakeUp();
  while (true) {
    try {
      const ping = await fetch(WAKE_URL, { method: 'GET' });
      if (ping.ok) {
        _hideWakeUp();
        return;
      }
    } catch { /* server still sleeping */ }
    await new Promise((r) => setTimeout(r, WAKE_POLL_INTERVAL));
  }
}

async function request(method, url, body = null) {
  const opts = {
    method,
    headers: { 'Content-Type': 'application/json', ...authHeaders() },
  };
  if (body !== null) opts.body = JSON.stringify(body);

  const wakeTimer = setTimeout(_showWakeUp, WAKE_DELAY);

  let res;
  try {
    res = await fetch(url, opts);
  } catch {
    res = null;
  }

  if (_needsWakeUp(res)) {
    clearTimeout(wakeTimer);
    await _waitForServer();
    // retry the original request after server woke up
    try {
      res = await fetch(url, opts);
    } catch {
      _hideWakeUp();
      return { ok: false, status: 0, data: { detail: 'Нет соединения с сервером' } };
    }
  }

  clearTimeout(wakeTimer);
  _hideWakeUp();

  if (res.status === 401) {
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    window.dispatchEvent(new Event('auth-expired'));
  }
  const text = await res.text();
  let data = null;
  try {
    data = JSON.parse(text);
  } catch {
    data = { detail: text || `HTTP ${res.status}` };
  }
  return { ok: res.ok, status: res.status, data };
}

/* ── Auth ── */
export async function login(username, password) {
  return request('POST', `${AUTH}/login`, { username, password });
}
export async function register(username, password, group, fullName) {
  const body = { username, password };
  if (group) body.group = group;
  if (fullName) body.full_name = fullName;
  return request('POST', `${AUTH}/register`, body);
}
export async function getAllUsers() {
  return request('GET', `${AUTH}/users`);
}
export async function getUsersByRole(role) {
  return request('GET', `${AUTH}/users/by-role/${role}`);
}
export async function getUsersByGroup(group) {
  return request('GET', `${AUTH}/users/by-group/${encodeURIComponent(group)}`);
}
export async function getStudents() {
  return request('GET', `${AUTH}/students`);
}
export async function getAllGroups() {
  return request('GET', `${AUTH}/groups`);
}
export async function changeUserRole(username, role) {
  return request('PUT', `${AUTH}/users/${encodeURIComponent(username)}/role`, { role });
}
export async function changeUserGroup(username, group) {
  return request('PUT', `${AUTH}/users/${encodeURIComponent(username)}/group`, { group: group || '' });
}
export async function deleteUser(username) {
  return request('DELETE', `${AUTH}/users/${encodeURIComponent(username)}`);
}
export async function changePassword(username, oldPassword, newPassword) {
  return request('PUT', `${AUTH}/users/${encodeURIComponent(username)}/password`, { old_password: oldPassword, new_password: newPassword });
}
export async function resetPassword(username, newPassword) {
  return request('PUT', `${AUTH}/users/${encodeURIComponent(username)}/reset-password`, { new_password: newPassword });
}
export async function updateUserFullName(username, fullName) {
  return request('PUT', `${AUTH}/users/${encodeURIComponent(username)}/full-name`, { full_name: fullName });
}
export async function createGroup(name) {
  return request('POST', `${AUTH}/groups`, { name });
}
export async function deleteGroup(name) {
  return request('DELETE', `${AUTH}/groups/${encodeURIComponent(name)}`);
}
export async function renameGroup(oldName, newName) {
  return request('PUT', `${AUTH}/groups/${encodeURIComponent(oldName)}`, { name: newName });
}

/* ── Content (Questions & Criteria) ── */
export async function getQuestions() {
  return request('GET', `${CONTENT}/questions`);
}
export async function getCategories() {
  return request('GET', `${CONTENT}/categories`);
}
export async function addQuestion(topic, questionData) {
  return request('POST', `${CONTENT}/questions/${encodeURIComponent(topic)}`, questionData);
}
export async function updateQuestion(topic, index, questionData) {
  return request('PUT', `${CONTENT}/questions/${encodeURIComponent(topic)}/${index}`, questionData);
}
export async function deleteQuestion(topic, index) {
  return request('DELETE', `${CONTENT}/questions/${encodeURIComponent(topic)}/${index}`);
}
export async function getCriteria(creatorUsername) {
  const qs = creatorUsername ? `?creator_username=${encodeURIComponent(creatorUsername)}` : '';
  return request('GET', `${CONTENT}/criteria${qs}`);
}
export async function getCriteriaForEditing(username, role) {
  return request('GET', `${CONTENT}/criteria/for-editing?username=${encodeURIComponent(username)}&role=${encodeURIComponent(role)}`);
}
export async function saveCriteria(username, role, criteriaObject) {
  return request('PUT', `${CONTENT}/criteria?username=${encodeURIComponent(username)}&role=${encodeURIComponent(role)}`, criteriaObject);
}
export async function getDefaultCriteria() {
  return request('GET', `${CONTENT}/criteria/defaults`);
}
export async function getTestCriteria(testId) {
  return request('GET', `${CONTENT}/criteria/test/${testId}`);
}
export async function saveTestCriteria(testId, criteriaObject) {
  return request('PUT', `${CONTENT}/criteria/test/${testId}`, criteriaObject);
}

/* ── Tests ── */
export async function getAllTests() {
  return request('GET', TESTS);
}
export async function getTestsForCreator(username) {
  return request('GET', `${TESTS}/creator/${encodeURIComponent(username)}`);
}
export async function getTestById(testId) {
  return request('GET', `${TESTS}/${testId}`);
}
export async function getAssignedTests(studentUsername) {
  return request('GET', `${TESTS}/assigned/${encodeURIComponent(studentUsername)}`);
}
export async function createTest(testName, questions, timeLimitMinutes, cooldownHours, maxAttempts, gradingMode = 'overall') {
  const body = { test_name: testName, questions, grading_mode: gradingMode };
  if (timeLimitMinutes) body.time_limit_minutes = timeLimitMinutes;
  if (cooldownHours != null) body.cooldown_hours = cooldownHours;
  if (maxAttempts) body.max_attempts = maxAttempts;
  return request('POST', TESTS, body);
}
export async function deleteTest(testId) {
  return request('DELETE', `${TESTS}/${testId}`);
}
export async function renameTest(testId, testName) {
  return request('PUT', `${TESTS}/${testId}/name`, { test_name: testName });
}
export async function updateTestSettings(testId, settings) {
  return request('PUT', `${TESTS}/${testId}/settings`, settings);
}
export async function cloneTest(testId) {
  return request('POST', `${TESTS}/${testId}/clone`);
}
export async function deleteQuestionFromTest(testId, index) {
  return request('DELETE', `${TESTS}/${testId}/questions/${index}`);
}
export async function addQuestionsToTest(testId, questions) {
  return request('POST', `${TESTS}/${testId}/questions`, { questions });
}
export async function batchUpdateAssignments(testId, assignList, unassignList) {
  return request('PUT', `${TESTS}/${testId}/assignments`, { assign: assignList, unassign: unassignList });
}
export async function generateTestByTopicScore(topic, maxScore) {
  return request('POST', `${TESTS}/generate`, { topic, max_score: maxScore });
}
export async function shareTest(testId) {
  return request('POST', `${TESTS}/${testId}/share`);
}
export async function unshareTest(testId) {
  return request('DELETE', `${TESTS}/${testId}/share`);
}
export async function getSharedTestInfo(shareToken) {
  return request('GET', `${TESTS}/shared/${shareToken}`);
}
export async function joinTestByShare(shareToken) {
  return request('POST', `${TESTS}/shared/${shareToken}/join`);
}

/* ── Content (Questions & Criteria) — Bulk Import ── */
export async function bulkImportQuestions(questions) {
  return request('POST', `${CONTENT}/questions/import`, { questions });
}

/* ── Sessions ── */
export async function startSession(testId) {
  return request('POST', `${SESSIONS}/start`, { test_id: testId });
}
export async function submitAnswer(sessionId, answer) {
  return request('POST', `${SESSIONS}/${sessionId}/answer`, { answer });
}
export async function getSessionStatus(sessionId) {
  return request('GET', `${SESSIONS}/${sessionId}/status`);
}
export async function getActiveSession() {
  return request('GET', `${SESSIONS}/active`);
}
export async function checkEligibility(username, testId) {
  return request('GET', `${SESSIONS}/eligibility/${encodeURIComponent(username)}/${testId}`);
}
export async function getTestHistory() {
  return request('GET', `${SESSIONS}/history`);
}
export async function getUserHistory(username) {
  return request('GET', `${SESSIONS}/history/${encodeURIComponent(username)}`);
}
export async function clearHistory(username = null, testId = null) {
  const params = new URLSearchParams();
  if (username) params.append('username', username);
  if (testId) params.append('test_id', testId);
  const query = params.toString();
  return request('DELETE', `${SESSIONS}/history${query ? '?' + query : ''}`);
}
export async function getTestResults(testId) {
  return request('GET', `${SESSIONS}/results/test/${testId}`);
}
export async function getTestAggregateStats(testId) {
  return request('GET', `${SESSIONS}/results/test/${testId}/stats`);
}
export async function verifyToken() {
  return request('GET', `${AUTH}/verify`);
}
