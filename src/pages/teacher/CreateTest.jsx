import React, { useState, useEffect } from 'react';
import { useAuth } from '../../context/AuthContext';
import { useToast } from '../../components/Toast';
import Modal from '../../components/Modal';
import * as api from '../../api';
import { FiSave, FiFilter, FiSliders, FiPlus, FiTrash2 } from 'react-icons/fi';

export default function CreateTest() {
  const { user } = useAuth();
  const toast = useToast();
  const [questions, setQuestions] = useState({});
  const [selectedIds, setSelectedIds] = useState(new Set());
  const [topicFilter, setTopicFilter] = useState('');
  const [testName, setTestName] = useState('');
  const [timeLimit, setTimeLimit] = useState(0);
  const [cooldown, setCooldown] = useState(24);
  const [maxAttempts, setMaxAttempts] = useState(0);
  const [saving, setSaving] = useState(false);
  const [pendingCriteria, setPendingCriteria] = useState(null);
  const [showCriteria, setShowCriteria] = useState(false);

  useEffect(() => {
    api.getQuestions().then(r => { if (r.ok) setQuestions(r.data || {}); });
  }, []);

  const topics = Object.keys(questions);
  const allQuestions = [];
  for (const [topic, qs] of Object.entries(questions)) {
    qs.forEach((q, i) => allQuestions.push({ ...q, topic, originalIndex: i, uid: `${topic}__${i}` }));
  }
  const filtered = topicFilter ? allQuestions.filter(q => q.topic === topicFilter) : allQuestions;

  const toggleAll = () => {
    const filteredIds = new Set(filtered.map(q => q.uid));
    const allSelected = filtered.every(q => selectedIds.has(q.uid));
    if (allSelected) {
      setSelectedIds(prev => { const s = new Set(prev); filteredIds.forEach(id => s.delete(id)); return s; });
    } else {
      setSelectedIds(prev => { const s = new Set(prev); filteredIds.forEach(id => s.add(id)); return s; });
    }
  };

  const toggleOne = (uid) => {
    setSelectedIds(prev => { const s = new Set(prev); s.has(uid) ? s.delete(uid) : s.add(uid); return s; });
  };

  const handleCreate = async () => {
    if (!testName.trim()) { toast('Введите название теста', 'error'); return; }
    if (selectedIds.size === 0) { toast('Выберите хотя бы один вопрос', 'error'); return; }

    const selectedQuestions = allQuestions.filter(q => selectedIds.has(q.uid)).map(q => {
      const { uid, originalIndex, ...rest } = q;
      return rest;
    });

    setSaving(true);
    const res = await api.createTest(
      testName.trim(),
      selectedQuestions,
      timeLimit || null,
      cooldown,
      maxAttempts || null
    );
    setSaving(false);

    if (res.ok) {
      // Save per-test criteria if configured
      if (pendingCriteria && res.data?.test_id) {
        const sorted = [...pendingCriteria].sort((a, b) => b.threshold_gte - a.threshold_gte);
        await api.saveTestCriteria(res.data.test_id, { topic_criteria: sorted });
      }
      toast('Тест создан!', 'success');
      setTestName('');
      setSelectedIds(new Set());
      setPendingCriteria(null);
    } else {
      toast(res.data?.detail || 'Ошибка создания теста', 'error');
    }
  };

  return (
    <>
      <h1 className="page-title">Создать готовый тест</h1>
      <div className="flex gap-md" style={{ alignItems: 'flex-start' }}>
        {/* Settings panel */}
        <div className="card" style={{ width: 300, flexShrink: 0 }}>
          <h3 style={{ marginBottom: '.75rem' }}>Параметры теста</h3>
          <div className="form-group">
            <label className="form-label">Название теста</label>
            <input className="input" value={testName} onChange={e => setTestName(e.target.value)} placeholder="Название..." />
          </div>
          <div className="form-group">
            <label className="form-label">Лимит времени (мин, 0 = без)</label>
            <input type="number" className="input" min={0} max={300} value={timeLimit} onChange={e => setTimeLimit(+e.target.value)} />
          </div>
          <div className="form-group">
            <label className="form-label">Перерыв (часов)</label>
            <input type="number" className="input" min={0} max={720} value={cooldown} onChange={e => setCooldown(+e.target.value)} />
          </div>
          <div className="form-group">
            <label className="form-label">Макс. попыток (0 = безлимит)</label>
            <input type="number" className="input" min={0} max={100} value={maxAttempts} onChange={e => setMaxAttempts(+e.target.value)} />
          </div>
          <div className="text-sm text-secondary mb-2">Выбрано вопросов: <strong>{selectedIds.size}</strong></div>
          <button className="btn btn-secondary mb-2" style={{ width: '100%' }} onClick={() => setShowCriteria(true)}>
            <FiSliders size={16} /> {pendingCriteria ? 'Изменить критерии' : 'Настроить критерии'}
          </button>
          {pendingCriteria && <div className="text-sm text-secondary mb-2" style={{ color: 'var(--color-green)' }}>✓ Критерии настроены ({pendingCriteria.length} уровней)</div>}
          <button className="btn btn-primary" style={{ width: '100%' }} disabled={saving} onClick={handleCreate}>
            <FiSave size={16} /> {saving ? 'Создание...' : 'Создать тест'}
          </button>
        </div>

        {/* Question picker */}
        <div style={{ flex: 1 }}>
          <div className="flex items-center gap-sm mb-4">
            <FiFilter size={16} className="text-secondary" />
            <select className="select" value={topicFilter} onChange={e => setTopicFilter(e.target.value)}>
              <option value="">Все темы</option>
              {topics.map(t => <option key={t} value={t}>{t}</option>)}
            </select>
            <button className="btn btn-secondary btn-sm" onClick={toggleAll}>
              {filtered.every(q => selectedIds.has(q.uid)) ? 'Снять все' : 'Выбрать все'}
            </button>
          </div>
          <div className="flex flex-col gap-xs" style={{ maxHeight: '65vh', overflowY: 'auto' }}>
            {filtered.map(q => (
              <label key={q.uid} className={`question-pick-item ${selectedIds.has(q.uid) ? 'question-pick-selected' : ''}`}>
                <input type="checkbox" checked={selectedIds.has(q.uid)} onChange={() => toggleOne(q.uid)} />
                <span className="badge badge-neutral" style={{ fontSize: '.75rem' }}>{q.topic}</span>
                <span style={{ flex: 1 }}>{q.question}</span>
                <span className="text-sm text-secondary">{q.points} б.</span>
              </label>
            ))}
            {filtered.length === 0 && <p className="text-secondary">Нет вопросов</p>}
          </div>
        </div>
      </div>

      {showCriteria && (
        <CreateTestCriteriaModal
          criteria={pendingCriteria}
          onSave={(c) => { setPendingCriteria(c); setShowCriteria(false); }}
          onClose={() => setShowCriteria(false)}
        />
      )}
    </>
  );
}

function CreateTestCriteriaModal({ criteria: initial, onSave, onClose }) {
  const [criteria, setCriteria] = useState(initial || []);
  const [loading, setLoading] = useState(!initial);

  useEffect(() => {
    if (!initial) {
      api.getDefaultCriteria().then(r => {
        if (r.ok) setCriteria(Array.isArray(r.data) ? r.data : (r.data?.topic_criteria || []));
        setLoading(false);
      });
    }
  }, []);

  const addRow = () => setCriteria([...criteria, { threshold_gte: 0, description: '', is_pass_status: false }]);
  const removeRow = (i) => setCriteria(criteria.filter((_, idx) => idx !== i));
  const updateRow = (i, field, val) => {
    const c = [...criteria];
    c[i] = { ...c[i], [field]: val };
    setCriteria(c);
  };

  if (loading) return <Modal title="Критерии оценки" onClose={onClose}><p className="text-secondary">Загрузка...</p></Modal>;

  return (
    <Modal title="Критерии оценки для теста" onClose={onClose}>
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
        <button className="btn btn-primary btn-sm" onClick={() => onSave(criteria)}>Применить</button>
      </div>
    </Modal>
  );
}
