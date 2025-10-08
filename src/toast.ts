// Toast notification system

import { ToastOptions } from "./types";

export class ToastService {
  private container: HTMLElement;
  private toastCount: number = 0;

  constructor() {
    this.container = this.createContainer();
  }

  /**
   * Create toast container
   */
  private createContainer(): HTMLElement {
    const existing = document.getElementById("toast-container");
    if (existing) return existing;

    const container = document.createElement("div");
    container.id = "toast-container";
    container.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            z-index: 10000;
            display: flex;
            flex-direction: column;
            gap: 10px;
            max-width: 400px;
        `;
    document.body.appendChild(container);
    return container;
  }

  /**
   * Show a toast notification
   */
  show(options: ToastOptions): void {
    const { message, type, duration = 3000 } = options;

    const toast = document.createElement("div");
    toast.className = `toast toast-${type}`;
    toast.style.cssText = `
            padding: 15px 20px;
            border-radius: 8px;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
            display: flex;
            align-items: center;
            gap: 12px;
            font-size: 0.9rem;
            animation: slideIn 0.3s ease;
            cursor: pointer;
            transition: transform 0.2s ease;
            ${this.getTypeStyles(type)}
        `;

    const icon = document.createElement("i");
    icon.className = this.getIcon(type);
    icon.style.fontSize = "1.2rem";

    const text = document.createElement("span");
    text.textContent = message;
    text.style.flex = "1";

    const closeBtn = document.createElement("span");
    closeBtn.innerHTML = "&times;";
    closeBtn.style.cssText = `
            font-size: 1.5rem;
            font-weight: bold;
            cursor: pointer;
            opacity: 0.7;
            transition: opacity 0.2s;
        `;
    closeBtn.onmouseover = () => (closeBtn.style.opacity = "1");
    closeBtn.onmouseout = () => (closeBtn.style.opacity = "0.7");

    toast.appendChild(icon);
    toast.appendChild(text);
    toast.appendChild(closeBtn);

    // Hover effect
    toast.onmouseover = () => (toast.style.transform = "translateX(-5px)");
    toast.onmouseout = () => (toast.style.transform = "translateX(0)");

    // Close on click
    const removeToast = () => {
      toast.style.animation = "slideOut 0.3s ease";
      setTimeout(() => {
        if (toast.parentElement) {
          this.container.removeChild(toast);
        }
      }, 300);
    };

    closeBtn.onclick = (e) => {
      e.stopPropagation();
      removeToast();
    };

    this.container.appendChild(toast);
    this.toastCount++;

    // Auto remove
    if (duration > 0) {
      setTimeout(removeToast, duration);
    }

    // Add animations if not already added
    this.addAnimations();
  }

  /**
   * Get type-specific styles
   */
  private getTypeStyles(type: string): string {
    const styles = {
      success: "background: #38a169; color: white;",
      error: "background: #e53e3e; color: white;",
      warning: "background: #d69e2e; color: white;",
      info: "background: #3182ce; color: white;",
    };
    return styles[type as keyof typeof styles] || styles.info;
  }

  /**
   * Get icon for toast type
   */
  private getIcon(type: string): string {
    const icons = {
      success: "fas fa-check-circle",
      error: "fas fa-exclamation-circle",
      warning: "fas fa-exclamation-triangle",
      info: "fas fa-info-circle",
    };
    return icons[type as keyof typeof icons] || icons.info;
  }

  /**
   * Add CSS animations
   */
  private addAnimations(): void {
    if (document.getElementById("toast-animations")) return;

    const style = document.createElement("style");
    style.id = "toast-animations";
    style.textContent = `
            @keyframes slideIn {
                from {
                    transform: translateX(400px);
                    opacity: 0;
                }
                to {
                    transform: translateX(0);
                    opacity: 1;
                }
            }
            
            @keyframes slideOut {
                from {
                    transform: translateX(0);
                    opacity: 1;
                }
                to {
                    transform: translateX(400px);
                    opacity: 0;
                }
            }
        `;
    document.head.appendChild(style);
  }

  /**
   * Convenience methods
   */
  success(message: string, duration?: number): void {
    this.show({ message, type: "success", duration });
  }

  error(message: string, duration?: number): void {
    this.show({ message, type: "error", duration });
  }

  warning(message: string, duration?: number): void {
    this.show({ message, type: "warning", duration });
  }

  info(message: string, duration?: number): void {
    this.show({ message, type: "info", duration });
  }

  /**
   * Clear all toasts
   */
  clearAll(): void {
    this.container.innerHTML = "";
    this.toastCount = 0;
  }
}
