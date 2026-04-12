import React from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import Sidebar from '../../components/Sidebar';
import { ToastProvider } from '../../components/Toast';
import {
  FiPlusCircle, FiEdit, FiFileText, FiSettings,
  FiGrid, FiSliders, FiBarChart2, FiUpload
} from 'react-icons/fi';

import AddQuestion from './AddQuestion';
import EditQuestions from './EditQuestions';
import ImportQuestions from './ImportQuestions';
import CreateTest from './CreateTest';
import ManageTests from './ManageTests';
import GenerateTest from './GenerateTest';
import GradingCriteria from './GradingCriteria';

const sidebarLinks = [
  {
    label: 'Вопросы', items: [
      { id: 'add', text: 'Добавить вопрос', icon: <FiPlusCircle size={18} />, path: '/teacher/add-question' },
      { id: 'edit', text: 'Изменить вопросы', icon: <FiEdit size={18} />, path: '/teacher/edit-questions' },
      { id: 'import', text: 'Импорт вопросов', icon: <FiUpload size={18} />, path: '/teacher/import-questions' },
    ]
  },
  {
    label: 'Тесты', items: [
      { id: 'create', text: 'Создать тест', icon: <FiFileText size={18} />, path: '/teacher/create-test' },
      { id: 'manage', text: 'Управление тестами', icon: <FiSettings size={18} />, path: '/teacher/manage-tests' },
      { id: 'generate', text: 'Сгенерировать тест', icon: <FiGrid size={18} />, path: '/teacher/generate-test' },
    ]
  },
  {
    label: 'Настройки', items: [
      { id: 'criteria', text: 'Критерии оценки', icon: <FiSliders size={18} />, path: '/teacher/criteria' },
    ]
  }
];

export default function TeacherDashboard() {
  return (
    <ToastProvider>
      <div className="page-layout">
        <Sidebar links={sidebarLinks} />
        <main className="main-content">
          <Routes>
            <Route index element={<Navigate to="manage-tests" replace />} />
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
