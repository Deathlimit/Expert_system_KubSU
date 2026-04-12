import React, { useState, useEffect, useRef, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { ToastProvider, useToast } from '../../components/Toast';
import * as api from '../../api';
import { FiChevronLeft, FiChevronRight, FiCheck, FiClock, FiArrowLeft } from 'react-icons/fi';

/* ── localStorage helpers for session persistence ── */
const SAVE_KEY_PREFIX = 'tes_active_session_';
function saveSessionState(username, state) {
  try { localStorage.setItem(SAVE_KEY_PREFIX + username, JSON.stringify(state)); } catch {}
}
function loadSessionState(username) {
  try { const raw = localStorage.getItem(SAVE_KEY_PREFIX + username); return raw ? JSON.parse(raw) : null; } catch { return null; }
}
function clearSessionState(username) {
  try { localStorage.removeItem(SAVE_KEY_PREFIX + username); } catch {}
}

function TestTakingContent() {
  const { testId } = useParams();
  const { user } = useAuth();
  const navigate = useNavigate();
  const toast = useToast();

  const [sessionId, setSessionId] = useState(null);
  const [question, setQuestion] = useState(null);
  const [totalQuestions, setTotalQuestions] = useState(0);
  const [selected, setSelected] = useState(null);
  const [finished, setFinished] = useState(false);
  const [results, setResults] = useState(null);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [secondsRemaining, setSecondsRemaining] = useState(null);
  const timerRef = useRef(null);

  /* ── Navigation / review state (like desktop) ── */
  const [qBuffer, setQBuffer] = useState([]);       // list of question dicts from API
  const [aBuffer, setABuffer] = useState([]);       // submitted answers (parallel)
  const [frontierIdx, setFrontierIdx] = useState(-1); // index of the last question from API
  const [currentNavIdx, setCurrentNavIdx] = useState(0);
  const inReviewMode = currentNavIdx < frontierIdx;

  /* ── Start or resume test ── */
  const startTest = useCallback(async () => {
    setLoading(true);
    // Try to resume a saved session
    const saved = loadSessionState(user.username);
    if (saved && saved.test_id === testId && saved.session_id) {
      const status = await api.getSessionStatus(saved.session_id);
      if (status.ok && status.data?.current_index === saved.frontier_idx) {
        // Restore session
        setSessionId(saved.session_id);
        setQBuffer(saved.q_buffer || []);
        setABuffer(saved.a_buffer || []);
        setFrontierIdx(saved.frontier_idx);
        setTotalQuestions(saved.total_questions || 0);
        const fq = (saved.q_buffer || [])[saved.frontier_idx];
        if (fq) {
          setQuestion(fq);
          setCurrentNavIdx(saved.frontier_idx);
          if (fq.seconds_remaining != null) setSecondsRemaining(fq.seconds_remaining);
        }
        setLoading(false);
        return;
      } else {
        clearSessionState(user.username);
      }
    }

    const res = await api.startSession(testId);
    if (res.ok) {
      const sid = res.data.session_id;
      const total = res.data.total_questions || res.data.current_question?.total_questions || 0;
      const q = res.data.current_question;
      setSessionId(sid);
      setTotalQuestions(total);
      setQBuffer([q]);
      setABuffer([]);
      setFrontierIdx(0);
      setCurrentNavIdx(0);
      applyQuestion(q);
      // Save initial state
      saveSessionState(user.username, {
        session_id: sid, test_id: testId, total_questions: total,
        frontier_idx: 0, q_buffer: [q], a_buffer: [],
      });
    } else {
      toast(res.data?.detail || 'Не удалось начать тест', 'error');
      navigate('/student');
    }
    setLoading(false);
  }, [testId, user.username]);

  useEffect(() => { startTest(); }, [startTest]);

  /* ── Timer ── */
  useEffect(() => {
    if (secondsRemaining != null && secondsRemaining > 0 && !timerRef.current) {
      timerRef.current = setInterval(() => {
        setSecondsRemaining(prev => {
          if (prev <= 1) { clearInterval(timerRef.current); timerRef.current = null; return 0; }
          return prev - 1;
        });
      }, 1000);
    }
    return () => { clearInterval(timerRef.current); timerRef.current = null; };
  }, [sessionId, secondsRemaining]);

  /* ── Auto-submit on timeout (like desktop) ── */
  useEffect(() => {
    if (secondsRemaining === 0 && sessionId && !finished) {
      handleTimeout();
    }
  }, [secondsRemaining]);

  const handleTimeout = async () => {
    if (!sessionId) return;
    clearInterval(timerRef.current);
    const res = await api.submitAnswer(sessionId, '');
    if (res.ok && res.data?.finished) {
      setFinished(true);
      setResults(res.data.results);
      clearSessionState(user.username);
      toast('Время вышло. Тест завершён автоматически.', 'error');
    } else {
      // Session may have already been finished server-side; check status
      const status = await api.getSessionStatus(sessionId);
      if (status.ok && status.data?.results) {
        setFinished(true);
        setResults(status.data.results);
        clearSessionState(user.username);
        toast('Время вышло. Тест завершён автоматически.', 'error');
      } else {
        clearSessionState(user.username);
        toast('Время вышло. Не удалось получить результат.', 'error');
        navigate('/student');
      }
    }
  };

  const applyQuestion = (q) => {
    if (!q) return;
    setQuestion(q);
    if (q.seconds_remaining != null) setSecondsRemaining(q.seconds_remaining);
    if (q.total_questions) setTotalQuestions(q.total_questions);
    setSelected(null);
  };

  /* ── Answer selection ── */
  const handleSelect = (option) => {
    if (!question || inReviewMode) return;
    if (question.answer_type === 'multiple') {
      setSelected(prev => {
        const arr = Array.isArray(prev) ? [...prev] : [];
        if (arr.includes(option)) return arr.filter(o => o !== option);
        return [...arr, option];
      });
    } else {
      setSelected(option);
    }
  };

  /* ── Submit answer ── */
  const handleSubmitAnswer = async () => {
    // In review mode, just navigate forward
    if (inReviewMode) {
      navigateToQuestion(currentNavIdx + 1);
      return;
    }

    if (!sessionId || selected == null || (Array.isArray(selected) && selected.length === 0)) {
      toast('Выберите ответ', 'error');
      return;
    }
    setSubmitting(true);
    const res = await api.submitAnswer(sessionId, selected);
    if (res.ok) {
      const newABuffer = [...aBuffer, selected];
      setABuffer(newABuffer);
      if (res.data.finished) {
        clearInterval(timerRef.current);
        setFinished(true);
        setResults(res.data.results);
        clearSessionState(user.username);
      } else {
        const nextQ = res.data.current_question;
        const newQBuffer = [...qBuffer, nextQ];
        const newFrontier = newQBuffer.length - 1;
        setQBuffer(newQBuffer);
        setFrontierIdx(newFrontier);
        setCurrentNavIdx(newFrontier);
        setQuestion(nextQ);
        applyQuestion(nextQ);
        // Save intermediate state
        saveSessionState(user.username, {
          session_id: sessionId, test_id: testId, total_questions: totalQuestions,
          frontier_idx: newFrontier, q_buffer: newQBuffer, a_buffer: newABuffer,
        });
      }
    } else {
      toast(res.data?.detail || 'Ошибка при отправке ответа', 'error');
    }
    setSubmitting(false);
  };

  /* ── Navigation between questions ── */
  const navigateToQuestion = (idx) => {
    if (idx < 0 || idx >= qBuffer.length) return;
    const q = qBuffer[idx];
    setCurrentNavIdx(idx);
    setQuestion(q);
    if (idx === frontierIdx) {
      // Active frontier question
      setSelected(null);
    } else {
      // Review mode — show submitted answer
      const submittedAnswer = aBuffer[idx] ?? null;
      setSelected(submittedAnswer);
    }
  };

  const fmtTime = (s) => {
    if (s == null) return null;
    const m = Math.floor(s / 60);
    const sec = s % 60;
    return `${m}:${sec.toString().padStart(2, '0')}`;
  };

  if (loading) {
    return <div className="page-layout"><main className="main-content" style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '60vh' }}><p className="text-secondary">Загрузка теста...</p></main></div>;
  }

  if (finished && results) {
    const isPassed = results.final_status === 'Зачёт' || results.final_status === 'Passed';
    return (
      <div className="page-layout">
        <main className="main-content" style={{ maxWidth: 600, margin: '0 auto', padding: '4rem 1.5rem', textAlign: 'center' }}>
          <h1 className="page-title">Тест завершён</h1>
          <div className="card" style={{ padding: '2.5rem', textAlign: 'center' }}>
            <div style={{
              fontSize: '3.5rem',
              marginBottom: '0.75rem',
            }}>
              {isPassed ? '✅' : '❌'}
            </div>
            <div style={{
              fontSize: '2.2rem', fontWeight: 700,
              color: isPassed ? 'var(--bg-success)' : 'var(--bg-danger)',
              marginBottom: '0.5rem',
            }}>
              {results.final_status}
            </div>
            <div className="text-secondary" style={{ fontSize: '1rem', marginBottom: '1.5rem' }}>
              {results.status_message || results.status}
            </div>
            <div style={{ display: 'flex', justifyContent: 'center', gap: '2.5rem', flexWrap: 'wrap' }}>
              <div>
                <div className="text-secondary" style={{ fontSize: '.8rem', marginBottom: 4 }}>Балл</div>
                <div style={{ fontSize: '1.6rem', fontWeight: 700 }}>{results.score_percentage?.toFixed(1)}%</div>
              </div>
              <div>
                <div className="text-secondary" style={{ fontSize: '.8rem', marginBottom: 4 }}>Длительность</div>
                <div style={{ fontSize: '1.6rem', fontWeight: 700 }}>{results.duration || '—'}</div>
              </div>
            </div>
          </div>
          <div style={{ marginTop: '1.5rem' }}>
            <button className="btn btn-primary" onClick={() => navigate('/student')}>
              <FiArrowLeft size={16} /> К списку тестов
            </button>
          </div>
        </main>
      </div>
    );
  }

  const isAdditional = question?.is_additional;
  const questionPrefix = isAdditional ? 'Дополнительный вопрос' : 'Вопрос';

  return (
    <div className="page-layout">
      <main className="main-content" style={{ maxWidth: 800, margin: '0 auto', padding: '2rem 1.5rem' }}>
        {/* Header */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
          <div>
            <span className="text-secondary text-sm">{questionPrefix}</span>
            <span style={{ fontSize: '1.4rem', fontWeight: 700, marginLeft: 8 }}>{currentNavIdx + 1} / {totalQuestions}</span>
          </div>
          {secondsRemaining != null && (
            <div className={`timer-badge ${secondsRemaining <= 60 ? 'timer-danger' : secondsRemaining <= 180 ? 'timer-warning' : ''}`}>
              <FiClock size={16} />
              <span style={{ fontWeight: 600 }}>{fmtTime(secondsRemaining)}</span>
            </div>
          )}
        </div>

        {/* Review mode indicator */}
        {inReviewMode && (
          <div style={{ padding: '.5rem 1rem', borderRadius: 8, background: 'rgba(255,165,0,.1)', border: '1px solid rgba(255,165,0,.3)', marginBottom: '1rem', fontSize: '.9rem', color: 'orange', fontStyle: 'italic' }}>
            Просмотр вопроса {currentNavIdx + 1} — ответ уже отправлен
          </div>
        )}

        {/* Progress bar */}
        <div className="progress-bar" style={{ marginBottom: '1.5rem' }}>
          <div className="progress-bar-fill" style={{ width: `${((frontierIdx >= 0 ? frontierIdx : 0) / totalQuestions) * 100}%` }} />
        </div>

        {/* Question card */}
        <div className="card question-card">
          <div className="question-text">{question?.question}</div>

          {question?.matrices && Object.keys(question.matrices).length > 0 && (
            <div className="matrix-container">
              {Object.entries(question.matrices).map(([name, matrixData], mi) => (
                <div key={mi} className="matrix-block">
                  {name && <div className="text-sm text-secondary" style={{ marginBottom: 4 }}>{name}</div>}
                  <table className="matrix-table">
                    <tbody>
                      {(Array.isArray(matrixData) ? matrixData : []).map((row, ri) => (
                        <tr key={ri}>
                          {(Array.isArray(row) ? row : []).map((cell, ci) => (
                            <td key={ci}>{cell}</td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ))}
            </div>
          )}

          {question?.commands && question.commands.length > 0 && (
            <div className="commands-container">
              {question.commands.map((cmd, ci) => (
                <div key={ci} className="command-block">{cmd}</div>
              ))}
            </div>
          )}

          <div className="text-sm text-secondary" style={{ marginBottom: '.75rem' }}>
            {question?.answer_type === 'multiple' ? 'Выберите один или несколько вариантов' : 'Выберите один вариант'}
          </div>

          <div className="options-list">
            {(question?.options || []).map((opt, idx) => {
              const isSelected = question?.answer_type === 'multiple'
                ? (Array.isArray(selected) && selected.includes(opt))
                : selected === opt;
              return (
                <button
                  key={idx}
                  className={`option-btn ${isSelected ? 'option-btn-selected' : ''} ${inReviewMode ? 'option-btn-disabled' : ''}`}
                  onClick={() => handleSelect(opt)}
                  disabled={inReviewMode}
                >
                  <span className="option-letter">{String.fromCharCode(65 + idx)}</span>
                  <span className="option-text">{opt}</span>
                  {isSelected && <FiCheck className="option-check" size={18} />}
                </button>
              );
            })}
          </div>
        </div>

        {/* Nav buttons */}
        <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '1.5rem' }}>
          <button
            className="btn btn-secondary"
            disabled={currentNavIdx <= 0}
            onClick={() => navigateToQuestion(currentNavIdx - 1)}
          >
            <FiChevronLeft size={18} /> Назад
          </button>
          <button
            className="btn btn-primary"
            disabled={!inReviewMode && (submitting || selected == null || (Array.isArray(selected) && selected.length === 0))}
            onClick={handleSubmitAnswer}
          >
            {submitting ? 'Отправка...' : inReviewMode ? 'Вперёд' : (frontierIdx === totalQuestions - 1 ? 'Завершить тест' : 'Следующий вопрос')}
            {!submitting && <FiChevronRight size={18} />}
          </button>
        </div>

        {/* Question dots — clickable navigation */}
        <div className="question-dots" style={{ marginTop: '1.5rem' }}>
          {Array.from({ length: totalQuestions }, (_, i) => {
            const isCurrent = i === currentNavIdx;
            const isAnswered = i < frontierIdx;
            const isFrontier = i === frontierIdx && !isCurrent;
            const isAccessible = i <= frontierIdx;
            return (
              <div
                key={i}
                className={`q-dot ${isCurrent ? 'q-dot-current' : ''} ${isAnswered ? 'q-dot-answered' : ''} ${isFrontier ? 'q-dot-frontier' : ''} ${isAccessible ? 'q-dot-clickable' : ''}`}
                title={`Вопрос ${i + 1}`}
                onClick={() => isAccessible && navigateToQuestion(i)}
                style={{ cursor: isAccessible ? 'pointer' : 'default' }}
              >
                {i + 1}
              </div>
            );
          })}
        </div>
      </main>
    </div>
  );
}

export default function TestTaking() {
  return <ToastProvider><TestTakingContent /></ToastProvider>;
}
