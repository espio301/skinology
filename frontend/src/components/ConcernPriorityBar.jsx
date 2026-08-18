import { useState } from 'react';
import './ConcernPriorityBar.css';

export default function ConcernPriorityBar({ concernsList, selectedConcerns, onPriorityChange }) {
  const [draggedIdx, setDraggedIdx] = useState(null);

  if (!selectedConcerns || selectedConcerns.length === 0) return null;

  // Map selected IDs/keys to concern objects
  const orderedConcerns = selectedConcerns.map(id => {
    const obj = concernsList.find(c => c.id === id || c.internal_key === id);
    return obj || { id, label: String(id), internal_key: String(id) };
  });

  const handleMove = (fromIndex, toIndex) => {
    if (toIndex < 0 || toIndex >= selectedConcerns.length) return;
    const newOrder = [...selectedConcerns];
    const [moved] = newOrder.splice(fromIndex, 1);
    newOrder.splice(toIndex, 0, moved);
    onPriorityChange(newOrder);
  };

  const handleRemove = (idToRemove) => {
    const newOrder = selectedConcerns.filter(id => id !== idToRemove);
    onPriorityChange(newOrder);
  };

  const handleDragStart = (e, index) => {
    setDraggedIdx(index);
    e.dataTransfer.effectAllowed = 'move';
    e.dataTransfer.setData('text/plain', index.toString());
  };

  const handleDragOver = (e) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = 'move';
  };

  const handleDrop = (e, targetIdx) => {
    e.preventDefault();
    const sourceIdx = parseInt(e.dataTransfer.getData('text/plain'), 10);
    if (!isNaN(sourceIdx) && sourceIdx !== targetIdx) {
      handleMove(sourceIdx, targetIdx);
    }
    setDraggedIdx(null);
  };

  return (
    <div className="concern-priority-bar">
      <div className="priority-bar-header">
        <span className="priority-title">
          <span className="priority-icon">⚡</span> Concern Priority (Drag or Use Arrows to Rank)
        </span>
        <span className="priority-hint">
          Products are sorted by highest concentration of Priority #1 active, then #2, then #3
        </span>
      </div>
      <div className="priority-chips-container">
        {orderedConcerns.map((concern, idx) => (
          <div
            key={concern.id || idx}
            className={`priority-chip ${draggedIdx === idx ? 'dragging' : ''}`}
            draggable
            onDragStart={(e) => handleDragStart(e, idx)}
            onDragOver={handleDragOver}
            onDrop={(e) => handleDrop(e, idx)}
            onDragEnd={() => setDraggedIdx(null)}
          >
            <span className="drag-handle" title="Drag to reorder priority">⋮⋮</span>
            <span className={`priority-rank-tag priority-rank-${idx + 1}`}>
              #{idx + 1}
            </span>
            <span className="priority-chip-label">{concern.label}</span>
            <div className="priority-controls">
              <button
                type="button"
                className="priority-btn"
                disabled={idx === 0}
                onClick={() => handleMove(idx, idx - 1)}
                title="Increase Priority"
              >
                ◀
              </button>
              <button
                type="button"
                className="priority-btn"
                disabled={idx === orderedConcerns.length - 1}
                onClick={() => handleMove(idx, idx + 1)}
                title="Decrease Priority"
              >
                ▶
              </button>
              <button
                type="button"
                className="priority-btn remove-btn"
                onClick={() => handleRemove(concern.id)}
                title="Remove Concern"
              >
                ×
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
