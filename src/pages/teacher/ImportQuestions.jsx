import React, { useState } from 'react';
import { useToast } from '../../components/Toast';
import * as api from '../../api';
import { FiUpload } from 'react-icons/fi';

export default function ImportQuestions() {
  const toast = useToast();
  const [jsonText, setJsonText] = useState('');
  const [importing, setImporting] = useState(false);
  const [result, setResult] = useState(null);

  const handleFileUpload = (e) => {
    const file = e.target.files[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = (ev) => setJsonText(ev.target.result);
    reader.readAsText(file);
  };

  const handleImport = async () => {
    let parsed;
    try {
      parsed = JSON.parse(jsonText);
    } catch {
      toast('Невалидный JSON', 'error');
      return;
    }
    const questions = Array.isArray(parsed) ? parsed : (parsed.questions || []);
    if (!questions.length) { toast('Нет вопросов для импорта', 'error'); return; }
    setImporting(true);
    const res = await api.bulkImportQuestions(questions);
    setImporting(false);
    if (res.ok) {
      setResult(res.data);
      toast(`Импортировано: ${res.data.imported}`, 'success');
    } else {
      toast(res.data?.detail || 'Ошибка импорта', 'error');
    }
  };

  return (
    <>
      <h1 className="page-title">Импорт вопросов из JSON</h1>
      <div className="card mb-4">
        <p className="text-sm text-secondary mb-2">
          Загрузите JSON-файл или вставьте JSON. Формат: массив объектов с полями: topic, question, options, correct, answer_type (опционально).
        </p>
        <input type="file" accept=".json" onChange={handleFileUpload} className="mb-2" />
        <textarea
          className="input"
          rows={12}
          placeholder='[{"topic": "...", "question": "...", "options": ["A", "B", "C"], "correct": "A"}]'
          value={jsonText}
          onChange={e => setJsonText(e.target.value)}
          style={{ fontFamily: 'monospace', fontSize: '.85rem' }}
        />
        <button className="btn btn-primary mt-2" disabled={importing || !jsonText.trim()} onClick={handleImport}>
          <FiUpload size={14} /> Импортировать
        </button>
      </div>
      {result && (
        <div className="card">
          <div className="badge badge-green mb-2">Импортировано: {result.imported}</div>
          {result.errors && result.errors.length > 0 && (
            <div className="mt-2">
              <h4 className="text-sm" style={{ marginBottom: '.25rem' }}>Ошибки:</h4>
              {result.errors.map((e, i) => <p key={i} className="text-sm text-secondary">{e}</p>)}
            </div>
          )}
        </div>
      )}
    </>
  );
}
