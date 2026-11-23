import React from 'react';
import {
  FiAlertTriangle, FiAward, FiTrendingUp, FiTrendingDown, FiMinus,
  FiCheckCircle, FiTarget, FiBarChart2, FiUsers, FiClock,
} from 'react-icons/fi';

const LEVEL_META = {
  'начальный': { cls: 'badge-red', label: 'Начальный' },
  'базовый': { cls: 'badge-yellow', label: 'Базовый' },
  'уверенный': { cls: 'badge-blue', label: 'Уверенный' },
  'продвинутый': { cls: 'badge-green', label: 'Продвинутый' },
};

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

function fmtDate(value) {
  if (!value) return null;
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return String(value);
  return d.toLocaleString('ru-RU', {
    day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit',
  });
}

function levelBadge(level) {
  const meta = LEVEL_META[String(level || '').toLowerCase()];
  return { cls: meta?.cls || 'badge-blue', label: meta?.label || level || '—' };
}

function topicTone(percentage) {
  if (percentage >= 70) return 'ok';
  if (percentage >= 40) return 'mid';
  return 'low';
}

/** Строка сравнения «студент против группы» с дельтой. */
function CompareRow({ label, student, group, unit = '%' }) {
  const has = student != null && group != null;
  const delta = has ? Math.round((student - group) * 10) / 10 : null;
  const tone = delta == null || delta === 0 ? 'flat' : delta > 0 ? 'up' : 'down';
  return (
    <div className="compare-row">
      <span className="compare-label">{label}</span>
      <span className="compare-values">
        <span className="compare-student">{student != null ? `${student}${unit}` : '—'}</span>
        <span className="compare-vs">против группы</span>
        <span className="compare-group">{group != null ? `${group}${unit}` : '—'}</span>
      </span>
      {delta != null && delta !== 0 && (
        <span className={`compare-delta ${tone}`}>
          {delta > 0 ? '+' : ''}{delta}{unit}
        </span>
      )}
    </div>
  );
}

export default function StudentPortrait({ task, insights, insightsLoading = false }) {
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
  const topics = Array.isArray(facts.topics) ? facts.topics : [];

  const level = LEVEL_META[String(portrait.level || '').toLowerCase()]
    || { cls: 'badge-blue', label: portrait.level || 'Уровень не определён' };
  const risk = RISK_META[String(portrait.risk_of_failing || '').toLowerCase()];
  const dyn = DYNAMICS_META[String(portrait.dynamics || '').toLowerCase()];
  const delta = facts.dynamics?.delta;

  const source = meta.source;
  const isFallback = source && source !== 'llm';
  const generatedAt = meta.generated_at || meta.finished_at;

  const group = insights?.group || null;
  const history = Array.isArray(insights?.history) ? insights.history : [];
  const groupTopicMap = Object.fromEntries(
    (group?.topics || []).map((t) => [t.topic, t.percentage]),
  );

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
        {generatedAt && (
          <span className="portrait-date">
            <FiClock size={13} />
            {fmtDate(generatedAt)}
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

      {topics.length > 0 && (
        <div className="portrait-section">
          <div className="portrait-section-title portrait-title-row">
            <FiBarChart2 size={14} /> Разбивка по темам
          </div>
          {topics.map((t) => {
            const pct = Number(t.percentage) || 0;
            const groupPct = groupTopicMap[t.topic];
            const width = Math.min(100, Math.max(2, pct));
            return (
              <div className="topic-row" key={t.topic}>
                <div className="topic-head">
                  <span className="topic-name">{t.topic}</span>
                  <span className="topic-value">{pct}%</span>
                </div>
                <span className="topic-bar">
                  <span className={`topic-bar-fill ${topicTone(pct)}`} style={{ width: `${width}%` }} />
                  {groupPct != null && (
                    <span
                      className="topic-bar-group"
                      style={{ left: `${Math.min(100, Math.max(0, groupPct))}%` }}
                      title={`Средний по группе: ${groupPct}%`}
                    />
                  )}
                </span>
                {groupPct != null && (
                  <span className="topic-group-label">по группе: {groupPct}%</span>
                )}
              </div>
            );
          })}
        </div>
      )}

      {group && group.average_score != null && (
        <div className="portrait-section">
          <div className="portrait-section-title portrait-title-row">
            <FiUsers size={14} />
            Сравнение с группой{group.name ? `: ${group.name}` : ''}
            {group.size ? ` · ${group.size} чел.` : ''}
          </div>
          <CompareRow label="Средний балл" student={facts.average_score} group={group.average_score} />
          <CompareRow label="Доля зачётов" student={facts.pass_rate} group={group.pass_rate} />
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

      {history.length > 0 && (
        <div className="portrait-section">
          <div className="portrait-section-title portrait-title-row">
            <FiClock size={14} /> История портретов ({history.length})
          </div>
          <div className="portrait-history">
            {history.map((h, i) => {
              const prev = history[i - 1];
              const d = prev && prev.average_score != null && h.average_score != null
                ? Math.round((h.average_score - prev.average_score) * 10) / 10
                : null;
              const badge = levelBadge(h.level);
              return (
                <div className="history-item" key={h.input_hash || i}>
                  <span className="history-dot" />
                  <div className="history-body">
                    <div className="history-head">
                      <span className="history-date">{fmtDate(h.generated_at) || '—'}</span>
                      <span className={`badge ${badge.cls}`}>{badge.label}</span>
                      {h.average_score != null && <span className="history-score">{h.average_score}%</span>}
                      {d != null && d !== 0 && (
                        <span className={`history-delta ${d > 0 ? 'up' : 'down'}`}>
                          {d > 0 ? '+' : ''}{d}%
                        </span>
                      )}
                    </div>
                    <div className="history-sub">
                      {h.open_gaps != null && <span>проблемных вопросов: {h.open_gaps}</span>}
                      {h.pass_rate != null && <span> · зачётов: {h.pass_rate}%</span>}
                      {h.source && (
                        <span> · {h.source === 'llm' ? 'модель' : h.source === 'fallback' ? 'резерв' : h.source}</span>
                      )}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {insightsLoading && <p className="portrait-empty portrait-loading">Загружаю группу и историю…</p>}

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
