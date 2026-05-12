import React, { useState, useEffect } from 'react';
import { useToast } from '../../components/Toast';
import Modal from '../../components/Modal';
import AutocompleteInput from '../../components/AutocompleteInput';
import * as api from '../../api';
import { FiEdit, FiTrash2, FiSave, FiPlus } from 'react-icons/fi';

export default function EditQuestions() {
  const toast = useToast();
  const [questions, setQuestions] = useState({});
  const [selectedTopic, setSelectedTopic] = useState('');
  const [editing, setEditing] = useState(null);
  const [loading, setLoading] = useState(true);

  const loadQuestions = async () => {
    setLoading(true);
    const res = await api.getQuestions();
    if (res.ok) {
      setQuestions(res.data || {});
      const topics = Object.keys(res.data || {});
      if (topics.length > 0 && !topics.includes(selectedTopic)) setSelectedTopic(topics[0]);
    }
    setLoading(false);
  };

  useEffect(() => { loadQuestions(); }, []);

  const topics = Object.keys(questions);
  const currentQuestions = questions[selectedTopic] || [];

  const handleDelete = async (index) => {
    if (!window.confirm('Удалить этот вопрос?')) return;
    const res = await api.deleteQuestion(selectedTopic, index);
    if (res.ok) {
      toast('Вопрос удалён', 'success');
      loadQuestions();
    } else {
      toast(res.data?.detail || 'Ошибка', 'error');
    }
  };

  const handleEdit = (index) => {
    const q = currentQuestions[index];
    setEditing({
      index,
      originalTopic: selectedTopic,
      topic: selectedTopic,
      questionText: q.question || '',
      options: [...(q.options || []), ...Array(5).fill('')].slice(0, 5),
      answerType: q.answer_type || 'single',
      correctSingle: (q.answer_type || 'single') === 'single' ? (q.correct ?? null) : null,
      correctMultiple: (q.answer_type || 'single') === 'multiple'
        ? (Array.isArray(q.correct) ? q.correct : (q.correct ? [q.correct] : []))
        : [],
      points: q.points || 1,
      useMatrices: !!q.matrices && Object.keys(q.matrices).length > 0,
      matrices: q.matrices ? Object.entries(q.matrices).map(([name, data]) => ({ name, rows: data.length, cols: data[0]?.length || 0, data })) : [],
      useCommands: !!q.commands && q.commands.length > 0,
      commands: q.commands || [],
    });
  };

  const handleSaveEdit = async () => {
    const e = editing;
    if (!e) return;
    const validOpts = e.options.filter(o => o.trim());
    if (validOpts.length < 2) { toast('Нужно минимум 2 варианта', 'error'); return; }

    const correct = e.answerType === 'single' ? e.correctSingle : e.correctMultiple.filter(c => validOpts.includes(c));
    const body = {
      question: e.questionText.trim(),
      options: validOpts,
      correct,
      answer_type: e.answerType,
      points: e.points,
    };
    if (e.useMatrices && e.matrices.length > 0) {
      const m = {};
      e.matrices.forEach(mt => { m[mt.name] = mt.data; });
      body.matrices = m;
    }
    if (e.useCommands && e.commands.filter(c => c.trim()).length > 0) {
      body.commands = e.commands.filter(c => c.trim());
    }

    let res;
    if (e.topic.trim() !== e.originalTopic) {
      await api.deleteQuestion(e.originalTopic, e.index);
      res = await api.addQuestion(e.topic.trim(), body);
    } else {
      res = await api.updateQuestion(e.originalTopic, e.index, body);
    }

    if (res.ok) {
      toast('Вопрос обновлён', 'success');
      setEditing(null);
      loadQuestions();
    } else {
      toast(res.data?.detail || 'Ошибка', 'error');
    }
  };

  if (loading) return <p className="text-secondary">Загрузка...</p>;

  return (
    <>
      <h1 className="page-title">Редактирование вопросов</h1>
      <div className="flex gap-md" style={{ alignItems: 'flex-start' }}>
        {/* Topic list */}
        <div className="card" style={{ width: 250, flexShrink: 0 }}>
          <h3 style={{ marginBottom: '.75rem', fontSize: '.95rem' }}>Темы</h3>
          {topics.length === 0 ? <p className="text-secondary text-sm">Нет вопросов</p> : (
            <div className="flex flex-col gap-xs">
              {topics.map(t => (
                <button key={t} className={`sidebar-item ${t === selectedTopic ? 'sidebar-item-active' : ''}`} onClick={() => setSelectedTopic(t)}>
                  {t} <span className="badge badge-neutral" style={{ marginLeft: 'auto' }}>{questions[t].length}</span>
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Questions list */}
        <div style={{ flex: 1 }}>
          {currentQuestions.length === 0 ? (
            <div className="card"><p className="text-secondary">Выберите тему</p></div>
          ) : (
            <div className="flex flex-col gap-sm">
              {currentQuestions.map((q, i) => (
                <div key={i} className="card" style={{ padding: '.75rem 1rem' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                    <div style={{ flex: 1 }}>
                      <div style={{ fontWeight: 600, fontSize: '.9rem', marginBottom: 4 }}>{i + 1}. {q.question}</div>
                      <div className="text-sm text-secondary">
                        {q.answer_type === 'multiple' ? 'Множественный' : 'Одиночный'} • {q.points} б.
                        {q.options && ` • ${q.options.length} вариантов`}
                      </div>
                    </div>
                    <div className="flex gap-xs">
                      <button className="btn btn-ghost btn-sm" onClick={() => handleEdit(i)}><FiEdit size={14} /></button>
                      <button className="btn btn-ghost btn-sm" style={{ color: 'var(--color-red)' }} onClick={() => handleDelete(i)}><FiTrash2 size={14} /></button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Edit modal */}
      {editing && (
        <Modal title="Редактирование вопроса" onClose={() => setEditing(null)}>
          <EditQuestionForm
            editing={editing}
            setEditing={setEditing}
            topics={topics}
            onSave={handleSaveEdit}
          />
        </Modal>
      )}
    </>
  );
}

function EditQuestionForm({ editing, setEditing, topics, onSave }) {
  const e = editing;
  const upd = (field, val) => setEditing({ ...e, [field]: val });
  const validOptions = e.options.filter(o => o.trim());

  return (
    <div style={{ maxHeight: '70vh', overflowY: 'auto', padding: '0 .25rem' }}>
      <div className="form-group">
        <label className="form-label">Тема</label>
        <AutocompleteInput value={e.topic} onChange={val => upd('topic', val)} options={topics} placeholder="Тема..." />
      </div>
      <div className="form-group">
        <label className="form-label">Текст вопроса</label>
        <textarea className="input" rows={3} value={e.questionText} onChange={ev => upd('questionText', ev.target.value)} />
      </div>

      {/* Matrices editing */}
      <div className="form-group">
        <label className="flex items-center gap-xs">
          <input type="checkbox" checked={e.useMatrices} onChange={ev => upd('useMatrices', ev.target.checked)} />
          <span className="form-label" style={{ margin: 0 }}>Матрицы</span>
        </label>
        {e.useMatrices && (
          <div style={{ marginTop: '.5rem' }}>
            {e.matrices.map((mt, mi) => (
              <div key={mi} style={{ marginBottom: '.75rem', padding: '.5rem', border: '1px solid var(--border)', borderRadius: 8 }}>
                <div className="flex items-center gap-sm mb-2">
                  <input className="input" style={{ flex: 1 }} placeholder="Название матрицы" value={mt.name} onChange={ev => {
                    const ms = [...e.matrices]; ms[mi] = { ...ms[mi], name: ev.target.value }; upd('matrices', ms);
                  }} />
                  <input type="number" className="input" style={{ width: 65 }} placeholder="Строк" min={1} max={20} value={mt.rows} onChange={ev => {
                    const newRows = +ev.target.value || 1;
                    const ms = [...e.matrices];
                    const data = [...(ms[mi].data || [])];
                    while (data.length < newRows) data.push(Array(mt.cols || 1).fill(''));
                    ms[mi] = { ...ms[mi], rows: newRows, data: data.slice(0, newRows) };
                    upd('matrices', ms);
                  }} />
                  <span className="text-sm text-secondary">×</span>
                  <input type="number" className="input" style={{ width: 65 }} placeholder="Колонок" min={1} max={20} value={mt.cols} onChange={ev => {
                    const newCols = +ev.target.value || 1;
                    const ms = [...e.matrices];
                    const data = (ms[mi].data || []).map(row => {
                      const r = [...row];
                      while (r.length < newCols) r.push('');
                      return r.slice(0, newCols);
                    });
                    ms[mi] = { ...ms[mi], cols: newCols, data };
                    upd('matrices', ms);
                  }} />
                  <button className="btn btn-ghost btn-sm" style={{ color: 'var(--color-red)' }} onClick={() => upd('matrices', e.matrices.filter((_, i) => i !== mi))}><FiTrash2 size={12} /></button>
                </div>
                <table className="matrix-table" onClick={e => { const input = e.target.closest('td')?.querySelector('input'); if (input) input.focus(); }}>
                  <tbody>
                    {(mt.data || []).map((row, ri) => (
                      <tr key={ri}>
                        {(row || []).map((cell, ci) => (
                          <td key={ci}><input className="matrix-cell-input" style={{ width: 70, textAlign: 'center', fontSize: '.9rem' }} value={cell} placeholder="-" onChange={ev => {
                            const ms = [...e.matrices];
                            const data = ms[mi].data.map(r => [...r]);
                            data[ri][ci] = ev.target.value;
                            ms[mi] = { ...ms[mi], data };
                            upd('matrices', ms);
                          }} /></td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ))}
            <button className="btn btn-secondary btn-sm" onClick={() => upd('matrices', [...e.matrices, { name: '', rows: 2, cols: 2, data: [['', ''], ['', '']] }])}><FiPlus size={12} /> Добавить матрицу</button>
          </div>
        )}
      </div>

      {/* Commands editing */}
      <div className="form-group">
        <label className="flex items-center gap-xs">
          <input type="checkbox" checked={e.useCommands} onChange={ev => upd('useCommands', ev.target.checked)} />
          <span className="form-label" style={{ margin: 0 }}>Команды</span>
        </label>
        {e.useCommands && (
          <div style={{ marginTop: '.5rem' }}>
            {e.commands.map((cmd, ci) => (
              <div key={ci} className="flex items-center gap-sm mb-2">
                <input className="input" style={{ flex: 1 }} value={cmd} onChange={ev => {
                  const cs = [...e.commands]; cs[ci] = ev.target.value; upd('commands', cs);
                }} />
                <button className="btn btn-ghost btn-sm" style={{ color: 'var(--color-red)' }} onClick={() => upd('commands', e.commands.filter((_, i) => i !== ci))}><FiTrash2 size={12} /></button>
              </div>
            ))}
            <button className="btn btn-secondary btn-sm" onClick={() => upd('commands', [...e.commands, ''])}><FiPlus size={12} /> Добавить команду</button>
          </div>
        )}
      </div>

      <div className="form-group">
        <label className="form-label">Варианты ответа</label>
        {e.options.map((opt, i) => (
          <div key={i} className="flex items-center gap-sm mb-2">
            <span className="option-letter-badge">{String.fromCharCode(65 + i)}</span>
            <input className="input" style={{ flex: 1 }} value={opt} onChange={ev => { const o = [...e.options]; o[i] = ev.target.value; upd('options', o); }} />
            {opt.trim() && (
              e.answerType === 'single'
                ? <input type="radio" name="edit-correct" checked={e.correctSingle === opt} onChange={() => upd('correctSingle', opt)} title="Правильный ответ" />
                : <input type="checkbox" checked={e.correctMultiple.includes(opt)} onChange={() => upd('correctMultiple', e.correctMultiple.includes(opt) ? e.correctMultiple.filter(x => x !== opt) : [...e.correctMultiple, opt])} title="Правильный ответ" />
            )}
          </div>
        ))}
      </div>
      <div className="form-group">
        <label className="form-label">Тип ответа</label>
        <div className="flex gap-md">
          <label className="flex items-center gap-xs"><input type="radio" checked={e.answerType === 'single'} onChange={() => upd('answerType', 'single')} /> Один</label>
          <label className="flex items-center gap-xs"><input type="radio" checked={e.answerType === 'multiple'} onChange={() => upd('answerType', 'multiple')} /> Несколько</label>
        </div>
      </div>
      <div className="form-group">
        <label className="form-label">Баллы</label>
        <input type="number" className="input" style={{ width: 100 }} min={1} max={100} value={e.points} onChange={ev => upd('points', +ev.target.value)} />
      </div>

      <div style={{ textAlign: 'right' }}>
        <button className="btn btn-primary" onClick={onSave}><FiSave size={16} /> Сохранить</button>
      </div>
    </div>
  );
}
