import React from 'react';
import {
  FiAlertTriangle, FiAward, FiTrendingUp, FiTrendingDown, FiMinus,
  FiCheckCircle, FiTarget,
} from 'react-icons/fi';

const LEVEL_META = {
  'начальный': { cls: 'badge-red', label: 'Начальный' },
  'базовый': { cls: 'badge-yellow', label: 'Базовый' },
  'уверенный': { cls: 'badge-blue', label: 'Уверенный' },
  'продвинутый': { cls: 'badge-green', label: 'Продвинутый' },
};

/** Краткие сведения о портрете для таблицы: уровень и средний балл. */
export function portraitBrief(result) {
  const data = unwrap(result);
  if (!data) return null;
  const key = String(data.portrait?.level || '').toLowerCase();
  return {
    level: LEVEL_META[key]?.label || data.portrait?.level || null,
    levelCls: LEVEL_META[key]?.cls || 'badge-blue',
    average: data.facts?.average_score,
  };
}

const RISK_META = {
  'высокий': { cls: 'badge-red', label: 'Высокий риск незачёта' },
  'средний': { cls: 'badge-yellow', label: 'Средний риск незачёта' },
  'низкий': { cls: 'badge-green', label: 'Низкий риск незачёта' },
};

const SEVERITY_META = {
  'высокий': { cls: 'badge-red', tone: 'sev-high', weight: 3 },
  'средний': { cls: 'badge-yellow', tone: 'sev-medium', weight: 2 },
  'низкий': { cls: 'badge-blue', tone: 'sev-low', weight: 1 },
};

const DYNAMICS_META = {
  'рост': { icon: <FiTrendingUp size={14} />, color: 'var(--bg-success)', label: 'Рост' },
  'падение': { icon: <FiTrendingDown size={14} />, color: 'var(--bg-danger)', label: 'Падение' },
  'стабильно': { icon: <FiMinus size={14} />, color: 'var(--text-secondary)', label: 'Стабильно' },
  'недостаточно данных': { icon: <FiMinus size={14} />, color: 'var(--text-secondary)', label: 'Недостаточно данных' },
};

/**
 * Задача хранит результат в виде { portrait, facts, source, model, ... }.
 * Старые задачи могли класть сам портрет без обёртки — поддерживаем оба вида.
 */
function unwrap(result) {
  if (!result || typeof result !== 'object') return null;
  if (result.portrait && typeof result.portrait === 'object') {
    return { portrait: result.portrait, facts: result.facts || {}, meta: result };
  }
  return { portrait: result, facts: {}, meta: {} };
}

export default function StudentPortrait({ task }) {
  const data = unwrap(task?.result);
  if (!data) return <p className="portrait-empty">Результат ещё не готов.</p>;

  const { portrait, facts, meta } = data;

  // Пробелы: сначала высокие по важности, внутри одной важности — по уверенности.
  const gaps = Array.isArray(portrait.gaps) ? [...portrait.gaps] : [];
  gaps.sort(
    (a, b) =>
      (SEVERITY_META[String(b?.severity || '').toLowerCase()]?.weight || 0) -
        (SEVERITY_META[String(a?.severity || '').toLowerCase()]?.weight || 0) ||
      (b?.confidence || 0) - (a?.confidence || 0),
  );

  const strengths = Array.isArray(portrait.strengths) ? portrait.strengths : [];
  const recommendations = Array.isArray(portrait.recommendations) ? portrait.recommendations : [];

  const level = LEVEL_META[String(portrait.level || '').toLowerCase()]
    || { cls: 'badge-blue', label: portrait.level || 'Уровень не определён' };
  const risk = RISK_META[String(portrait.risk_of_failing || '').toLowerCase()];
  const dyn = DYNAMICS_META[String(portrait.dynamics || '').toLowerCase()];
  const delta = facts.dynamics?.delta;

  const source = meta.source;
  const isFallback = source && source !== 'llm';

  const stats = [
    facts.average_score != null && { label: 'Средний балл', value: `${facts.average_score}%` },
    facts.pass_rate != null && { label: 'Зачётов', value: `${facts.pass_rate}%` },
    facts.attempts != null && { label: 'Попыток', value: facts.attempts },
    facts.open_gaps != null && { label: 'Проблемных вопросов', value: facts.open_gaps },
    facts.closed_gaps != null && { label: 'Исправлено', value: facts.closed_gaps },
    facts.persistent_gaps != null && { label: 'Устойчивых', value: facts.persistent_gaps },
    facts.average_duration_seconds != null && {
      label: 'Ср. время',
      value: `${Math.max(1, Math.round(facts.average_duration_seconds / 60))} мин`,
    },
  ].filter(Boolean);

  const period = facts.period?.first && facts.period?.last
    ? `${facts.period.first} — ${facts.period.last}`
    : null;

  return (
    <div>
      {isFallback && (
        <div className="portrait-warning">
          <FiAlertTriangle size={16} />
          <span>Резервный расчёт: модель недоступна, профиль построен по статистике.</span>
        </div>
      )}

      <div className="portrait-head">
        <span className={`badge ${level.cls}`}>
          <FiAward size={13} style={{ marginRight: 4 }} />
          {level.label}
        </span>
        {risk && (
          <span className={`badge ${risk.cls}`}>
            <FiAlertTriangle size={13} style={{ marginRight: 4 }} />
            {risk.label}
          </span>
        )}
        {dyn && (
          <span className="portrait-dynamics" style={{ color: dyn.color }}>
            {dyn.icon}
            {dyn.label}
            {delta != null && delta !== 0 && (portrait.dynamics === 'рост' || portrait.dynamics === 'падение')
              ? ` (${delta > 0 ? '+' : ''}${delta})`
              : ''}
          </span>
        )}
      </div>

      {portrait.summary && <p className="portrait-summary">{portrait.summary}</p>}

      {stats.length > 0 && (
        <div className="portrait-stats">
          {stats.map((s) => (
            <div className="portrait-stat" key={s.label}>
              <div className="portrait-stat-value">{s.value}</div>
              <div className="portrait-stat-label">{s.label}</div>
            </div>
          ))}
        </div>
      )}

      {strengths.length > 0 && (
        <div className="portrait-section">
          <div className="portrait-section-title">Сильные стороны</div>
          <div className="portrait-chips">
            {strengths.map((text, i) => (
              <span className="portrait-chip" key={i}>{text}</span>
            ))}
          </div>
        </div>
      )}

      <div className="portrait-section">
        <div className="portrait-section-title">
          Пробелы{gaps.length > 0 ? `: областей — ${gaps.length}` : ''}
        </div>
        {gaps.length === 0 ? (
          <p className="portrait-empty portrait-ok">
            <FiCheckCircle size={15} /> Значимых пробелов не выявлено.
          </p>
        ) : (
          gaps.map((gap, i) => {
            const sev = SEVERITY_META[String(gap.severity || '').toLowerCase()] || SEVERITY_META['средний'];
            const confidence = Math.round((gap.confidence || 0) * 100);
            return (
              <div className={`portrait-gap ${sev.tone}`} key={i}>
                <div className="portrait-gap-head">
                  <span className="portrait-gap-area">{gap.area || 'Без названия'}</span>
                  <span className={`badge ${sev.cls}`}>{gap.severity || 'средний'}</span>
                </div>
                {confidence > 0 && (
                  <div className="portrait-confidence">
                    <span>Уверенность</span>
                    <span className="portrait-confidence-bar">
                      <span style={{ width: `${confidence}%` }} />
                    </span>
                    <span>{confidence}%</span>
                  </div>
                )}
                {Array.isArray(gap.evidence) && gap.evidence.length > 0 && (
                  <ul className="portrait-evidence">
                    {gap.evidence.map((item, j) => <li key={j}>{item}</li>)}
                  </ul>
                )}
                {gap.recommendation && (
                  <div className="portrait-reco">
                    <strong>Что делать: </strong>{gap.recommendation}
                  </div>
                )}
              </div>
            );
          })
        )}
      </div>

      {recommendations.length > 0 && (
        <div className="portrait-section">
          <div className="portrait-section-title portrait-title-row">
            <FiTarget size={14} /> Рекомендации
          </div>
          <ol className="portrait-recos">
            {recommendations.map((text, i) => <li key={i}>{text}</li>)}
          </ol>
        </div>
      )}

      {(period || facts.total_answers != null || meta.model || source) && (
        <div className="portrait-meta">
          {period && <span>Период: {period}</span>}
          {facts.total_answers != null && <span>Ответов: {facts.total_answers}</span>}
          {meta.model && <span>Модель: {meta.model}</span>}
          {source && <span>Источник: {source === 'llm' ? 'модель' : source === 'fallback' ? 'резерв' : source}</span>}
        </div>
      )}
    </div>
  );
}
