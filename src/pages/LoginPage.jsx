import React, { useState, useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { useTheme } from '../context/ThemeContext';
import { FiSun, FiMoon } from 'react-icons/fi';
import * as api from '../api';

export default function LoginPage() {
  const { user, loginUser, registerUser } = useAuth();
  const { theme, toggleTheme } = useTheme();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const [isRegister, setIsRegister] = useState(searchParams.get('mode') === 'register');
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [fullName, setFullName] = useState('');
  const [group, setGroup] = useState('');
  const [groups, setGroups] = useState([]);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (isRegister) {
      api.getAllGroups().then(r => { if (r.ok) setGroups(r.data || []); });
    }
  }, [isRegister]);

  useEffect(() => {
    if (user) {
      const pendingShare = localStorage.getItem('pending_share_token');
      if (pendingShare) {
        localStorage.removeItem('pending_share_token');
        navigate(`/join/${pendingShare}`, { replace: true });
      } else {
        navigate('/');
      }
    }
  }, [user, navigate]);

  if (user) return null;

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setSuccess('');
    setLoading(true);

    if (isRegister) {
      const res = await registerUser(username, password, group, fullName);
      setLoading(false);
      if (res.ok) {
        // Проверяем, есть ли токен приглашения
        const pendingShare = localStorage.getItem('pending_share_token');
        if (pendingShare) {
          // Перенаправляем на страницу приглашения для входа
          localStorage.removeItem('pending_share_token');
          navigate(`/join/${pendingShare}`, { replace: true });
        } else {
          setSuccess(res.message + ' Теперь войдите.');
          setIsRegister(false);
        }
      } else {
        setError(res.message);
      }
    } else {
      const res = await loginUser(username, password);
      setLoading(false);
      if (res.ok) {
        const pendingShare = localStorage.getItem('pending_share_token');
        if (pendingShare) {
          localStorage.removeItem('pending_share_token');
          navigate(`/join/${pendingShare}`, { replace: true });
        } else {
          navigate('/');
        }
      } else setError(res.message);
    }
  };

  return (
    <div className="login-page">
      <div className="card login-card">
        <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: 8 }}>
          <button className="btn-icon" onClick={toggleTheme} title="Сменить тему">
            {theme === 'light' ? <FiMoon size={18} /> : <FiSun size={18} />}
          </button>
        </div>
        <div className="login-title">
          {isRegister ? 'Регистрация' : 'Вход в систему'}
        </div>
        <div className="login-subtitle">
          Система тестирования экспертных знаний
        </div>

        {error && <div className="toast toast-error" style={{ marginBottom: 16 }}>{error}</div>}
        {success && <div className="toast toast-success" style={{ marginBottom: 16 }}>{success}</div>}

        <form className="login-form" onSubmit={handleSubmit}>
          {isRegister && (
            <div className="form-group">
              <label className="form-label">ФИО</label>
              <input className="input" value={fullName} onChange={(e) => setFullName(e.target.value)} placeholder="Иванов Иван Иванович" />
            </div>
          )}
          <div className="form-group">
            <label className="form-label">Логин</label>
            <input className="input" value={username} onChange={(e) => setUsername(e.target.value)} required autoFocus />
          </div>
          <div className="form-group">
            <label className="form-label">Пароль</label>
            <input className="input" type="password" value={password} onChange={(e) => setPassword(e.target.value)} required />
          </div>
          {isRegister && (
            <div className="form-group">
              <label className="form-label">Группа (необязательно)</label>
              <select className="input" value={group} onChange={(e) => setGroup(e.target.value)}>
                <option value="">— Без группы —</option>
                {groups.map(g => <option key={g} value={g}>{g}</option>)}
              </select>
            </div>
          )}
          <button className="btn btn-primary w-full" disabled={loading} style={{ justifyContent: 'center', padding: '12px' }}>
            {loading ? '...' : isRegister ? 'Зарегистрироваться' : 'Войти'}
          </button>
        </form>

        <div className="login-toggle">
          {isRegister ? (
            <>Уже есть аккаунт? <a onClick={() => { setIsRegister(false); setError(''); setSuccess(''); }}>Войти</a></>
          ) : (
            <>Нет аккаунта? <a onClick={() => { setIsRegister(true); setError(''); setSuccess(''); }}>Регистрация</a></>
          )}
        </div>
      </div>
    </div>
  );
}
