import React, { useState, useEffect } from 'react';
import { useToast } from '../../components/Toast';
import * as api from '../../api';
import { FiZap, FiSave } from 'react-icons/fi';

export default function GenerateTest() {
  const toast = useToast();
  const [categories, setCategories] = useState([]);
  const [topic, setTopic] = useState('');
  const [maxScore, setMaxScore] = useState(20);
  const [generated, setGenerated] = useState(null);
  const [testName, setTestName] = useState('');
  const [timeLimitMinutes, setTimeLimitMinutes] = useState('');
  const [cooldownHours, setCooldownHours] = useState('');
  const [maxAttempts, setMaxAttempts] = useState('');
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    api.getCategories().then(r => {
      if (r.ok && r.data?.length > 0) {
        setCategories(r.data);
        setTopic(r.data[0]);
      }
    });
  }, []);

  const handleGenerate = async () => {
    if (!topic) { toast('Выберите тему', 'error'); return; }
    setLoading(true);
    const res = await api.generateTestByTopicScore(topic, maxScore);
    setLoading(false);
    if (res.ok) {
      setGenerated(res.data);
      setTestName(`${topic} — ${maxScore} баллов`);
    } else {
      toast(res.data?.detail || 'Ошибка генерации', 'error');
    }
  };

  const handleSave = async () => {
    if (!testName.trim()) { toast('Введите название', 'error'); return; }
    if (!generated?.questions) return;
    setSaving(true);
    const res = await api.createTest(
      testName.trim(),
      generated.questions,
      timeLimitMinutes ? +timeLimitMinutes : undefined,
      cooldownHours !== '' ? +cooldownHours : undefined,
      maxAttempts ? +maxAttempts : undefined,
    );
    setSaving(false);
    if (res.ok) {
      toast('Тест сохранён!', 'success');
      setGenerated(null);
    } else {
      toast(res.data?.detail || 'Ошибка', 'error');
    }
  };

  return (
    <>
      <h1 className="page-title">Сгенерировать тест по теме и баллам</h1>

      <div className="card" style={{ maxWidth: 500, marginBottom: '1.5rem' }}>
        <div className="form-group">
          <label className="form-label">Тема</label>
          <select className="select" value={topic} onChange={e => setTopic(e.target.value)}>
            {categories.map(c => <option key={c} value={c}>{c}</option>)}
          </select>
        </div>
        <div className="form-group">
          <label className="form-label">Максимальный балл</label>
          <input type="number" className="input" style={{ width: 120 }} min={1} max={500} value={maxScore} onChange={e => setMaxScore(+e.target.value)} />
        </div>
        <button className="btn btn-primary" disabled={loading} onClick={handleGenerate}>
          <FiZap size={16} /> {loading ? 'Генерация...' : 'Сгенерировать'}
        </button>
      </div>

      {generated && generated.questions && (
        <div>
          <div className="card mb-4">
            <h3 style={{ marginBottom: '.75rem' }}>Сгенерированный тест ({generated.questions.length} вопросов, {generated.total_points || generated.questions.reduce((s, q) => s + (q.points || 1), 0)} баллов)</h3>
            <div className="flex flex-col gap-sm">
              {generated.questions.map((q, i) => (
                <div key={i} style={{ padding: '.75rem', borderRadius: 8, border: '1px solid var(--border)', background: 'var(--card-bg)' }}>
                  <div style={{ fontWeight: 600, fontSize: '.9rem', marginBottom: 4 }}>
                    {i + 1}. {q.question} <span className="badge badge-neutral text-xs">{q.points || 1} б.</span>
                  </div>
                  <div className="text-sm text-secondary">
                    Тип: {q.answer_type === 'multiple' ? 'множественный' : 'одиночный'} • 
                    Варианты: {(q.options || []).join(', ')}
                  </div>
                  <div className="text-sm" style={{ color: 'var(--color-green)' }}>
                    Ответ: {Array.isArray(q.correct) ? q.correct.join(', ') : q.correct}
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div className="card" style={{ maxWidth: 500 }}>
            <h3 style={{ marginBottom: '.75rem' }}>Сохранить как тест</h3>
            <div className="form-group">
              <label className="form-label">Название теста</label>
              <input className="input" value={testName} onChange={e => setTestName(e.target.value)} />
            </div>
            <div className="form-group">
              <label className="form-label">Ограничение по времени (мин, необязательно)</label>
              <input type="number" className="input" style={{ width: 120 }} min={1} value={timeLimitMinutes} onChange={e => setTimeLimitMinutes(e.target.value)} placeholder="—" />
            </div>
            <div className="form-group">
              <label className="form-label">Кулдаун между попытками (часов)</label>
              <input type="number" className="input" style={{ width: 120 }} min={0} value={cooldownHours} onChange={e => setCooldownHours(e.target.value)} placeholder="24" />
            </div>
            <div className="form-group">
              <label className="form-label">Максимум попыток (необязательно)</label>
              <input type="number" className="input" style={{ width: 120 }} min={1} value={maxAttempts} onChange={e => setMaxAttempts(e.target.value)} placeholder="—" />
            </div>
            <button className="btn btn-primary" disabled={saving} onClick={handleSave}>
              <FiSave size={16} /> {saving ? 'Сохранение...' : 'Сохранить тест'}
            </button>
          </div>
        </div>
      )}
    </>
  );
}
