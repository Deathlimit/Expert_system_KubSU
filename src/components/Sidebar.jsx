import React, { useEffect, useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { useTheme } from '../context/ThemeContext';
import { useNavigate, useLocation } from 'react-router-dom';
import { FiSun, FiMoon, FiLogOut, FiLock, FiX } from 'react-icons/fi';
import * as api from '../api';

export default function Sidebar({ links, isMobileOpen = false, onClose }) {
  const { user, logout } = useAuth();
  const { theme, toggleTheme } = useTheme();
  const navigate = useNavigate();
  const location = useLocation();
  const [showPwdModal, setShowPwdModal] = useState(false);

  const handleLogout = () => { logout(); navigate('/login'); };

  useEffect(() => {
    if (isMobileOpen && onClose) onClose();
    // Close mobile sidebar after route change
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [location.pathname]);

  const handleItemClick = (item) => {
    if (item.onClick) item.onClick();
    else if (item.path) navigate(item.path);
    if (onClose) onClose();
  };

  const roleLabels = { student: 'Студент', teacher: 'Преподаватель', admin: 'Администратор' };

  return (
    <nav className={`sidebar ${isMobileOpen ? 'sidebar-mobile-open' : ''}`}>
      <div className="sidebar-brand-row">
        <div className="sidebar-brand">
          <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M12 2L2 7l10 5 10-5-10-5z"/>
            <path d="M2 17l10 5 10-5"/>
            <path d="M2 12l10 5 10-5"/>
          </svg>
          Тестирование
        </div>
        <button
          className="sidebar-close"
          aria-label="Закрыть меню"
          onClick={() => onClose?.()}
        >
          <FiX size={18} />
        </button>
      </div>

      {links.map((section, si) => (
        <React.Fragment key={si}>
          {section.label && <div className="sidebar-section-label">{section.label}</div>}
          {section.items.map((item) => (
            <button
              key={item.path || item.id}
              className={`sidebar-link ${item.active != null ? (item.active ? 'active' : '') : (item.path && location.pathname.startsWith(item.path) ? 'active' : '')}`}
              onClick={() => handleItemClick(item)}
            >
              {item.icon} {item.text}
            </button>
          ))}
        </React.Fragment>
      ))}

      <div className="sidebar-spacer" />

      <button className="sidebar-link" onClick={() => setShowPwdModal(true)}>
        <FiLock size={18} /> Сменить пароль
      </button>

      <button className="sidebar-link" onClick={toggleTheme}>
        {theme === 'light' ? <FiMoon size={18} /> : <FiSun size={18} />}
        {theme === 'light' ? 'Тёмная тема' : 'Светлая тема'}
      </button>

      <button className="sidebar-link" onClick={handleLogout}>
        <FiLogOut size={18} /> Выйти
      </button>

      <div className="sidebar-user">
        <div className="sidebar-user-avatar">{(user?.full_name || user?.username)?.[0]?.toUpperCase()}</div>
        <div className="sidebar-user-info">
          <div className="sidebar-user-name">{user?.full_name || user?.username}</div>
          <div className="sidebar-user-role">{roleLabels[user?.role] || user?.role}</div>
        </div>
      </div>

      {showPwdModal && <SidebarPasswordModal username={user?.username} onClose={() => setShowPwdModal(false)} />}
    </nav>
  );
}

function SidebarPasswordModal({ username, onClose }) {
  const [oldPwd, setOldPwd] = useState('');
  const [newPwd, setNewPwd] = useState('');
  const [msg, setMsg] = useState('');
  const [err, setErr] = useState('');
  const [saving, setSaving] = useState(false);

  const handleSave = async () => {
    setMsg(''); setErr('');
    if (!oldPwd || !newPwd) { setErr('Заполните оба поля'); return; }
    if (newPwd.length < 6) { setErr('Мин. 6 символов'); return; }
    setSaving(true);
    const res = await api.changePassword(username, oldPwd, newPwd);
    setSaving(false);
    if (res.ok) { setMsg('Пароль изменён'); setTimeout(onClose, 1000); }
    else setErr(res.data?.detail || 'Ошибка');
  };

  return (
    <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,.5)', zIndex: 9999, display: 'flex', alignItems: 'center', justifyContent: 'center' }} onClick={onClose}>
      <div className="card" style={{ minWidth: 320, maxWidth: 400 }} onClick={e => e.stopPropagation()}>
        <h3 style={{ marginBottom: '.75rem' }}>Сменить пароль</h3>
        {err && <div className="toast toast-error" style={{ marginBottom: 8 }}>{err}</div>}
        {msg && <div className="toast toast-success" style={{ marginBottom: 8 }}>{msg}</div>}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          <input className="input" type="password" placeholder="Текущий пароль" value={oldPwd} onChange={e => setOldPwd(e.target.value)} />
          <input className="input" type="password" placeholder="Новый пароль" value={newPwd} onChange={e => setNewPwd(e.target.value)} />
          <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
            <button className="btn btn-secondary btn-sm" onClick={onClose}>Отмена</button>
            <button className="btn btn-primary btn-sm" disabled={saving} onClick={handleSave}>Сохранить</button>
          </div>
        </div>
      </div>
    </div>
  );
}
