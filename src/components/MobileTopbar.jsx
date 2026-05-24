import React from 'react';
import { FiMenu, FiSun, FiMoon } from 'react-icons/fi';
import { useTheme } from '../context/ThemeContext';
import { useAuth } from '../context/AuthContext';

export default function MobileTopbar({ title, onMenu }) {
  const { theme, toggleTheme } = useTheme();
  const { user } = useAuth();
  const initials = (user?.full_name || user?.username || '')?.[0]?.toUpperCase();

  return (
    <div className="mobile-topbar">
      <button className="mobile-icon-btn" aria-label="Открыть меню" onClick={onMenu}>
        <FiMenu size={18} />
      </button>

      <div className="mobile-topbar-title">
        <div className="mobile-brand">Тестирование</div>
        {title && <div className="mobile-topbar-sub">{title}</div>}
      </div>

      <div className="mobile-topbar-actions">
        <button className="mobile-icon-btn" aria-label="Переключить тему" onClick={toggleTheme}>
          {theme === 'light' ? <FiMoon size={18} /> : <FiSun size={18} />}
        </button>
        {initials && <div className="mobile-avatar" title={user?.full_name || user?.username}>{initials}</div>}
      </div>
    </div>
  );
}
