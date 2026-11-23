import React, { useCallback, useEffect, useState } from 'react';
import * as api from '../../api';
import SortableTable from '../../components/SortableTable';
import Modal from '../../components/Modal';
import { useToast } from '../../components/Toast';
import { FiUserPlus, FiRefreshCw, FiEye, FiClock } from 'react-icons/fi';

const TASK_TYPE = 'create_student_profile';
const ACTIVE = ['queued', 'in_progress'];

const STATUS_META = {
  none: { label: 'Не создавался', cls: 'badge-neutral' },
  queued: { label: 'В очереди', cls: 'badge-yellow' },
  in_progress: { label: 'В процессе', cls: 'badge-blue' },
  done: { label: 'Готов', cls: 'badge-green' },
  failed: { label: 'Ошибка', cls: 'badge-red' },
};

export default function StudentProfiles() {
  const toast = useToast();
  const [students, setStudents] = useState([]);
  const [tasks, setTasks] = useState({});
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState({});
  const [viewedUser, setViewedUser] = useState(null);

  const load = useCallback(async () => {
    setLoading(true);
    const [studentsRes, tasksRes] = await Promise.all([
      api.getStudents(),
      api.listQueueTasks({ type: TASK_TYPE, limit: 500 }),
    ]);

    if (studentsRes.ok) {
      setStudents(studentsRes.data || []);
    } else {
      toast(studentsRes.data?.detail || 'Не удалось загрузить студентов', 'error');
    }

    if (tasksRes.ok) {
      const byUser = {};
      // Сервер отдаёт задачи от новых к старым — оставляем последнюю на студента.
      for (const task of tasksRes.data || []) {
        const username = task.username || task.payload?.username;
        if (username && !byUser[username]) byUser[username] = task;
      }
      setTasks(byUser);
    } else {
      toast(tasksRes.data?.detail || 'Не удалось загрузить задачи', 'error');
    }

    setLoading(false);
  }, [toast]);

  useEffect(() => { load(); }, [load]);

  // Пока есть активные задачи — опрашиваем их статус каждые 3 секунды.
  useEffect(() => {
    const activeTasks = Object.values(tasks).filter((t) => t && ACTIVE.includes(t.status));
    if (!activeTasks.length) return undefined;

    let cancelled = false;
    const tick = async () => {
      for (const task of activeTasks) {
        const res = await api.getQueueTask(task.task_id);
        if (cancelled || !res.ok) continue;
        const username = res.data.username || res.data.payload?.username;
        if (!username) continue;
        setTasks((prev) => ({ ...prev, [username]: res.data }));
      }
    };
    const timer = setInterval(tick, 3000);
    return () => {
      cancelled = true;
      clearInterval(timer);
    };
  }, [tasks]);

  const handleCreate = async (student) => {
    const username = student.username;
    setBusy((prev) => ({ ...prev, [username]: true }));
    const res = await api.createStudentProfileTask(username);
    setBusy((prev) => ({ ...prev, [username]: false }));

    if (res.ok) {
      setTasks((prev) => ({ ...prev, [username]: res.data }));
      toast(`Задача для ${username} создана: ${res.data.task_id}`, 'success');
    } else {
      toast(res.data?.detail || 'Не удалось создать задачу', 'error');
    }
  };

  const rows = students.map((student) => {
    const task = tasks[student.username] || null;
    const meta = STATUS_META[task?.status] || STATUS_META.none;
    return {
      ...student,
      task_id: task?.task_id || '',
      status: meta.label,
      status_code: task?.status || 'none',
      _task: task,
    };
  });

  const columns = [
    { key: 'username', label: 'Логин' },
    { key: 'full_name', label: 'ФИО', render: (value) => value || '—' },
    { key: 'group', label: 'Группа', render: (value) => value || '—' },
    {
      key: 'status',
      label: 'Профиль',
      render: (_, row) => {
        const meta = STATUS_META[row.status_code] || STATUS_META.none;
        return <span className={`badge ${meta.cls}`}>{meta.label}</span>;
      },
    },
    {
      key: 'task_id',
      label: 'Задача',
      render: (value) => (value ? <code style={{ fontSize: '.75rem' }}>{value}</code> : '—'),
    },
    {
      key: '_actions',
      label: 'Действия',
      render: (_, row) => (
        <div className="flex gap-xs">
          <button
            className="btn btn-primary btn-sm"
            disabled={Boolean(busy[row.username])}
            onClick={() => handleCreate(row)}
          >
            {busy[row.username] ? <FiClock size={14} /> : <FiUserPlus size={14} />}
            Создать профиль
          </button>
          {row._task && ['done', 'failed'].includes(row._task.status) && (
            <button className="btn btn-secondary btn-sm" onClick={() => setViewedUser(row.username)}>
              <FiEye size={14} /> Результат
            </button>
          )}
        </div>
      ),
    },
  ];

  const viewedRow = viewedUser ? rows.find((row) => row.username === viewedUser) : null;
  const viewedTask = viewedRow?._task;

  if (loading) return <p className="text-secondary">Загрузка...</p>;

  return (
    <>
      <div className="flex items-center" style={{ justifyContent: 'space-between', marginBottom: '.5rem' }}>
        <h1 className="page-title" style={{ margin: 0 }}>Профили студентов</h1>
        <button className="btn btn-secondary btn-sm" onClick={load}>
          <FiRefreshCw size={14} /> Обновить
        </button>
      </div>
      <p className="text-sm text-secondary mb-4">
        Кнопка ставит задачу в очередь <code>/queue</code>. Воркер забирает её
        HTTP-поллингом, генерирует профиль и присылает результат обратно.
      </p>

      <div className="card">
        <SortableTable columns={columns} data={rows} emptyText="Нет студентов для создания профиля" />
      </div>

      {viewedTask && (
        <Modal title={`Профиль: ${viewedRow.username}`} onClose={() => setViewedUser(null)}>
          {viewedTask.status === 'failed' ? (
            <p className="text-sm" style={{ color: 'var(--color-red)' }}>{viewedTask.error || 'Ошибка задачи'}</p>
          ) : (
            <pre style={{
              background: 'var(--bg-input)',
              padding: '.75rem',
              borderRadius: 6,
              fontSize: '.8rem',
              overflow: 'auto',
              maxHeight: 480,
              margin: 0,
            }}>
{JSON.stringify(viewedTask.result, null, 2)}
            </pre>
          )}
        </Modal>
      )}
    </>
  );
}