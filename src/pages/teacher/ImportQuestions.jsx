import React, { useState } from 'react';
import { useToast } from '../../components/Toast';
import * as api from '../../api';
import { FiUpload, FiHelpCircle, FiCopy, FiCheck } from 'react-icons/fi';

const EXAMPLE_QUESTIONS = [
  {
    "topic": "Линейная алгебра",
    "question": "Чему равен определитель матрицы [[1, 2], [3, 4]]?",
    "options": ["-2", "10", "0", "-1"],
    "correct": "-2",
    "answer_type": "single",
    "points": 2
  },
  {
    "topic": "Линейная алгебра",
    "question": "Какие из данных матриц являются единичными?",
    "options": ["A", "B", "C", "D"],
    "correct": ["A", "C"],
    "answer_type": "multiple",
    "points": 3,
    "matrices": {
      "A": [[1, 0], [0, 1]],
      "B": [[1, 1], [1, 1]],
      "C": [[1, 0, 0], [0, 1, 0], [0, 0, 1]],
      "D": [[0, 1], [1, 0]]
    }
  },
  {
    "topic": "Программирование",
    "question": "Вычислите результат выполнения команды: len([1, [2, 3], 4])",
    "options": ["3", "4", "5", "Ошибка"],
    "correct": "3",
    "answer_type": "single",
    "commands": ["len([1, [2, 3], 4])"]
  }
];

export default function ImportQuestions() {
  const toast = useToast();
  const [jsonText, setJsonText] = useState('');
  const [importing, setImporting] = useState(false);
  const [result, setResult] = useState(null);
  const [showHelp, setShowHelp] = useState(false);
  const [copied, setCopied] = useState(false);

  const handleCopyExample = () => {
    navigator.clipboard.writeText(JSON.stringify(EXAMPLE_QUESTIONS, null, 2));
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
    toast('Пример скопирован в буфер обмена', 'success');
  };

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
      <div className="flex items-center" style={{ marginBottom: 24 }}>
        <h1 className="page-title" style={{ marginBottom: 0 }}>Импорт вопросов из JSON</h1>
        <button className="btn btn-ghost btn-sm" onClick={() => setShowHelp(!showHelp)} title="Формат данных" style={{ marginLeft: 8 }}>
          <FiHelpCircle size={18} />
        </button>
      </div>

      {showHelp && (
        <div className="card mb-4" style={{ background: 'var(--bg-secondary)', border: '1px solid var(--border)' }}>
          <div className="flex items-center justify-between mb-2">
            <h3 className="text-sm" style={{ margin: 0 }}>Формат данных</h3>
            <button className="btn btn-primary btn-sm" onClick={handleCopyExample}>
              {copied ? <FiCheck size={14} /> : <FiCopy size={14} />} {copied ? 'Скопировано' : 'Копировать пример'}
            </button>
          </div>
          <div className="text-sm" style={{ lineHeight: 1.6 }}>
            <p><strong>Обязательные поля:</strong></p>
            <ul style={{ margin: '0 0 1rem 1.25rem', padding: 0 }}>
              <li><code>topic</code> — тема вопроса (строка)</li>
              <li><code>question</code> — текст вопроса (строка)</li>
              <li><code>options</code> — варианты ответа (массив строк, мин. 2)</li>
              <li><code>correct</code> — правильный ответ (строка для single, массив для multiple)</li>
            </ul>
            <p><strong>Опциональные поля:</strong></p>
            <ul style={{ margin: '0 0 1rem 1.25rem', padding: 0 }}>
              <li><code>answer_type</code> — тип ответа: <code>"single"</code> (по умолчанию) или <code>"multiple"</code></li>
              <li><code>points</code> — баллы за вопрос (число, по умолчанию 1)</li>
              <li><code>matrices</code> — матрицы (объект с именами и данными)</li>
              <li><code>commands</code> — команды для отображения (массив строк)</li>
            </ul>
            <p><strong>Пример JSON:</strong></p>
          </div>
          <pre style={{ 
            background: 'var(--bg-input)', 
            padding: '.75rem', 
            borderRadius: 6, 
            fontSize: '.8rem', 
            overflow: 'auto',
            maxHeight: 300,
            margin: 0
          }}>
{JSON.stringify(EXAMPLE_QUESTIONS, null, 2)}
          </pre>
        </div>
      )}

      <div className="card mb-4">
        <p className="text-sm text-secondary mb-2">
          Загрузите JSON-файл или вставьте JSON. Формат: массив объектов.
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
