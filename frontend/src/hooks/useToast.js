import { useCallback, useState } from "react";

let toastId = 0;

export function useToast() {
  const [toasts, setToasts] = useState([]);

  const dismissToast = useCallback((id) => {
    setToasts((current) => current.filter((toast) => toast.id !== id));
  }, []);

  const showToast = useCallback((message, type = "success", duration = 3500) => {
    const id = ++toastId;
    setToasts((current) => [...current, { id, message, type, duration }]);
    return id;
  }, []);

  return { toasts, showToast, dismissToast };
}
