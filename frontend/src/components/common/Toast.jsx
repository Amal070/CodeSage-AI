/* eslint-disable react-refresh/only-export-components */
import { createContext, useContext, useState, useCallback } from 'react';
import { Icon } from './Icon';

const ToastContext = createContext(null);

export function ToastProvider({ children }) {
  const [toasts, setToasts] = useState([]);

  const addToast = useCallback(({ title, message, type = 'info', duration = 4000 }) => {
    const id = Date.now().toString(36) + Math.random().toString(36).substring(2, 5);
    const newToast = { id, title, message, type };

    setToasts((prev) => [...prev, newToast]);

    if (duration > 0) {
      setTimeout(() => {
        setToasts((prev) => prev.filter((t) => t.id !== id));
      }, duration);
    }
    return id;
  }, []);

  const removeToast = useCallback((id) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  const toastSuccess = useCallback((message, title = 'Success') => {
    return addToast({ title, message, type: 'success' });
  }, [addToast]);

  const toastError = useCallback((message, title = 'Error') => {
    return addToast({ title, message, type: 'error' });
  }, [addToast]);

  const toastInfo = useCallback((message, title = 'Notice') => {
    return addToast({ title, message, type: 'info' });
  }, [addToast]);

  const toastWarning = useCallback((message, title = 'Warning') => {
    return addToast({ title, message, type: 'warning' });
  }, [addToast]);

  const getIconForType = (type) => {
    switch (type) {
      case 'success':
        return 'check';
      case 'error':
        return 'error';
      case 'warning':
        return 'warning';
      default:
        return 'info';
    }
  };

  return (
    <ToastContext.Provider
      value={{
        addToast,
        removeToast,
        success: toastSuccess,
        error: toastError,
        info: toastInfo,
        warning: toastWarning,
      }}
    >
      {children}

      {/* Floating Toast Notification Container */}
      <div
        className="cs-toast-container"
        aria-live="polite"
        aria-atomic="true"
      >
        {toasts.map((toast) => (
          <div
            key={toast.id}
            className={`cs-toast cs-toast-${toast.type} animate-slide-in-right`}
            role="alert"
          >
            <div className={`cs-toast-icon-wrap cs-toast-icon-${toast.type}`}>
              <Icon name={getIconForType(toast.type)} size={16} />
            </div>

            <div className="cs-toast-body">
              {toast.title && <div className="cs-toast-title">{toast.title}</div>}
              {toast.message && <div className="cs-toast-message">{toast.message}</div>}
            </div>

            <button
              type="button"
              className="cs-toast-close"
              onClick={() => removeToast(toast.id)}
              aria-label="Dismiss notification"
            >
              <Icon name="x" size={14} />
            </button>
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}

export function useToast() {
  const context = useContext(ToastContext);
  if (!context) {
    // Graceful fallback if invoked outside of ToastProvider
    return {
      success: (msg) => console.log('[Toast Success]:', msg),
      error: (msg) => console.error('[Toast Error]:', msg),
      info: (msg) => console.log('[Toast Info]:', msg),
      warning: (msg) => console.warn('[Toast Warning]:', msg),
    };
  }
  return context;
}
