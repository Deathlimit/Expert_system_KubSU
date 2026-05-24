import React, { useState, useEffect } from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import Sidebar from '../../components/Sidebar';
import SortableTable from '../../components/SortableTable';
import Modal from '../../components/Modal';
import { ToastProvider, useToast } from '../../components/Toast';
import MobileTopbar from '../../components/MobileTopbar';
import * as api from '../../api';
import {
  FiUsers, FiPlusCircle, FiEdit, FiFileText,
  FiSettings, FiGrid, FiSliders, FiUpload, FiLayers, FiHelpCircle, FiCopy, FiCheck
} from 'react-icons/fi';

import AddQuestion from '../teacher/AddQuestion';
import EditQuestions from '../teacher/EditQuestions';
import CreateTest from '../teacher/CreateTest';
import ManageTests from '../teacher/ManageTests';
import GenerateTest from '../teacher/GenerateTest';
import GradingCriteria from '../teacher/GradingCriteria';

const sidebarLinks = [
  {
    label: 'Администрирование', items: [
      { id: 'users', text: 'Управление ролями', icon: <FiUsers size={18} />, path: '/admin/users' },
      { id: 'groups', text: 'Управление группами', icon: <FiLayers size={18} />, path: '/admin/groups' },
    ]
  },
  {
    label: 'Вопросы', items: [
      { id: 'add', text: 'Добавить вопрос', icon: <FiPlusCircle size={18} />, path: '/admin/add-question' },
      { id: 'edit', text: 'Изменить вопросы', icon: <FiEdit size={18} />, path: '/admin/edit-questions' },
      { id: 'import', text: 'Импорт вопросов', icon: <FiUpload size={18} />, path: '/admin/import-questions' },
    ]
  },
  {
    label: 'Тесты', items: [
      { id: 'create', text: 'Создать тест', icon: <FiFileText size={18} />, path: '/admin/create-test' },
      { id: 'manage', text: 'Управление тестами', icon: <FiSettings size={18} />, path: '/admin/manage-tests' },
      { id: 'generate', text: 'Сгенерировать тест', icon: <FiGrid size={18} />, path: '/admin/generate-test' },
    ]
  },
  {
    label: 'Настройки', items: [
      { id: 'criteria', text: 'Критерии оценки', icon: <FiSliders size={18} />, path: '/admin/criteria' },
    ]
  }
];

export default function AdminDashboard() {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  return (
    <ToastProvider>
      <div className="page-layout">
        <Sidebar links={sidebarLinks} isMobileOpen={mobileMenuOpen} onClose={() => setMobileMenuOpen(false)} />
        <div className={`sidebar-overlay ${mobileMenuOpen ? 'show' : ''}`} onClick={() => setMobileMenuOpen(false)} />
        <main className="main-content">
          <MobileTopbar title="Панель администратора" onMenu={() => setMobileMenuOpen(true)} />
          <Routes>
            <Route index element={<Navigate to="users" replace />} />
            <Route path="users" element={<UserManagement />} />
            <Route path="groups" element={<GroupManagement />} />
            <Route path="add-question" element={<AddQuestion />} />
            <Route path="edit-questions" element={<EditQuestions />} />
            <Route path="import-questions" element={<ImportQuestions />} />
            <Route path="create-test" element={<CreateTest />} />
            <Route path="manage-tests" element={<ManageTests />} />
            <Route path="generate-test" element={<GenerateTest />} />
            <Route path="criteria" element={<GradingCriteria />} />
          </Routes>
        </main>
      </div>
    </ToastProvider>
  );
}

function UserManagement() {
  const toast = useToast();
  const [users, setUsers] = useState([]);
  const [groups, setGroups] = useState([]);
  const [loading, setLoading] = useState(true);
  const [pwdModal, setPwdModal] = useState(null);
  const [fnModal, setFnModal] = useState(null);

  const loadUsers = async () => {
    setLoading(true);
    const [usersRes, groupsRes] = await Promise.all([api.getAllUsers(), api.getAllGroups()]);
    if (usersRes.ok) setUsers(Object.entries(usersRes.data || {}).map(([username, info]) => ({ username, ...info })));
    if (groupsRes.ok) setGroups(groupsRes.data || []);
    setLoading(false);
  };

  useEffect(() => { loadUsers(); }, []);

  const handleRoleChange = async (username, newRole) => {
    const res = await api.changeUserRole(username, newRole);
    if (res.ok) {
      toast(`Роль ${username} изменена на ${newRole}`, 'success');
      loadUsers();
    } else {
      toast(res.data?.detail || 'Ошибка', 'error');
    }
  };

  const handleGroupChange = async (username, newGroup) => {
    const res = await api.changeUserGroup(username, newGroup);
    if (res.ok) {
      toast(newGroup ? `Группа ${username} изменена на ${newGroup}` : `Пользователь ${username} оставлен без группы`, 'success');
      loadUsers();
    } else {
      toast(res.data?.detail || 'Ошибка', 'error');
    }
  };

  const handleDeleteUser = async (username) => {
    if (!window.confirm(`Удалить пользователя "${username}"? Это действие необратимо.`)) return;
    const res = await api.deleteUser(username);
    if (res.ok) {
      toast(`Пользователь ${username} удалён`, 'success');
      loadUsers();
    } else {
      toast(res.data?.detail || 'Ошибка', 'error');
    }
  };

  const columns = [
    { key: 'username', label: 'Логин' },
    { key: 'full_name', label: 'ФИО', render: (v, row) => (
      <div className="flex items-center gap-xs">
        <span>{v || '—'}</span>
        <button className="btn btn-ghost btn-sm" title="Изменить ФИО" onClick={() => setFnModal(row)}>
          <FiEdit size={12} />
        </button>
      </div>
    )},
    { key: 'role', label: 'Роль', render: (v, row) => {
      const isAdmin = v === 'admin';
      return (
        <select className="select" style={{ minWidth: 130 }} value={v} disabled={isAdmin} title={isAdmin ? 'Нельзя изменить роль администратора' : ''} onChange={e => handleRoleChange(row.username, e.target.value)}>
          <option value="unassigned">unassigned</option>
          <option value="student">student</option>
          <option value="teacher">teacher</option>
          <option value="admin">admin</option>
        </select>
      );
    }},
    { key: 'group', label: 'Группа', render: (v, row) => (
      <select className="select" style={{ minWidth: 160 }} value={v || ''} onChange={e => handleGroupChange(row.username, e.target.value)}>
        <option value="">Без группы</option>
        {groups.map(g => <option key={g} value={g}>{g}</option>)}
      </select>
    ) },
    { key: '_actions', label: 'Действия', render: (_, row) => {
      const isAdmin = row.role === 'admin';
      return (
        <div className="flex gap-xs">
          <button className="btn btn-secondary btn-sm" onClick={() => setPwdModal(row.username)}>Сбросить пароль</button>
          {!isAdmin && <button className="btn btn-danger btn-sm" onClick={() => handleDeleteUser(row.username)}>Удалить</button>}
        </div>
      );
    }},
  ];

  if (loading) return <p className="text-secondary">Загрузка...</p>;

  return (
    <>
      <h1 className="page-title">Управление ролями пользователей</h1>
      <div className="card">
        <SortableTable columns={columns} data={users} emptyText="Нет пользователей" />
      </div>
      {pwdModal && <ChangePasswordModal username={pwdModal} onClose={() => setPwdModal(null)} />}
      {fnModal && <EditFullNameModal username={fnModal.username} currentName={fnModal.full_name || ''} onClose={() => setFnModal(null)} onSaved={loadUsers} />}
    </>
  );
}

function ChangePasswordModal({ username, onClose }) {
  const toast = useToast();
  const [newPwd, setNewPwd] = useState('');
  const [saving, setSaving] = useState(false);

  const handleSave = async () => {
    if (!newPwd) { toast('Введите новый пароль', 'error'); return; }
    if (newPwd.length < 6) { toast('Новый пароль должен быть не менее 6 символов', 'error'); return; }
    setSaving(true);
    const res = await api.resetPassword(username, newPwd);
    setSaving(false);
    if (res.ok) { toast('Пароль сброшен', 'success'); onClose(); }
    else toast(res.data?.detail || 'Ошибка', 'error');
  };

  return (
    <Modal title={`Сбросить пароль: ${username}`} onClose={onClose}>
      <div className="flex flex-col gap-sm">
        <input className="input" type="password" placeholder="Новый пароль (мин. 6 символов)" value={newPwd} onChange={e => setNewPwd(e.target.value)} />
        <button className="btn btn-primary" disabled={saving} onClick={handleSave}>Сбросить пароль</button>
      </div>
    </Modal>
  );
}

function EditFullNameModal({ username, currentName, onClose, onSaved }) {
  const toast = useToast();
  const [fullName, setFullName] = useState(currentName);
  const [saving, setSaving] = useState(false);

  const handleSave = async () => {
    setSaving(true);
    const res = await api.updateUserFullName(username, fullName.trim());
    setSaving(false);
    if (res.ok) { toast('ФИО обновлено', 'success'); onSaved(); onClose(); }
    else toast(res.data?.detail || 'Ошибка', 'error');
  };

  return (
    <Modal title={`ФИО: ${username}`} onClose={onClose}>
      <div className="flex flex-col gap-sm">
        <input className="input" placeholder="Фамилия Имя Отчество" value={fullName} onChange={e => setFullName(e.target.value)} autoFocus />
        <button className="btn btn-primary" disabled={saving} onClick={handleSave}>Сохранить</button>
      </div>
    </Modal>
  );
}

function GroupManagement() {
  const toast = useToast();
  const [groups, setGroups] = useState([]);
  const [newGroup, setNewGroup] = useState('');
  const [loading, setLoading] = useState(true);
  const [editingGroup, setEditingGroup] = useState(null);
  const [editValue, setEditValue] = useState('');

  const loadGroups = async () => {
    setLoading(true);
    const res = await api.getAllGroups();
    if (res.ok) setGroups(res.data || []);
    setLoading(false);
  };

  useEffect(() => { loadGroups(); }, []);

  const handleCreate = async () => {
    if (!newGroup.trim()) { toast('Введите название группы', 'error'); return; }
    const res = await api.createGroup(newGroup.trim());
    if (res.ok) {
      toast('Группа создана', 'success');
      setNewGroup('');
      loadGroups();
    } else {
      toast(res.data?.detail || 'Ошибка', 'error');
    }
  };

  const handleDelete = async (name) => {
    if (!window.confirm(`Удалить группу "${name}"?`)) return;
    const res = await api.deleteGroup(name);
    if (res.ok) {
      toast('Группа удалена', 'success');
      loadGroups();
    } else {
      toast(res.data?.detail || 'Ошибка', 'error');
    }
  };

  const handleRename = async (oldName) => {
    const newName = editValue.trim();
    if (!newName) { toast('Введите название группы', 'error'); return; }
    if (newName === oldName) { setEditingGroup(null); return; }
    const res = await api.renameGroup(oldName, newName);
    if (res.ok) {
      toast('Группа переименована', 'success');
      setEditingGroup(null);
      loadGroups();
    } else {
      toast(res.data?.detail || 'Ошибка', 'error');
    }
  };

  const startRename = (group) => {
    setEditingGroup(group);
    setEditValue(group);
  };

  if (loading) return <p className="text-secondary">Загрузка...</p>;

  return (
    <>
      <h1 className="page-title">Управление группами</h1>
      <div className="card mb-4">
        <div className="flex items-center gap-sm">
          <input className="input" style={{ maxWidth: 300 }} value={newGroup} onChange={e => setNewGroup(e.target.value)} placeholder="Название новой группы" onKeyDown={e => e.key === 'Enter' && handleCreate()} />
          <button className="btn btn-primary btn-sm" onClick={handleCreate}>Создать</button>
        </div>
      </div>
      <div className="card">
        {groups.length === 0 ? <p className="text-secondary">Нет групп</p> : (
          <div className="flex flex-col gap-xs">
            {groups.map(g => (
              <div key={g} className="flex items-center" style={{ justifyContent: 'space-between', padding: '.5rem .75rem', borderRadius: 6, border: '1px solid var(--border)' }}>
                {editingGroup === g ? (
                  <div className="flex items-center gap-sm">
                    <input className="input" style={{ maxWidth: 200 }} value={editValue} onChange={e => setEditValue(e.target.value)} onKeyDown={e => e.key === 'Enter' && handleRename(g)} autoFocus />
                    <button className="btn btn-primary btn-sm" onClick={() => handleRename(g)}>Сохранить</button>
                    <button className="btn btn-secondary btn-sm" onClick={() => setEditingGroup(null)}>Отмена</button>
                  </div>
                ) : (
                  <>
                    <span>{g}</span>
                    <div className="flex items-center gap-xs">
                      <button className="btn btn-secondary btn-sm" onClick={() => startRename(g)}>Переименовать</button>
                      <button className="btn btn-danger btn-sm" onClick={() => handleDelete(g)}>Удалить</button>
                    </div>
                  </>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </>
  );
}

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

function ImportQuestions() {
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
      <h1 className="page-title">Импорт вопросов из JSON
        <button className="btn btn-ghost btn-sm" onClick={() => setShowHelp(!showHelp)} title="Формат данных" style={{ marginLeft: 8 }}>
          <FiHelpCircle size={18} />
        </button>
      </h1>

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
