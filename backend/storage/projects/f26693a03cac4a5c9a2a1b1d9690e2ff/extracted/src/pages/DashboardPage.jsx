import React, { useState, useEffect } from 'react';
import { fetchTasks, completeTask } from '../services/api';
import TaskCard from '../components/TaskCard';

export default function DashboardPage() {
  const [tasks, setTasks] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchTasks()
      .then(data => setTasks(data))
      .finally(() => setLoading(false));
  }, []);

  const handleComplete = async (taskId) => {
    await completeTask(taskId);
    setTasks(prev => prev.filter(t => t.id !== taskId));
  };

  if (loading) return <div>Loading tasks...</div>;

  return (
    <div className="dashboard-grid">
      <h3>Active Tasks ({tasks.length})</h3>
      {tasks.map(task => (
        <TaskCard key={task.id} task={task} onComplete={handleComplete} />
      ))}
    </div>
  );
}
