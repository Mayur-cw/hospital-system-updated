/**
 * Hedgewar Hospital Management System - Directory Live Search
 * Accessible, debounced client-side filter without inline onkeyup/onclick.
 */

(function () {
  'use strict';

  document.addEventListener('DOMContentLoaded', function () {
    const searchInputs = document.querySelectorAll('[data-directory-search]');

    searchInputs.forEach(input => {
      const targetSelector = input.getAttribute('data-directory-search');
      const items = document.querySelectorAll(targetSelector);
      const clearBtn = input.closest('.topbar-search, .input-group')?.querySelector('.search-clear-btn');
      const counter = document.getElementById(input.getAttribute('data-count-target'));

      function filter() {
        const q = input.value.toLowerCase().trim();
        let visible = 0;

        items.forEach(item => {
          const text = (item.getAttribute('data-search-text') || item.textContent).toLowerCase();
          const matches = (!q || text.includes(q));
          item.classList.toggle('d-none', !matches);
          if (matches) visible++;
        });

        if (counter) {
          counter.textContent = `${visible} records`;
        }
      }

      input.addEventListener('input', filter);

      if (clearBtn) {
        clearBtn.addEventListener('click', function () {
          input.value = '';
          filter();
          input.focus();
        });
      }
    });
  });
})();
