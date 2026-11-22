// Sign-in interactions are isolated from the restored application's shared layout.
(() => {
  'use strict';
  document.querySelectorAll('[data-password-toggle]').forEach(button => {
    button.addEventListener('click', () => {
      const input = document.getElementById(button.dataset.passwordToggle);
      const show = input.type === 'password';
      input.type = show ? 'text' : 'password';
      button.setAttribute('aria-label', show ? 'Hide password' : 'Show password');
      button.setAttribute('aria-pressed', String(show));
    });
  });
  document.querySelectorAll('[data-demo-email]').forEach(button => {
    button.addEventListener('click', () => {
      const form = document.getElementById('login-form');
      form.elements.email.value = button.dataset.demoEmail;
      form.elements.password.value = button.dataset.demoPassword;
      form.requestSubmit();
    });
  });
  document.querySelectorAll('[data-dismiss-toast]').forEach(button => {
    button.addEventListener('click', () => button.closest('.workspace-toast').remove());
  });
})();
