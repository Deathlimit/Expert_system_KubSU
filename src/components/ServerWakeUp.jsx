import React, { useState, useEffect } from 'react';

export default function ServerWakeUp() {
  const [visible, setVisible] = useState(false);
  const [seconds, setSeconds] = useState(0);

  useEffect(() => {
    const show = () => { setVisible(true); setSeconds(0); };
    const hide = () => setVisible(false);
    window.addEventListener('server-waking-up', show);
    window.addEventListener('server-ready', hide);
    return () => {
      window.removeEventListener('server-waking-up', show);
      window.removeEventListener('server-ready', hide);
    };
  }, []);

  useEffect(() => {
    if (!visible) return;
    const id = setInterval(() => setSeconds((s) => s + 1), 1000);
    return () => clearInterval(id);
  }, [visible]);

  if (!visible) return null;

  return (
    <div className="wakeup-overlay">
      <div className="wakeup-card">
        <div className="wakeup-spinner" />
        <h3>Сервер просыпается…</h3>
        <p>Обычно это занимает 1–2 минуты.<br/>Пожалуйста, не закрывайте страницу.</p>
        <span className="wakeup-timer">{seconds} сек.</span>
      </div>
    </div>
  );
}
