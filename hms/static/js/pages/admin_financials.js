/**
 * Hedgewar Hospital Management System - Admin Financials Filter
 */

(function () {
  'use strict';

  document.addEventListener('DOMContentLoaded', function () {
    const filterCards = document.querySelectorAll('[data-action="filter-bills"]');
    const rows = document.querySelectorAll('.bill-row');
    const rowCountLabel = document.getElementById('rowCountLabel');
    const emptyMsg = document.getElementById('emptyMsg');

    function applyFilter(targetStatus) {
      filterCards.forEach(card => {
        const filter = card.getAttribute('data-filter');
        if (filter === targetStatus) {
          card.classList.remove('opacity-50');
          card.classList.add('border-primary');
        } else {
          card.classList.add('opacity-50');
          card.classList.remove('border-primary');
        }
      });

      let visibleCount = 0;
      rows.forEach(row => {
        const status = row.getAttribute('data-status');
        const matches = (targetStatus === 'All' || status === targetStatus);
        row.classList.toggle('d-none', !matches);
        if (matches) visibleCount++;
      });

      if (rowCountLabel) {
        rowCountLabel.textContent = `${visibleCount} Records`;
      }
      if (emptyMsg) {
        emptyMsg.classList.toggle('d-none', visibleCount > 0);
      }
    }

    document.addEventListener('click', function (e) {
      const trigger = e.target.closest('[data-action="filter-bills"]');
      if (trigger) {
        const filter = trigger.getAttribute('data-filter') || 'All';
        applyFilter(filter);
      }
    });
  });
})();
