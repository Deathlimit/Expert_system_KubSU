import React, { useState, useEffect, useCallback } from 'react';
import { useAuth } from '../../context/AuthContext';
import { useToast } from '../../components/Toast';
import SortableTable from '../../components/SortableTable';
import Modal from '../../components/Modal';
import AutocompleteInput from '../../components/AutocompleteInput';
import * as api from '../../api';
import { FiTrash2, FiPlus, FiUsers, FiBarChart2, FiDownload, FiSearch, FiSliders, FiCopy, FiEdit2 } from 'react-icons/fi';

export default function ManageTests() {
  const [tab, setTab] = useState('manage');
  return (
    <>
      <h1 className="page-title">Управление тестами</h1>
      <div className="tabs mb-4">
        <button className={`tab ${tab === 'manage' ? 'tab-active' : ''}`} onClick={() => setTab('manage')}>Тесты и назначения</button>
        <button className={`tab ${tab === 'history' ? 'tab-active' : ''}`} onClick={() => setTab('history')}>История</button>
      </div>
      {tab === 'manage' && <ManageTab />}
      {tab === 'history' && <HistoryTab />}
    </>
  );
}

/* ======================== MANAGE TAB ======================== */
function ManageTab() {
  const { user } = useAuth();
  const toast = useToast();
  const [tests, setTests] = useState([]);
  const [selectedTest, setSelectedTest] = useState(null);
  const [students, setStudents] = useState([]);
  const [groups, setGroups] = useState([]);
  const [groupFilter, setGroupFilter] = useState('');
  const [assignedSet, setAssignedSet] = useState(new Set());
  const [localAssigned, setLocalAssigned] = useState(new Set());
  const [loading, setLoading] = useState(true);
  const [showAddQ, setShowAddQ] = useState(false);
  const [showStats, setShowStats] = useState(false);
  const [showCriteria, setShowCriteria] = useState(false);

  const loadTests = useCallback(async () => {
    setLoading(true);
    const res = user.role === 'admin' ? await api.getAllTests() : await api.getTestsForCreator(user.username);
    if (res.ok) setTests(res.data || []);
    const sRes = await api.getStudents();
    if (sRes.ok) setStudents(sRes.data || []);
    const gRes = await api.getAllGroups();
    if (gRes.ok) setGroups(gRes.data || []);
    setLoading(false);
  }, [user]);

  useEffect(() => { loadTests(); }, [loadTests]);

  const selectTest = (test) => {
    // Warn about unsaved assignment changes
    if (selectedTest && localAssigned.size !== assignedSet.size ||
        selectedTest && [...localAssigned].some(u => !assignedSet.has(u))) {
      if (!window.confirm('Есть несохранённые изменения назначений. Переключить тест?')) return;
    }
    setSelectedTest(test);
    const assigned = new Set(test.assigned_students || []);
    setAssignedSet(assigned);
    setLocalAssigned(new Set(assigned));
  };

  const filteredStudents = groupFilter
    ? students.filter(s => s.group === groupFilter)
    : students;

  const toggleStudent = (username) => {
    setLocalAssigned(prev => {
      const s = new Set(prev);
      s.has(username) ? s.delete(username) : s.add(username);
      return s;
    });
  };

  const toggleGroup = () => {
    const groupStudents = filteredStudents.map(s => s.username);
    const allAssigned = groupStudents.every(s => localAssigned.has(s));
    setLocalAssigned(prev => {
      const s = new Set(prev);
      groupStudents.forEach(u => allAssigned ? s.delete(u) : s.add(u));
      return s;
    });
  };

  const saveAssignments = async () => {
    if (!selectedTest) return;
    const assign = [...localAssigned].filter(u => !assignedSet.has(u));
    const unassign = [...assignedSet].filter(u => !localAssigned.has(u));
    if (assign.length === 0 && unassign.length === 0) { toast('Нет изменений', 'info'); return; }
    const res = await api.batchUpdateAssignments(selectedTest.test_id, assign, unassign);
    if (res.ok) {
      toast('Назначения сохранены', 'success');
      loadTests();
    } else {
      toast(res.data?.detail || 'Ошибка', 'error');
    }
  };

  const handleDeleteTest = async () => {
    if (!selectedTest) return;
    if (!window.confirm(`Удалить тест "${selectedTest.test_name}"?`)) return;
    const res = await api.deleteTest(selectedTest.test_id);
    if (res.ok) {
      toast('Тест удалён', 'success');
      setSelectedTest(null);
      loadTests();
    } else {
      toast(res.data?.detail || 'Ошибка', 'error');
    }
  };

  const handleCloneTest = async () => {
    if (!selectedTest) return;
    const res = await api.cloneTest(selectedTest.test_id);
    if (res.ok) {
      toast(`Тест клонирован: ${res.data?.test?.test_name || 'копия'}`, 'success');
      loadTests();
    } else {
      toast(res.data?.detail || 'Ошибка', 'error');
    }
  };

  const handleRenameTest = async () => {
    if (!selectedTest) return;
    const newName = window.prompt('Новое название теста:', selectedTest.test_name);
    if (!newName || newName.trim() === '' || newName.trim() === selectedTest.test_name) return;
    const res = await api.renameTest(selectedTest.test_id, newName.trim());
    if (res.ok) {
      toast('Тест переименован', 'success');
      setSelectedTest(null);
      loadTests();
    } else {
      toast(res.data?.detail || 'Ошибка', 'error');
    }
  };

  const handleDeleteQuestion = async (index) => {
    if (!selectedTest) return;
    if (!window.confirm('Удалить вопрос из теста?')) return;
    const res = await api.deleteQuestionFromTest(selectedTest.test_id, index);
    if (res.ok) {
      toast('Вопрос удалён из теста', 'success');
      const updated = await api.getTestById(selectedTest.test_id);
      if (updated.ok) selectTest(updated.data);
    } else {
      toast(res.data?.detail || 'Ошибка', 'error');
    }
  };

  if (loading) return <p className="text-secondary">Загрузка...</p>;

  return (
    <div className="flex gap-md" style={{ alignItems: 'flex-start' }}>
      {/* Test list */}
      <div className="card" style={{ width: 280, flexShrink: 0 }}>
        <h3 style={{ marginBottom: '.75rem', fontSize: '.95rem' }}>Тесты</h3>
        <div className="flex flex-col gap-xs" style={{ maxHeight: '60vh', overflowY: 'auto' }}>
          {tests.map(t => (
            <button key={t.test_id}
              className={`sidebar-item ${selectedTest?.test_id === t.test_id ? 'sidebar-item-active' : ''}`}
              onClick={() => selectTest(t)}
            >
              <span style={{ flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{t.test_name}</span>
              <span className="badge badge-neutral text-xs">{(t.questions || []).length}</span>
            </button>
          ))}
          {tests.length === 0 && <p className="text-secondary text-sm">Нет тестов</p>}
        </div>
      </div>

      {/* Details panel */}
      {selectedTest ? (
        <div style={{ flex: 1 }}>
          <div className="card mb-4">
            <div className="flex items-center" style={{ justifyContent: 'space-between', marginBottom: '.75rem' }}>
              <h2 style={{ fontSize: '1.1rem' }}>{selectedTest.test_name}</h2>
              <div className="flex gap-xs">
                <button className="btn btn-secondary btn-sm" onClick={handleRenameTest}><FiEdit2 size={14} /> Переименовать</button>
                <button className="btn btn-secondary btn-sm" onClick={() => setShowStats(true)}><FiBarChart2 size={14} /> Статистика</button>
                <button className="btn btn-secondary btn-sm" onClick={() => setShowCriteria(true)}><FiSliders size={14} /> Критерии</button>
                <button className="btn btn-secondary btn-sm" onClick={handleCloneTest}><FiCopy size={14} /> Клон</button>
                <button className="btn btn-danger btn-sm" onClick={handleDeleteTest}><FiTrash2 size={14} /> Удалить</button>
              </div>
            </div>
            <div className="text-sm text-secondary mb-2">
              Создатель: {selectedTest.creator_username} • Дата: {selectedTest.creation_date || '—'}
              {selectedTest.time_limit_minutes ? ` • ${selectedTest.time_limit_minutes} мин` : ''}
            </div>

            {/* Questions in test */}
            <h3 style={{ fontSize: '.95rem', margin: '.75rem 0 .5rem' }}>Вопросы ({(selectedTest.questions || []).length})</h3>
            <div className="flex flex-col gap-xs" style={{ maxHeight: '30vh', overflowY: 'auto' }}>
              {(selectedTest.questions || []).map((q, i) => (
                <div key={i} className="flex items-center gap-sm" style={{ padding: '.4rem .6rem', borderRadius: 6, background: 'var(--card-bg)', border: '1px solid var(--border)' }}>
                  <span className="text-sm" style={{ flex: 1 }}>{i + 1}. [{q.topic || q.category}] {q.question}</span>
                  <button className="btn btn-ghost btn-sm" style={{ color: 'var(--color-red)' }} onClick={() => handleDeleteQuestion(i)}><FiTrash2 size={12} /></button>
                </div>
              ))}
            </div>
            <button className="btn btn-secondary btn-sm mt-2" onClick={() => setShowAddQ(true)}><FiPlus size={14} /> Добавить вопросы</button>
          </div>

          {/* Assignments */}
          <div className="card">
            <h3 style={{ fontSize: '.95rem', marginBottom: '.75rem' }}><FiUsers size={16} style={{ marginRight: 6 }} />Назначение студентам</h3>
            <div className="flex items-center gap-sm mb-2">
              <select className="select" value={groupFilter} onChange={e => setGroupFilter(e.target.value)}>
                <option value="">Все группы</option>
                {groups.map(g => <option key={g} value={g}>{g}</option>)}
              </select>
              {groupFilter && <button className="btn btn-secondary btn-sm" onClick={toggleGroup}>
                {filteredStudents.every(s => localAssigned.has(s.username)) ? 'Снять группу' : 'Назначить группу'}
              </button>}
            </div>
            <div style={{ maxHeight: '25vh', overflowY: 'auto' }}>
              {filteredStudents.map(s => (
                <label key={s.username} className="flex items-center gap-xs" style={{ padding: '4px 0' }}>
                  <input type="checkbox" checked={localAssigned.has(s.username)} onChange={() => toggleStudent(s.username)} />
                  <span>{s.username}</span>
                  {s.group && <span className="badge badge-neutral text-xs">{s.group}</span>}
                </label>
              ))}
              {filteredStudents.length === 0 && <p className="text-secondary text-sm">Нет студентов</p>}
            </div>
            <button className="btn btn-primary btn-sm mt-2" onClick={saveAssignments}>Сохранить назначения</button>
          </div>
        </div>
      ) : (
        <div className="card" style={{ flex: 1 }}><p className="text-secondary">Выберите тест из списка</p></div>
      )}

      {/* Add questions modal */}
      {showAddQ && selectedTest && (
        <AddQuestionsModal
          testId={selectedTest.test_id}
          existingQuestions={selectedTest.questions || []}
          onClose={() => { setShowAddQ(false); loadTests(); }}
        />
      )}

      {/* Statistics modal */}
      {showStats && selectedTest && (
        <StatisticsModal testId={selectedTest.test_id} testName={selectedTest.test_name} onClose={() => setShowStats(false)} />
      )}

      {/* Criteria modal */}
      {showCriteria && selectedTest && (
        <TestCriteriaModal testId={selectedTest.test_id} onClose={() => setShowCriteria(false)} />
      )}
    </div>
  );
}

/* ======================== ADD QUESTIONS MODAL ======================== */
function AddQuestionsModal({ testId, existingQuestions, onClose }) {
  const toast = useToast();
  const [questions, setQuestions] = useState({});
  const [selected, setSelected] = useState(new Set());
  const [topicFilter, setTopicFilter] = useState('');
  const [textFilter, setTextFilter] = useState('');
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    api.getQuestions().then(r => { if (r.ok) setQuestions(r.data || {}); });
  }, []);

  const existingTexts = new Set((existingQuestions || []).map(q => q.question));
  const allQuestions = [];
  for (const [topic, qs] of Object.entries(questions)) {
    qs.forEach((q, i) => allQuestions.push({ ...q, topic, uid: `${topic}__${i}`, inTest: existingTexts.has(q.question) }));
  }
  const filtered = allQuestions.filter(q =>
    (!topicFilter || q.topic === topicFilter) &&
    (!textFilter || q.question.toLowerCase().includes(textFilter.toLowerCase()))
  );

  const handleAdd = async () => {
    const toAdd = allQuestions.filter(q => selected.has(q.uid)).map(q => {
      const { uid, inTest, ...rest } = q;
      return rest;
    });
    if (toAdd.length === 0) { toast('Выберите вопросы', 'error'); return; }
    setSaving(true);
    const res = await api.addQuestionsToTest(testId, toAdd);
    setSaving(false);
    if (res.ok) { toast('Вопросы добавлены', 'success'); onClose(); }
    else toast(res.data?.detail || 'Ошибка', 'error');
  };

  return (
    <Modal title="Добавить вопросы в тест" onClose={onClose}>
      <div className="flex items-center gap-sm mb-2">
        <select className="select" value={topicFilter} onChange={e => setTopicFilter(e.target.value)}>
          <option value="">Все темы</option>
          {Object.keys(questions).map(t => <option key={t} value={t}>{t}</option>)}
        </select>
        <input className="input" placeholder="Поиск..." value={textFilter} onChange={e => setTextFilter(e.target.value)} />
      </div>
      <div style={{ maxHeight: '50vh', overflowY: 'auto' }}>
        {filtered.map(q => (
          <label key={q.uid} className={`question-pick-item ${q.inTest ? 'question-pick-disabled' : ''}`}>
            <input type="checkbox" disabled={q.inTest} checked={selected.has(q.uid)} onChange={() => {
              setSelected(prev => { const s = new Set(prev); s.has(q.uid) ? s.delete(q.uid) : s.add(q.uid); return s; });
            }} />
            <span className="badge badge-neutral" style={{ fontSize: '.75rem' }}>{q.topic}</span>
            <span style={{ flex: 1 }}>{q.question}</span>
            {q.inTest && <span className="badge badge-yellow text-xs">уже в тесте</span>}
          </label>
        ))}
      </div>
      <div style={{ textAlign: 'right', marginTop: '.75rem' }}>
        <button className="btn btn-primary" disabled={saving} onClick={handleAdd}><FiPlus size={14} /> Добавить выбранные</button>
      </div>
    </Modal>
  );
}

/* ======================== STATISTICS MODAL ======================== */
function StatisticsModal({ testId, testName, onClose }) {
  const [results, setResults] = useState([]);
  const [stats, setStats] = useState(null);
  const [textFilter, setTextFilter] = useState('');
  const [groupFilter, setGroupFilter] = useState('');
  const [groups, setGroups] = useState([]);
  const [studentsByGroup, setStudentsByGroup] = useState({});
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      api.getTestResults(testId),
      api.getTestAggregateStats(testId),
      api.getAllGroups(),
      api.getStudents(),
    ]).then(([rr, sr, gr, studr]) => {
      if (rr.ok) setResults(rr.data || []);
      if (sr.ok) setStats(sr.data);
      if (gr.ok) setGroups(gr.data || []);
      if (studr.ok) {
        const byGroup = {};
        (studr.data || []).forEach(s => {
          if (s.group) {
            if (!byGroup[s.group]) byGroup[s.group] = new Set();
            byGroup[s.group].add(s.username);
          }
        });
        setStudentsByGroup(byGroup);
      }
      setLoading(false);
    });
  }, [testId]);

  const groupStudents = groupFilter ? (studentsByGroup[groupFilter] || new Set()) : null;

  const filtered = results.filter(r =>
    (!textFilter || (r.username || '').toLowerCase().includes(textFilter.toLowerCase())) &&
    (!groupStudents || groupStudents.has(r.username))
  );

  const passed = filtered.filter(r => r.final_status === 'Зачёт' || r.final_status === 'Passed').length;
  const failed = filtered.length - passed;

  const exportCSV = () => {
    const BOM = '\uFEFF';
    const header = 'Студент;Дата;Длительность;Итог;Статус;Правильных';
    const rows = filtered.map(r =>
      [r.username, r.start_time, r.duration, r.final_status, r.status, r.score_percentage?.toFixed(1) + '%'].join(';')
    );
    const csv = BOM + header + '\n' + rows.join('\n');
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `stats_${testName}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const columns = [
    { key: 'username', label: 'Студент' },
    { key: 'start_time', label: 'Дата' },
    { key: 'duration', label: 'Длительность' },
    { key: 'final_status', label: 'Итог', render: v => <span className={`badge ${v === 'Зачёт' || v === 'Passed' ? 'badge-green' : 'badge-red'}`}>{v}</span> },
    { key: 'score_percentage', label: '% верных', render: v => v != null ? v.toFixed(1) + '%' : '—' },
  ];

  return (
    <Modal title={`Статистика: ${testName}`} onClose={onClose} className="modal-lg">
      {loading ? <p className="text-secondary">Загрузка...</p> : (
        <>
          {stats && (
            <div className="flex items-center gap-md mb-4" style={{ flexWrap: 'wrap' }}>
              <div className="badge badge-neutral">Попыток: {stats.total_attempts}</div>
              <div className="badge badge-neutral">Студентов: {stats.unique_students}</div>
              <div className="badge badge-green">Средний балл: {stats.average_score}%</div>
              <div className="badge badge-green">Зачёт: {stats.pass_rate}%</div>
              <div className="badge badge-neutral">Лучший: {stats.best_score}%</div>
              <div className="badge badge-neutral">Худший: {stats.worst_score}%</div>
              <div style={{ marginLeft: 'auto' }}>
                <button className="btn btn-secondary btn-sm" onClick={exportCSV}><FiDownload size={14} /> CSV</button>
              </div>
            </div>
          )}
          {!stats && (
            <div className="flex items-center gap-md mb-4">
              <div className="badge badge-neutral">Всего: {filtered.length}</div>
              <div className="badge badge-green">Зачёт: {passed}</div>
              <div className="badge badge-red">Не зачёт: {failed}</div>
              <div style={{ marginLeft: 'auto' }}>
                <button className="btn btn-secondary btn-sm" onClick={exportCSV}><FiDownload size={14} /> CSV</button>
              </div>
            </div>
          )}
          <div className="flex items-center gap-sm mb-2">
            <input className="input" placeholder="Поиск по студенту..." value={textFilter} onChange={e => setTextFilter(e.target.value)} />
            <select className="select" value={groupFilter} onChange={e => setGroupFilter(e.target.value)}>
              <option value="">Все группы</option>
              {groups.map(g => <option key={g} value={g}>{g}</option>)}
            </select>
          </div>
          <SortableTable columns={columns} data={filtered} emptyText="Нет результатов" />
        </>
      )}
    </Modal>
  );
}

/* ======================== TEST CRITERIA MODAL ======================== */
function TestCriteriaModal({ testId, onClose }) {
  const toast = useToast();
  const [criteria, setCriteria] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.getTestCriteria(testId).then(r => {
      if (r.ok && r.data) {
        setCriteria(Array.isArray(r.data) ? r.data : (r.data.topic_criteria || []));
      } else {
        api.getDefaultCriteria().then(dr => {
          if (dr.ok) setCriteria(Array.isArray(dr.data) ? dr.data : (dr.data.topic_criteria || []));
        });
      }
      setLoading(false);
    });
  }, [testId]);

  const addRow = () => setCriteria([...criteria, { threshold_gte: 0, description: '', is_pass_status: false }]);
  const removeRow = (i) => setCriteria(criteria.filter((_, idx) => idx !== i));
  const updateRow = (i, field, val) => {
    const c = [...criteria];
    c[i] = { ...c[i], [field]: val };
    setCriteria(c);
  };

  const handleSave = async () => {
    const sorted = [...criteria].sort((a, b) => b.threshold_gte - a.threshold_gte);
    const res = await api.saveTestCriteria(testId, { topic_criteria: sorted });
    if (res.ok) { toast('Критерии сохранены', 'success'); onClose(); }
    else toast(res.data?.detail || 'Ошибка', 'error');
  };

  if (loading) return <Modal title="Критерии теста" onClose={onClose}><p className="text-secondary">Загрузка...</p></Modal>;

  return (
    <Modal title="Критерии теста" onClose={onClose}>
      <table className="table mb-2">
        <thead>
          <tr><th>Порог (%)</th><th>Описание</th><th>Зачёт</th><th></th></tr>
        </thead>
        <tbody>
          {criteria.map((c, i) => (
            <tr key={i}>
              <td><input type="number" className="input" style={{ width: 80 }} min={0} max={100} value={c.threshold_gte} onChange={e => updateRow(i, 'threshold_gte', +e.target.value)} /></td>
              <td><input className="input" value={c.description} onChange={e => updateRow(i, 'description', e.target.value)} /></td>
              <td><input type="checkbox" checked={c.is_pass_status} onChange={e => updateRow(i, 'is_pass_status', e.target.checked)} /></td>
              <td><button className="btn btn-ghost btn-sm" style={{ color: 'var(--color-red)' }} onClick={() => removeRow(i)}><FiTrash2 size={12} /></button></td>
            </tr>
          ))}
        </tbody>
      </table>
      <div className="flex gap-sm">
        <button className="btn btn-secondary btn-sm" onClick={addRow}><FiPlus size={14} /> Добавить</button>
        <button className="btn btn-primary btn-sm" onClick={handleSave}>Сохранить</button>
      </div>
    </Modal>
  );
}

/* ======================== HISTORY TAB ======================== */
function HistoryTab() {
  const toast = useToast();
  const [searchMode, setSearchMode] = useState('student');
  const [searchValue, setSearchValue] = useState('');
  const [results, setResults] = useState([]);
  const [textFilter, setTextFilter] = useState('');
  const [loading, setLoading] = useState(false);
  const [detailResult, setDetailResult] = useState(null);
  const [studentOptions, setStudentOptions] = useState([]);
  const [groupOptions, setGroupOptions] = useState([]);

  useEffect(() => {
    Promise.all([api.getStudents(), api.getAllGroups()]).then(([sr, gr]) => {
      if (sr.ok) setStudentOptions((sr.data || []).map(s => s.username));
      if (gr.ok) setGroupOptions(gr.data || []);
    });
  }, []);

  const searchOptions = searchMode === 'student' ? studentOptions : groupOptions;

  const handleSearch = async () => {
    if (!searchValue.trim()) return;
    setLoading(true);
    if (searchMode === 'student') {
      const res = await api.getUserHistory(searchValue.trim());
      if (res.ok) setResults(res.data || []);
      else { toast(res.data?.detail || 'Не найдено', 'error'); setResults([]); }
    } else {
      const gr = await api.getUsersByGroup(searchValue.trim());
      if (gr.ok && gr.data?.length > 0) {
        const all = [];
        for (const username of gr.data) {
          const r = await api.getUserHistory(username);
          if (r.ok) all.push(...(r.data || []).map(h => ({ ...h, username })));
        }
        setResults(all);
      } else {
        toast('Группа не найдена или пуста', 'error');
        setResults([]);
      }
    }
    setLoading(false);
  };

  const filtered = results.filter(r =>
    !textFilter ||
    Object.values(r).some(v => String(v).toLowerCase().includes(textFilter.toLowerCase()))
  );

  const columns = [
    { key: 'username', label: 'Студент' },
    { key: 'test_name', label: 'Тест' },
    { key: 'attempt_number', label: 'Попытка' },
    { key: 'start_time', label: 'Дата' },
    { key: 'duration', label: 'Длительность' },
    { key: 'score_percentage', label: '% верных', render: v => v != null ? v.toFixed(1) + '%' : '—' },
    { key: 'final_status', label: 'Итог', render: v => <span className={`badge ${v === 'Зачёт' || v === 'Passed' ? 'badge-green' : 'badge-red'}`}>{v}</span> },
  ];

  return (
    <>
      <div className="flex items-center gap-sm mb-4">
        <div className="flex gap-sm">
          <label className="flex items-center gap-xs"><input type="radio" checked={searchMode === 'student'} onChange={() => setSearchMode('student')} /> По студенту</label>
          <label className="flex items-center gap-xs"><input type="radio" checked={searchMode === 'group'} onChange={() => setSearchMode('group')} /> По группе</label>
        </div>
        <AutocompleteInput
          value={searchValue}
          onChange={val => { setSearchValue(val); }}
          options={searchOptions}
          placeholder={searchMode === 'student' ? 'Имя студента...' : 'Название группы...'}
          style={{ maxWidth: 300 }}
          onEnter={handleSearch}
        />
        <button className="btn btn-primary btn-sm" onClick={handleSearch} disabled={loading}><FiSearch size={14} /> Найти</button>
      </div>

      {results.length > 0 && (
        <>
          <input className="input mb-2" style={{ maxWidth: 300 }} placeholder="Фильтр..." value={textFilter} onChange={e => setTextFilter(e.target.value)} />
          <SortableTable columns={columns} data={filtered} emptyText="Нет результатов" onRowClick={setDetailResult} />
        </>
      )}

      {detailResult && (
        <Modal title="Детали" onClose={() => setDetailResult(null)}>
          <div className="text-sm">
            <p><strong>Студент:</strong> {detailResult.username}</p>
            <p><strong>Тест:</strong> {detailResult.test_name}</p>
            <p><strong>Результат:</strong> {detailResult.final_status} ({detailResult.score_percentage?.toFixed(1)}%)</p>
            <p><strong>Длительность:</strong> {detailResult.duration}</p>
          </div>
          {detailResult.answers && detailResult.answers.length > 0 && (
            <div className="mt-2">
              <h4 style={{ marginBottom: '.5rem' }}>Ответы</h4>
              {detailResult.answers.map((a, i) => {
                const correct = JSON.stringify(a.user_answer) === JSON.stringify(a.correct_answer);
                return (
                  <div key={i} style={{ padding: '.5rem', marginBottom: '.25rem', borderRadius: 6, background: correct ? 'rgba(16,185,129,.08)' : 'rgba(239,68,68,.08)' }}>
                    <div style={{ fontWeight: 600, fontSize: '.85rem' }}>{i + 1}. {a.question}</div>
                    <div className="text-sm text-secondary">
                      Ответ: {Array.isArray(a.user_answer) ? a.user_answer.join(', ') : (a.user_answer || '—')}
                      {!correct && <> | Верный: {Array.isArray(a.correct_answer) ? a.correct_answer.join(', ') : a.correct_answer}</>}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </Modal>
      )}
    </>
  );
}
