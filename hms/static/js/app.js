/**
 * Hedgewar Hospital Management System - Core Client JS
 * Zero inline scripts, accessible interactions, WCAG AA compliant.
 */

(function () {
  'use strict';

  // --- 1. Theme Management (Light / Dark) ---
  const THEME_KEY = 'hms_theme_preference';

  function getPreferredTheme() {
    const saved = localStorage.getItem(THEME_KEY);
    if (saved) return saved;
    return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
  }

  function applyTheme(theme) {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem(THEME_KEY, theme);

    const themeToggle = document.getElementById('theme-toggle-btn');
    if (themeToggle) {
      const icon = themeToggle.querySelector('i');
      if (icon) {
        if (theme === 'dark') {
          icon.className = 'fa-solid fa-sun';
          themeToggle.setAttribute('aria-label', 'Switch to light mode');
        } else {
          icon.className = 'fa-solid fa-moon';
          themeToggle.setAttribute('aria-label', 'Switch to dark mode');
        }
      }
    }
  }

  // --- 2. Mobile Sidebar Drawer Management ---
  function initSidebar() {
    const toggleBtn = document.getElementById('sidebar-toggle-btn');
    const sidebar = document.querySelector('.app-sidebar');
    const backdrop = document.querySelector('.sidebar-backdrop');

    if (!toggleBtn || !sidebar) return;

    function openSidebar() {
      sidebar.classList.add('show');
      if (backdrop) backdrop.classList.add('show');
      toggleBtn.setAttribute('aria-expanded', 'true');
    }

    function closeSidebar() {
      sidebar.classList.remove('show');
      if (backdrop) backdrop.classList.remove('show');
      toggleBtn.setAttribute('aria-expanded', 'false');
    }

    toggleBtn.addEventListener('click', function () {
      const isOpen = sidebar.classList.contains('show');
      if (isOpen) {
        closeSidebar();
      } else {
        openSidebar();
      }
    });

    if (backdrop) {
      backdrop.addEventListener('click', closeSidebar);
    }

    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape' && sidebar.classList.contains('show')) {
        closeSidebar();
      }
    });
  }

  // --- 3. Toasts & Flash Notifications ---
  function initToasts() {
    document.querySelectorAll('.hms-toast').forEach(function (toast) {
      const closeBtn = toast.querySelector('.toast-close-btn');
      if (closeBtn) {
        closeBtn.addEventListener('click', function () {
          toast.remove();
        });
      }

      const autoDismiss = toast.getAttribute('data-auto-dismiss');
      if (autoDismiss) {
        setTimeout(function () {
          toast.style.opacity = '0';
          toast.style.transition = 'opacity 300ms ease';
          setTimeout(function () {
            toast.remove();
          }, 300);
        }, parseInt(autoDismiss, 10));
      }
    });
  }

  // --- 4. Double Submit Prevention & Spinners ---
  function initForms() {
    document.querySelectorAll('form:not([data-allow-double-submit])').forEach(function (form) {
      form.addEventListener('submit', function () {
        const submitBtn = form.querySelector('button[type="submit"]');
        if (submitBtn && !submitBtn.disabled) {
          // Delay briefly to allow browser native validations to run
          setTimeout(function () {
            if (!form.checkValidity || form.checkValidity()) {
              submitBtn.disabled = true;
              const originalHtml = submitBtn.innerHTML;
              submitBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin" aria-hidden="true"></i> <span>Processing...</span>';
              // Re-enable if page doesn't unload in 10s
              setTimeout(function () {
                submitBtn.disabled = false;
                submitBtn.innerHTML = originalHtml;
              }, 10000);
            }
          }, 10);
        }
      });
    });

    // Confirmation challenge typing (e.g. typing entity name to confirm delete/void)
    document.querySelectorAll('.modal-confirm-challenge').forEach(function (input) {
      const target = input.getAttribute('data-target');
      const submitBtn = input.closest('form').querySelector('.modal-submit-btn');

      if (target && submitBtn) {
        input.addEventListener('input', function () {
          submitBtn.disabled = (input.value.trim() !== target.trim());
        });
      }
    });
  }

  // --- Document Ready Initialization ---
  document.addEventListener('DOMContentLoaded', function () {
    // Theme setup
    const initialTheme = getPreferredTheme();
    applyTheme(initialTheme);

    const themeToggle = document.getElementById('theme-toggle-btn');
    if (themeToggle) {
      themeToggle.addEventListener('click', function () {
        const current = document.documentElement.getAttribute('data-theme') || 'light';
        const next = current === 'dark' ? 'light' : 'dark';
        applyTheme(next);
      });
    }

    // Global action delegation (print, go-back)
    document.addEventListener('click', function (e) {
      const printBtn = e.target.closest('[data-action="print"]');
      if (printBtn) {
        window.print();
        return;
      }
      const backBtn = e.target.closest('[data-action="go-back"]');
      if (backBtn) {
        window.history.back();
        return;
      }
    });

    // Initialize modules
    initSidebar();
    initToasts();
    initForms();
    initProgressBars();
  });

  function initProgressBars() {
    document.querySelectorAll('.progress-bar[aria-valuenow]').forEach(function (bar) {
      const val = bar.getAttribute('aria-valuenow') || '0';
      bar.style.width = val + '%';
    });
  }
})();
