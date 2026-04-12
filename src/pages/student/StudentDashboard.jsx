import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import Sidebar from '../../components/Sidebar';
import SortableTable from '../../components/SortableTable';
import { ToastProvider, useToast } from '../../components/Toast';
import * as api from '../../api';
import { FiPlay, FiClock, FiBookOpen, FiList, FiRefreshCw } from 'react-icons/fi';

/* ── localStorage helpers for detecting active session ── */
const SAVE_KEY_PREFIX = 'tes_active_session_';
function getActiveSession(username) {
  try { const raw = localStorage.getItem(SAVE_KEY_PREFIX + username); return raw ? JSON.parse(raw) : null; } catch { return null; }
}

function StudentContent() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const toast = useToast();
  const [tab, setTab] = useState('tests');
  const [assignedTests, setAssignedTests] = useState({});
  const [eligibility, setEligibility] = useState({});
  const [selectedTeacher, setSelectedTeacher] = useState('');
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(true);
  const [activeSession, setActiveSession] = useState(null);

  const loadData = useCallback(async () => {
    setLoading(true);
    // Check for active session in localStorage
    const saved = getActiveSession(user.username);
    if (saved && saved.test_id) setActiveSession(saved);
    else setActiveSession(null);

    const res = await api.getAssignedTests(user.username);
    if (res.ok) {
      setAssignedTests(res.data || {});
      const elig = {};
      for (const [, tests] of Object.entries(res.data || {})) {
        for (const t of tests) {
          if (t.test_id) {
            const er = await api.checkEligibility(user.username, t.test_id);
            if (er.ok) elig[t.test_id] = er.data;
          }
        }
      }
      setEligibility(elig);
      const teachers = Object.keys(res.data || {});
      if (teachers.length > 0 && !selectedTeacher) setSelectedTeacher(teachers[0]);
    }
    setLoading(false);
  }, [user.username]);

  const loadHistory = useCallback(async () => {
    const res = await api.getUserHistory(user.username);
    if (res.ok) setHistory(res.data || []);
  }, [user.username]);

  useEffect(() => { loadData(); }, [loadData]);
  useEffect(() => { if (tab === 'history') loadHistory(); }, [tab, loadHistory]);

  const teachers = Object.keys(assignedTests);
  const currentTests = assignedTests[selectedTeacher] || [];

  const handleStartTest = (testId) => {
    const e = eligibility[testId];
    if (e && !e.eligible) {
      toast(e.message || 'Тест недоступен', 'error');
      return;
    }
    navigate(`/student/test/${testId}`);
  };

  const historyColumns = [
    { key: 'start_time', label: 'Дата начала' },
    { key: 'test_name', label: 'Название теста' },
    { key: 'attempt_number', label: 'Попытка' },
    { key: 'duration', label: 'Длительность' },
    { key: 'final_status', label: 'Результат', render: (v) => (
      <span className={`badge ${v === 'Зачёт' || v === 'зачтено' || v === 'Passed' ? 'badge-green' : 'badge-red'}`}>{v || '—'}</span>
    )},
  ];

  const sidebarLinks = [
    { label: 'Меню', items: [
      { id: 'tests', text: 'Назначенные тесты', icon: <FiList size={18} />, onClick: () => setTab('tests'), path: '/student' },
      { id: 'history', text: 'Моя история', icon: <FiBookOpen size={18} />, onClick: () => setTab('history') },
    ]}
  ];

  return (
    <div className="page-layout">
      <Sidebar links={sidebarLinks} />
      <main className="main-content">
        {tab === 'tests' && (
          <>
            <h1 className="page-title">Назначенные тесты</h1>
            {activeSession && (
              <div className="card mb-4" style={{ border: '1px solid var(--color-green)', background: 'rgba(16,185,129,.06)' }}>
                <div className="flex items-center" style={{ justifyContent: 'space-between' }}>
                  <div>
                    <div style={{ fontWeight: 600, color: 'var(--color-green)' }}>Активный тест</div>
                    <div className="text-sm text-secondary">У вас есть незавершённый тест. Вопрос {(activeSession.frontier_idx || 0) + 1} из {activeSession.total_questions || '?'}</div>
                  </div>
                  <button className="btn btn-primary btn-sm" onClick={() => navigate(`/student/test/${activeSession.test_id}`)}>
                    <FiRefreshCw size={14} /> Продолжить
                  </button>
                </div>
              </div>
            )}
            {loading ? <p className="text-secondary">Загрузка...</p> : teachers.length === 0 ? (
              <div className="empty-state">
                <div className="empty-state-icon">📚</div>
                <div className="empty-state-text">Нет назначенных тестов</div>
              </div>
            ) : (
              <>
                <div className="form-group mb-4">
                  <label className="form-label">Преподаватель</label>
                  <select className="select" value={selectedTeacher} onChange={(e) => setSelectedTeacher(e.target.value)}>
                    {teachers.map((t) => <option key={t} value={t}>{t}</option>)}
                  </select>
                </div>
                <div className="flex flex-col gap-sm">
                  {currentTests.map((test) => {
                    const e = eligibility[test.test_id];
                    const eligible = !e || e.eligible;
                    const hasActiveSession = activeSession && activeSession.test_id === test.test_id;
                    return (
                      <div key={test.test_id} className="test-item" onClick={() => handleStartTest(test.test_id)} style={hasActiveSession ? { borderLeft: '3px solid var(--color-green)' } : {}}>
                        <div>
                          <div style={{ fontWeight: 600, fontSize: '.95rem' }}>
                            {hasActiveSession && <span style={{ color: 'var(--color-green)', marginRight: 6 }}>●</span>}
                            {test.test_name || 'Безымянный тест'}
                          </div>
                          <div className="text-sm text-secondary" style={{ marginTop: 4 }}>
                            {test.questions?.length || 0} вопросов
                            {test.time_limit_minutes ? ` • ${test.time_limit_minutes} мин` : ''}
                          </div>
                        </div>
                        <div>
                          {eligible ? (
                            <button className="btn btn-primary btn-sm" onClick={(ev) => { ev.stopPropagation(); handleStartTest(test.test_id); }}>
                              <FiPlay size={14} /> Начать
                            </button>
                          ) : (
                            <span className="badge badge-yellow"><FiClock size={12} style={{ marginRight: 4 }} /> {e?.message || 'Недоступен'}</span>
                          )}
                        </div>
                      </div>
                    );
                  })}
                </div>
              </>
            )}
          </>
        )}

        {tab === 'history' && (
          <>
            <h1 className="page-title">Моя история тестов</h1>
            <div className="card">
              <SortableTable columns={historyColumns} data={history} emptyText="Вы ещё не прошли ни одного теста" />
            </div>
          </>
        )}
      </main>
    </div>
  );
}

export default function StudentDashboard() {
  return <ToastProvider><StudentContent /></ToastProvider>;
}
