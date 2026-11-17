/**
 * Hedgewar Hospital Management System - Appointment History Script
 * Filters appointment rows by status tab and search query without inline scripts.
 */

(function () {
  'use strict';

  function initAppointmentHistory() {
    const filterTabs = document.querySelectorAll('[data-appt-tab]');
    const rows = document.querySelectorAll('.appt-row');
    const searchInput = document.getElementById('appt-search-input');
    const rowCounter = document.getElementById('visibleRowCount');
    const emptyRow = document.getElementById('empty-appts-row');

    if (!rows.length) return;

    let activeCategory = 'all';

    function applyFilter() {
      const query = (searchInput ? searchInput.value : '').toLowerCase().trim();
      let visible = 0;

      rows.forEach(row => {
        const cat = row.getAttribute('data-category');
        const name = (row.getAttribute('data-name') || '').toLowerCase();
        const date = (row.getAttribute('data-date') || '').toLowerCase();

        const matchesCat = (activeCategory === 'all' || cat.toLowerCase() === activeCategory.toLowerCase());
        const matchesQuery = (!query || name.includes(query) || date.includes(query));

        if (matchesCat && matchesQuery) {
          row.classList.remove('d-none');
          visible++;
        } else {
          row.classList.add('d-none');
        }
      });

      if (rowCounter) {
        rowCounter.textContent = `${visible} records`;
      }

      if (emptyRow) {
        emptyRow.classList.toggle('d-none', visible > 0);
      }
    }

    filterTabs.forEach(tab => {
      tab.addEventListener('click', function () {
        filterTabs.forEach(t => t.classList.remove('active', 'btn-hms-primary'));
        this.classList.add('active', 'btn-hms-primary');
        activeCategory = this.getAttribute('data-appt-tab');
        applyFilter();
      });
    });

    if (searchInput) {
      searchInput.addEventListener('input', applyFilter);
    }

    // Check URL query string for pre-selected filter e.g. ?filter=Pending or ?filter=Completed
    const params = new URLSearchParams(window.location.search);
    const filterParam = params.get('filter');
    if (filterParam) {
      activeCategory = filterParam.toLowerCase();
      filterTabs.forEach(tab => {
        if (tab.getAttribute('data-appt-tab').toLowerCase() === activeCategory) {
          filterTabs.forEach(t => t.classList.remove('active', 'btn-hms-primary'));
          tab.classList.add('active', 'btn-hms-primary');
        }
      });
    }

    applyFilter();
  }

  document.addEventListener('DOMContentLoaded', initAppointmentHistory);
})();
