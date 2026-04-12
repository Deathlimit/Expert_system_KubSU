import React, { useState, useEffect } from 'react';
import { useToast } from '../../components/Toast';
import AutocompleteInput from '../../components/AutocompleteInput';
import * as api from '../../api';
import { FiPlus, FiTrash2, FiSave } from 'react-icons/fi';

export default function AddQuestion() {
  const toast = useToast();
  const [categories, setCategories] = useState([]);
  const [topic, setTopic] = useState('');
  const [questionText, setQuestionText] = useState('');
  const [options, setOptions] = useState(['', '', '', '', '']);
  const [answerType, setAnswerType] = useState('single');
  const [correctSingle, setCorrectSingle] = useState(null);
  const [correctMultiple, setCorrectMultiple] = useState([]);
  const [points, setPoints] = useState(1);
  const [useMatrices, setUseMatrices] = useState(false);
  const [matrices, setMatrices] = useState([]);
  const [useCommands, setUseCommands] = useState(false);
  const [commands, setCommands] = useState([]);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    api.getCategories().then(r => { if (r.ok) setCategories(r.data || []); });
  }, []);

  const validOptions = options.filter(o => o.trim());

  const handleAnswerTypeChange = (type) => {
    setAnswerType(type);
    setCorrectSingle(null);
    setCorrectMultiple([]);
    setPoints(type === 'multiple' ? 2 : 1);
  };

  const handleToggleMatrices = (checked) => {
    setUseMatrices(checked);
  };

  const handleToggleCommands = (checked) => {
    setUseCommands(checked);
  };

  const addMatrix = () => {
    if (matrices.length >= 5) return;
    setMatrices([...matrices, { name: `Matrix${matrices.length + 1}`, rows: 2, cols: 2, data: [[0, 0], [0, 0]] }]);
  };

  const updateMatrixCell = (mi, ri, ci, val) => {
    const m = [...matrices];
    m[mi] = { ...m[mi], data: m[mi].data.map((row, r) => r === ri ? row.map((c, cc) => cc === ci ? val : c) : row) };
    setMatrices(m);
  };

  const resizeMatrix = (mi, newRows, newCols) => {
    const m = [...matrices];
    const old = m[mi].data;
    const data = [];
    for (let r = 0; r < newRows; r++) {
      const row = [];
      for (let c = 0; c < newCols; c++) {
        row.push(old[r]?.[c] ?? 0);
      }
      data.push(row);
    }
    m[mi] = { ...m[mi], rows: newRows, cols: newCols, data };
    setMatrices(m);
  };

  const removeMatrix = (mi) => setMatrices(matrices.filter((_, i) => i !== mi));

  const addCommand = () => {
    if (commands.length >= 5) return;
    setCommands([...commands, '']);
  };

  const removeCommand = (ci) => setCommands(commands.filter((_, i) => i !== ci));

  const handleSave = async () => {
    if (!topic.trim()) { toast('Укажите тему', 'error'); return; }
    if (!questionText.trim()) { toast('Введите текст вопроса', 'error'); return; }
    if (validOptions.length < 2) { toast('Нужно минимум 2 варианта ответа', 'error'); return; }
    if (answerType === 'single' && correctSingle == null) { toast('Выберите правильный ответ', 'error'); return; }
    if (answerType === 'multiple' && correctMultiple.length === 0) { toast('Выберите правильные ответы', 'error'); return; }

    const correct = answerType === 'single' ? correctSingle : correctMultiple.filter(c => validOptions.includes(c));
    const body = {
      question: questionText.trim(),
      options: validOptions,
      correct,
      answer_type: answerType,
      points,
    };
    if (useMatrices && matrices.length > 0) {
      const m = {};
      matrices.forEach(mt => { m[mt.name] = mt.data; });
      body.matrices = m;
    }
    if (useCommands && commands.filter(c => c.trim()).length > 0) {
      body.commands = commands.filter(c => c.trim());
    }

    setSaving(true);
    const res = await api.addQuestion(topic.trim(), body);
    setSaving(false);
    if (res.ok) {
      toast('Вопрос добавлен', 'success');
      setQuestionText('');
      setOptions(['', '', '', '', '']);
      setCorrectSingle(null);
      setCorrectMultiple([]);
      setMatrices([]);
      setCommands([]);
      if (!categories.includes(topic.trim())) setCategories([...categories, topic.trim()]);
    } else {
      toast(res.data?.detail || 'Ошибка при добавлении', 'error');
    }
  };

  return (
    <>
      <h1 className="page-title">Добавить вопрос</h1>
      <div className="card" style={{ maxWidth: 800 }}>
        {/* Topic */}
        <div className="form-group">
          <label className="form-label">Тема</label>
          <AutocompleteInput value={topic} onChange={setTopic} options={categories} placeholder="Введите или выберите тему" />
        </div>

        {/* Question text */}
        <div className="form-group">
          <label className="form-label">Текст вопроса</label>
          <textarea className="input" rows={3} value={questionText} onChange={e => setQuestionText(e.target.value)} placeholder="Текст вопроса..." />
        </div>

        {/* Matrices */}
        <div className="form-group">
          <label className="form-label">
            <input type="checkbox" checked={useMatrices} onChange={e => handleToggleMatrices(e.target.checked)} style={{ marginRight: 8 }} />
            Матрицы
          </label>
          {useMatrices && (
            <div className="ml-4">
              {matrices.map((mat, mi) => (
                <div key={mi} className="card" style={{ padding: '.75rem', marginBottom: '.5rem' }}>
                  <div className="flex items-center gap-sm mb-2">
                    <input className="input" style={{ width: 150 }} value={mat.name} onChange={e => { const m = [...matrices]; m[mi] = { ...m[mi], name: e.target.value }; setMatrices(m); }} />
                    <label className="text-sm text-secondary">Строки:</label>
                    <input type="number" className="input" style={{ width: 60 }} min={1} max={10} value={mat.rows} onChange={e => resizeMatrix(mi, +e.target.value, mat.cols)} />
                    <label className="text-sm text-secondary">Столбцы:</label>
                    <input type="number" className="input" style={{ width: 60 }} min={1} max={10} value={mat.cols} onChange={e => resizeMatrix(mi, mat.rows, +e.target.value)} />
                    <button className="btn btn-danger btn-sm" onClick={() => removeMatrix(mi)}><FiTrash2 size={14} /></button>
                  </div>
                  <table className="matrix-table">
                    <tbody>
                      {mat.data.map((row, ri) => (
                        <tr key={ri}>
                          {row.map((cell, ci) => (
                            <td key={ci}><input type="number" className="input" style={{ width: 60, textAlign: 'center' }} value={cell} onChange={e => updateMatrixCell(mi, ri, ci, +e.target.value)} /></td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ))}
              {matrices.length < 5 && <button className="btn btn-secondary btn-sm" onClick={addMatrix}><FiPlus size={14} /> Добавить матрицу</button>}
            </div>
          )}
        </div>

        {/* Commands */}
        <div className="form-group">
          <label className="form-label">
            <input type="checkbox" checked={useCommands} onChange={e => handleToggleCommands(e.target.checked)} style={{ marginRight: 8 }} />
            Команды
          </label>
          {useCommands && (
            <div className="ml-4 flex flex-col gap-sm">
              {commands.map((cmd, ci) => (
                <div key={ci} className="flex items-center gap-sm">
                  <input className="input" style={{ flex: 1 }} value={cmd} onChange={e => { const c = [...commands]; c[ci] = e.target.value; setCommands(c); }} placeholder={`Команда ${ci + 1}`} />
                  <button className="btn btn-danger btn-sm" onClick={() => removeCommand(ci)}><FiTrash2 size={14} /></button>
                </div>
              ))}
              {commands.length < 5 && <button className="btn btn-secondary btn-sm" onClick={addCommand}><FiPlus size={14} /> Добавить команду</button>}
            </div>
          )}
        </div>

        {/* Options */}
        <div className="form-group">
          <label className="form-label">Варианты ответа (мин. 2)</label>
          {options.map((opt, i) => (
            <div key={i} className="flex items-center gap-sm mb-2">
              <span className="option-letter-badge">{String.fromCharCode(65 + i)}</span>
              <input className="input" style={{ flex: 1 }} value={opt} onChange={e => { const o = [...options]; o[i] = e.target.value; setOptions(o); }} placeholder={`Вариант ${i + 1}`} />
            </div>
          ))}
        </div>

        {/* Answer type */}
        <div className="form-group">
          <label className="form-label">Тип ответа</label>
          <div className="flex gap-md">
            <label className="flex items-center gap-xs"><input type="radio" checked={answerType === 'single'} onChange={() => handleAnswerTypeChange('single')} /> Один ответ</label>
            <label className="flex items-center gap-xs"><input type="radio" checked={answerType === 'multiple'} onChange={() => handleAnswerTypeChange('multiple')} /> Несколько ответов</label>
          </div>
        </div>

        {/* Correct answer selection */}
        <div className="form-group">
          <label className="form-label">Правильный ответ</label>
          <div className="flex flex-col gap-xs">
            {validOptions.map((opt, i) => (
              <label key={i} className="flex items-center gap-xs">
                {answerType === 'single'
                  ? <input type="radio" name="correct" checked={correctSingle === opt} onChange={() => setCorrectSingle(opt)} />
                  : <input type="checkbox" checked={correctMultiple.includes(opt)} onChange={() => setCorrectMultiple(prev => prev.includes(opt) ? prev.filter(x => x !== opt) : [...prev, opt])} />
                }
                <span>{opt}</span>
              </label>
            ))}
          </div>
        </div>

        {/* Points */}
        <div className="form-group">
          <label className="form-label">Баллы</label>
          <input type="number" className="input" style={{ width: 100 }} min={1} max={100} value={points} onChange={e => setPoints(+e.target.value)} />
        </div>

        <button className="btn btn-primary" disabled={saving} onClick={handleSave}>
          <FiSave size={16} /> {saving ? 'Сохранение...' : 'Сохранить вопрос'}
        </button>
      </div>
    </>
  );
}
