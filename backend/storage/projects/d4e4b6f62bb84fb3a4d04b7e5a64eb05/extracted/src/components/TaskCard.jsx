import React from 'react';
import { formatDueDate } from '../utils/formatters';

export default function TaskCard({ task, onComplete }) {
  return (
    <div className="task-card">
      <h4>{task.title}</h4>
      <p>{task.description}</p>
      <span className="due-date">Due: {formatDueDate(task.dueDate)}</span>
      <button className="btn-complete" onClick={() => onComplete(task.id)}>
        Complete Task
      </button>
    </div>
  );
}
