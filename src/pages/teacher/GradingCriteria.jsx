import React, { useState, useEffect } from 'react';
import { useAuth } from '../../context/AuthContext';
import { useToast } from '../../components/Toast';
import * as api from '../../api';
import { FiPlus, FiTrash2, FiSave, FiRotateCcw } from 'react-icons/fi';

export default function GradingCriteria() {
  const { user } = useAuth();
  const toast = useToast();
  const [criteria, setCriteria] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.getCriteriaForEditing(user.username, user.role).then(r => {
      if (r.ok) {
        const data = r.data;
        setCriteria(Array.isArray(data) ? data : (data?.topic_criteria || []));
      }
      setLoading(false);
    });
  }, [user]);

  const addRow = () => setCriteria([...criteria, { threshold_gte: 0, description: '', is_pass_status: false }]);
  const removeRow = (i) => setCriteria(criteria.filter((_, idx) => idx !== i));
  const updateRow = (i, field, val) => {
    const c = [...criteria];
    c[i] = { ...c[i], [field]: val };
    setCriteria(c);
  };

  const handleSave = async () => {
    const sorted = [...criteria].sort((a, b) => b.threshold_gte - a.threshold_gte);
    const res = await api.saveCriteria(user.username, user.role, { topic_criteria: sorted });
    if (res.ok) toast('Критерии сохранены', 'success');
    else toast(res.data?.detail || 'Ошибка', 'error');
  };

  const handleReset = async () => {
    const res = await api.getDefaultCriteria();
    if (res.ok) {
      const data = res.data;
      setCriteria(Array.isArray(data) ? data : (data?.topic_criteria || []));
      toast('Сброшено к значениям по умолчанию', 'info');
    }
  };

  if (loading) return <p className="text-secondary">Загрузка...</p>;

  return (
    <>
      <h1 className="page-title">Критерии оценки</h1>
      <div className="card" style={{ maxWidth: 700 }}>
        <p className="text-sm text-secondary mb-4">
          Настройте пороговые значения для оценки результатов тестирования. Критерии применяются в порядке убывания порога.
        </p>
        <table className="table criteria-table mb-4">
          <thead>
            <tr>
              <th style={{ width: 120 }}>Порог (%)</th>
              <th>Описание</th>
              <th style={{ width: 80 }}>Зачёт</th>
              <th style={{ width: 50 }}></th>
            </tr>
          </thead>
          <tbody>
            {criteria.map((c, i) => (
              <tr key={i}>
                <td data-label="Порог (%)">
                  <input type="number" className="input" style={{ width: 90 }} min={0} max={100}
                    value={c.threshold_gte} onChange={e => updateRow(i, 'threshold_gte', +e.target.value)} />
                </td>
                <td data-label="Описание">
                  <input className="input" value={c.description || ''}
                    onChange={e => updateRow(i, 'description', e.target.value)} placeholder="Например: Отлично" />
                </td>
                <td style={{ textAlign: 'center' }} data-label="Зачёт">
                  <input type="checkbox" checked={c.is_pass_status || false}
                    onChange={e => updateRow(i, 'is_pass_status', e.target.checked)} />
                </td>
                <td data-label="">
                  <button className="btn btn-ghost btn-sm" style={{ color: 'var(--color-red)' }}
                    onClick={() => removeRow(i)}><FiTrash2 size={14} /></button>
                </td>
              </tr>
            ))}
            {criteria.length === 0 && (
              <tr><td colSpan={4} className="text-secondary text-center">Нет критериев</td></tr>
            )}
          </tbody>
        </table>

        <div className="flex gap-sm">
          <button className="btn btn-secondary btn-sm" onClick={addRow}><FiPlus size={14} /> Добавить</button>
          <button className="btn btn-ghost btn-sm" onClick={handleReset}><FiRotateCcw size={14} /> По умолчанию</button>
          <div style={{ flex: 1 }} />
          <button className="btn btn-primary" onClick={handleSave}><FiSave size={16} /> Сохранить</button>
        </div>
      </div>
    </>
  );
}
