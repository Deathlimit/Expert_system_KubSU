import React, { createContext, useContext, useState, useCallback } from 'react';
import * as api from '../api';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(() => {
    const saved = localStorage.getItem('user');
    return saved ? JSON.parse(saved) : null;
  });

  const loginUser = useCallback(async (username, password) => {
    const res = await api.login(username, password);
    if (res.ok) {
      const { access_token, role, username: uname } = res.data;
      localStorage.setItem('token', access_token);
      const u = { username: uname, role };
      localStorage.setItem('user', JSON.stringify(u));
      setUser(u);
      return { ok: true };
    }
    const detail = res.data?.detail;
    const message = Array.isArray(detail)
      ? detail.map(e => e.msg).join('; ')
      : (detail || 'Ошибка входа');
    return { ok: false, message };
  }, []);

  const registerUser = useCallback(async (username, password, group) => {
    const res = await api.register(username, password, group);
    if (res.ok) return { ok: true, message: res.data?.message || 'Регистрация успешна' };
    const detail = res.data?.detail;
    const message = Array.isArray(detail)
      ? detail.map(e => e.msg).join('; ')
      : (detail || 'Ошибка регистрации');
    return { ok: false, message };
  }, []);

  const logout = useCallback(() => {
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    setUser(null);
  }, []);

  return (
    <AuthContext.Provider value={{ user, loginUser, registerUser, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  return useContext(AuthContext);
}
