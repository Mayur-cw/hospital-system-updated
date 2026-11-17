/**
 * Hedgewar Hospital Management System - Admin Appointments Script
 */

(function () {
  'use strict';

  document.addEventListener('DOMContentLoaded', function () {
    const tabs = document.querySelectorAll('[data-admin-appt-tab]');
    const rows = document.querySelectorAll('.admin-appt-row');
    const searchInput = document.getElementById('admin-appt-search');
    const counter = document.getElementById('admin-appt-count');
    const emptyRow = document.getElementById('empty-admin-appts');

    let activeFilter = 'all';

    function filterTable() {
      const q = (searchInput ? searchInput.value : '').toLowerCase().trim();
      let visible = 0;

      rows.forEach(row => {
        const cat = row.getAttribute('data-status-category');
        const text = row.textContent.toLowerCase();

        const matchCat = (activeFilter === 'all' || cat === activeFilter);
        const matchQ = (!q || text.includes(q));

        if (matchCat && matchQ) {
          row.classList.remove('d-none');
          visible++;
        } else {
          row.classList.add('d-none');
        }
      });

      if (counter) counter.textContent = `${visible} records`;
      if (emptyRow) emptyRow.classList.toggle('d-none', visible > 0);
    }

    tabs.forEach(tab => {
      tab.addEventListener('click', function () {
        tabs.forEach(t => t.classList.remove('active', 'btn-hms-primary'));
        this.classList.add('active', 'btn-hms-primary');
        activeFilter = this.getAttribute('data-admin-appt-tab');
        filterTable();
      });
    });

    if (searchInput) {
      searchInput.addEventListener('input', filterTable);
    }
  });
})();
