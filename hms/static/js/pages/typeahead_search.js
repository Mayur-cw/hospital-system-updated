/**
 * Hedgewar Hospital Management System - Global Typeahead Search (F-02)
 * Debounced, keyboard-navigable, accessible ARIA combobox.
 */

(function () {
  'use strict';

  document.addEventListener('DOMContentLoaded', function () {
    const searchForms = document.querySelectorAll('.topbar-search');

    searchForms.forEach(form => {
      const input = form.querySelector('input[type="search"]');
      if (!input) return;

      // Create dropdown container
      const dropdown = document.createElement('div');
      dropdown.className = 'typeahead-dropdown shadow-lg d-none';
      dropdown.setAttribute('role', 'listbox');
      dropdown.id = `typeahead-${Math.random().toString(36).substr(2, 9)}`;
      input.setAttribute('aria-expanded', 'false');
      input.setAttribute('aria-autocomplete', 'list');
      input.setAttribute('aria-controls', dropdown.id);
      form.style.position = 'relative';
      form.appendChild(dropdown);

      let debounceTimer = null;
      let activeIndex = -1;

      function renderResults(results) {
        dropdown.innerHTML = '';
        activeIndex = -1;

        if (!results || results.length === 0) {
          dropdown.innerHTML = '<div class="p-3 text-muted text-xs text-center">No matching records found.</div>';
          dropdown.classList.remove('d-none');
          input.setAttribute('aria-expanded', 'true');
          return;
        }

        results.forEach((item, index) => {
          const opt = document.createElement('a');
          opt.href = item.url;
          opt.className = 'typeahead-item d-flex align-items-center justify-content-between p-2 px-3 text-decoration-none border-bottom';
          opt.setAttribute('role', 'option');
          opt.id = `${dropdown.id}-opt-${index}`;

          const iconClass = item.category === 'Doctor' ? 'fa-user-doctor text-primary' : 'fa-hospital-user text-info';

          opt.innerHTML = `
            <div class="d-flex align-items-center gap-2 overflow-hidden">
              <i class="fa-solid ${iconClass}"></i>
              <div class="overflow-hidden">
                <div class="fw-semibold text-dark text-sm text-truncate">${item.title}</div>
                <div class="text-xs text-muted text-truncate">${item.subtitle || ''}</div>
              </div>
            </div>
            <span class="badge bg-surface-subtle text-secondary border text-xs ms-2">${item.category}</span>
          `;
          dropdown.appendChild(opt);
        });

        dropdown.classList.remove('d-none');
        input.setAttribute('aria-expanded', 'true');
      }

      function closeDropdown() {
        dropdown.classList.add('d-none');
        input.setAttribute('aria-expanded', 'false');
        activeIndex = -1;
      }

      input.addEventListener('input', function () {
        clearTimeout(debounceTimer);
        const q = input.value.trim();
        if (q.length < 2) {
          closeDropdown();
          return;
        }

        debounceTimer = setTimeout(() => {
          fetch(`/api/v1/search?q=${encodeURIComponent(q)}`)
            .then(res => res.json())
            .then(data => {
              renderResults(data.results || []);
            })
            .catch(() => {
              closeDropdown();
            });
        }, 200);
      });

      // Keyboard navigation
      input.addEventListener('keydown', function (e) {
        const items = dropdown.querySelectorAll('.typeahead-item');
        if (dropdown.classList.contains('d-none') || items.length === 0) return;

        if (e.key === 'ArrowDown') {
          e.preventDefault();
          activeIndex = (activeIndex + 1) % items.length;
          updateActiveItem(items);
        } else if (e.key === 'ArrowUp') {
          e.preventDefault();
          activeIndex = (activeIndex - 1 + items.length) % items.length;
          updateActiveItem(items);
        } else if (e.key === 'Enter' && activeIndex >= 0) {
          e.preventDefault();
          items[activeIndex].click();
        } else if (e.key === 'Escape') {
          closeDropdown();
        }
      });

      function updateActiveItem(items) {
        items.forEach((item, idx) => {
          const isSelected = (idx === activeIndex);
          item.classList.toggle('active', isSelected);
          if (isSelected) {
            item.scrollIntoView({ block: 'nearest' });
            input.setAttribute('aria-activedescendant', item.id);
          }
        });
      }

      // Close on outside click
      document.addEventListener('click', function (e) {
        if (!form.contains(e.target)) {
          closeDropdown();
        }
      });
    });
  });
})();
