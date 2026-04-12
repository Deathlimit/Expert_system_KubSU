import React, { useState, useRef, useEffect } from 'react';
import { FiChevronDown } from 'react-icons/fi';

/**
 * AutocompleteInput — text input with filtered dropdown suggestions.
 *
 * Props:
 *   value        — controlled string value
 *   onChange     — called with new string value
 *   options      — array of suggestion strings
 *   placeholder  — input placeholder
 *   style        — wrapper div style
 *   inputStyle   — additional style for the <input>
 *   className    — extra className for the <input>
 *   onEnter      — called when Enter pressed with no highlighted suggestion
 *   disabled     — disables the input
 */
export default function AutocompleteInput({
  value = '',
  onChange,
  options = [],
  placeholder = '',
  style,
  inputStyle,
  className = '',
  onEnter,
  disabled = false,
}) {
  const [open, setOpen] = useState(false);
  const [highlighted, setHighlighted] = useState(-1);
  const containerRef = useRef(null);
  const inputRef = useRef(null);
  const listRef = useRef(null);

  // Filtered list: show all when empty, filter otherwise
  const filtered = value.trim()
    ? options.filter(o => o.toLowerCase().includes(value.toLowerCase()))
    : options;

  const showDropdown = open && filtered.length > 0 && !disabled;

  // Close on outside click
  useEffect(() => {
    const handleOutside = (e) => {
      if (containerRef.current && !containerRef.current.contains(e.target)) {
        setOpen(false);
        setHighlighted(-1);
      }
    };
    document.addEventListener('mousedown', handleOutside);
    return () => document.removeEventListener('mousedown', handleOutside);
  }, []);

  // Scroll highlighted item into view
  useEffect(() => {
    if (highlighted >= 0 && listRef.current) {
      const items = listRef.current.querySelectorAll('li');
      items[highlighted]?.scrollIntoView({ block: 'nearest' });
    }
  }, [highlighted]);

  const handleSelect = (opt) => {
    onChange(opt);
    setOpen(false);
    setHighlighted(-1);
  };

  const handleKeyDown = (e) => {
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      if (!open) { setOpen(true); setHighlighted(0); return; }
      setHighlighted(h => Math.min(h + 1, filtered.length - 1));
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setHighlighted(h => Math.max(h - 1, 0));
    } else if (e.key === 'Enter') {
      if (showDropdown && highlighted >= 0 && filtered[highlighted] != null) {
        e.preventDefault();
        handleSelect(filtered[highlighted]);
      } else if (onEnter) {
        onEnter();
      }
    } else if (e.key === 'Escape') {
      setOpen(false);
      setHighlighted(-1);
    }
  };

  const toggleOpen = (e) => {
    e.preventDefault();
    setOpen(o => !o);
    setHighlighted(-1);
    inputRef.current?.focus();
  };

  return (
    <div ref={containerRef} style={{ position: 'relative', ...style }}>
      <div style={{ position: 'relative', display: 'flex' }}>
        <input
          ref={inputRef}
          className={`input ${className}`}
          style={{ paddingRight: '2.25rem', width: '100%', ...inputStyle }}
          value={value}
          onChange={e => { onChange(e.target.value); setOpen(true); setHighlighted(-1); }}
          onFocus={() => setOpen(true)}
          onKeyDown={handleKeyDown}
          placeholder={placeholder}
          autoComplete="off"
          disabled={disabled}
        />
        <button
          type="button"
          tabIndex={-1}
          disabled={disabled}
          onMouseDown={toggleOpen}
          style={{
            position: 'absolute',
            right: 0, top: 0, bottom: 0,
            width: '2.25rem',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            background: 'none',
            border: 'none',
            borderLeft: '1px solid var(--border)',
            borderRadius: '0 var(--radius, 8px) var(--radius, 8px) 0',
            cursor: disabled ? 'default' : 'pointer',
            color: 'var(--text-secondary, #888)',
            transition: 'background 0.1s',
          }}
        >
          <FiChevronDown
            size={15}
            style={{
              transform: open ? 'rotate(180deg)' : 'none',
              transition: 'transform 0.15s ease',
            }}
          />
        </button>
      </div>

      {showDropdown && (
        <ul
          ref={listRef}
          style={{
            position: 'absolute',
            top: 'calc(100% + 3px)',
            left: 0,
            right: 0,
            zIndex: 1000,
            background: 'var(--bg-card)',
            border: '1px solid var(--border)',
            borderRadius: 8,
            boxShadow: '0 8px 28px rgba(0,0,0,.25)',
            listStyle: 'none',
            margin: 0,
            padding: '4px',
            maxHeight: 240,
            overflowY: 'auto',
          }}
        >
          {filtered.map((opt, i) => (
            <li
              key={opt}
              onMouseDown={e => { e.preventDefault(); handleSelect(opt); }}
              onMouseEnter={() => setHighlighted(i)}
              style={{
                padding: '7px 10px',
                borderRadius: 6,
                cursor: 'pointer',
                fontSize: '.9rem',
                background: i === highlighted ? 'var(--nav-active-bg)' : 'transparent',
                color: i === highlighted ? 'var(--nav-active-text)' : 'var(--text)',
                fontWeight: i === highlighted ? 500 : 400,
                transition: 'background 0.08s',
              }}
            >
              {opt}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
