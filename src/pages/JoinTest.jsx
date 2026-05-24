import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { useTheme } from '../context/ThemeContext';
import * as api from '../api';
import { FiPlay, FiClock, FiBookOpen, FiLogIn, FiUserPlus } from 'react-icons/fi';

export default function JoinTest() {
  const { shareToken } = useParams();
  const { user } = useAuth();
  const navigate = useNavigate();
  const { theme, toggleTheme } = useTheme();
  const [testInfo, setTestInfo] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [joining, setJoining] = useState(false);

  useEffect(() => {
    api.getSharedTestInfo(shareToken).then(res => {
      if (res.ok) {
        setTestInfo(res.data);
      } else {
        setError(res.data?.detail || 'Ссылка недействительна');
      }
      setLoading(false);
    });
  }, [shareToken]);

  // If user is already authenticated, auto-join
  useEffect(() => {
    if (user && testInfo && !joining) {
      handleJoin();
    }
  }, [user, testInfo]);

  const handleJoin = async () => {
    if (joining) return;
    setJoining(true);
    const res = await api.joinTestByShare(shareToken);
    if (res.ok) {
      if (res.data.role_restricted) {
        // Teacher/admin clicked share link — redirect to their dashboard
        navigate('/', { replace: true });
        return;
      }
      navigate(`/student/test/${res.data.test_id}`, { replace: true });
    } else {
      setError(res.data?.detail || 'Не удалось присоединиться к тесту');
      setJoining(false);
    }
  };

  const handleLoginRedirect = () => {
    localStorage.setItem('pending_share_token', shareToken);
    navigate('/login');
  };

  if (loading) {
    return (
      <div className="login-page">
        <div className="card login-card">
          <div className="login-title">Загрузка...</div>
        </div>
      </div>
    );
  }

  if (error && !testInfo) {
    return (
      <div className="login-page">
        <div className="card login-card">
          <div className="login-title">Ошибка</div>
          <div className="login-subtitle" style={{ color: 'var(--color-red)' }}>{error}</div>
          <button className="btn btn-primary w-full" style={{ marginTop: 16, justifyContent: 'center', padding: '12px' }} onClick={() => navigate('/login')}>
            На главную
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="login-page">
      <div className="card login-card" style={{ maxWidth: 440 }}>
        <div className="login-title">Приглашение на тест</div>
        <div className="login-subtitle">Вас пригласили пройти тестирование</div>

        {testInfo && (
          <div style={{
            margin: '1.25rem 0',
            padding: '1rem',
            borderRadius: 10,
            background: 'var(--bg-secondary)',
            border: '1px solid var(--border)',
          }}>
            <div style={{ fontWeight: 700, fontSize: '1.15rem', marginBottom: '.5rem' }}>
              {testInfo.test_name || 'Безымянный тест'}
            </div>
            <div className="text-sm text-secondary" style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
              <span><FiBookOpen size={14} style={{ marginRight: 6, verticalAlign: 'middle' }} />{testInfo.question_count} вопросов</span>
              {testInfo.time_limit_minutes && (
                <span><FiClock size={14} style={{ marginRight: 6, verticalAlign: 'middle' }} />{testInfo.time_limit_minutes} мин на прохождение</span>
              )}
            </div>
          </div>
        )}

        {error && <div className="toast toast-error" style={{ marginBottom: 16 }}>{error}</div>}

        {user ? (
          <button
            className="btn btn-primary w-full"
            style={{ justifyContent: 'center', padding: '12px' }}
            disabled={joining}
            onClick={handleJoin}
          >
            <FiPlay size={16} /> {joining ? 'Присоединение...' : 'Присоединиться и начать'}
          </button>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '.75rem' }}>
            <button
              className="btn btn-primary w-full"
              style={{ justifyContent: 'center', padding: '12px' }}
              onClick={handleLoginRedirect}
            >
              <FiLogIn size={16} /> Войти и присоединиться
            </button>
            <button
              className="btn btn-secondary w-full"
              style={{ justifyContent: 'center', padding: '12px' }}
              onClick={() => { localStorage.setItem('pending_share_token', shareToken); navigate('/login'); }}
            >
              <FiUserPlus size={16} /> Зарегистрироваться
            </button>
            <div className="text-sm text-secondary" style={{ textAlign: 'center' }}>
              Для прохождения теста необходимо авторизоваться
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
