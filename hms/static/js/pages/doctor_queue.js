/**
 * Hedgewar Hospital Management System - Doctor Queue Page Script
 * Filters queue rows without inline onclick or styles.
 */

(function () {
  'use strict';

  function initDoctorQueue() {
    const filterButtons = document.querySelectorAll('[data-queue-filter]');
    const queueRows = document.querySelectorAll('.queue-row');
    const queueTitle = document.getElementById('queue-title');
    const emptyMsg = document.getElementById('empty-queue-msg');

    if (!filterButtons.length || !queueRows.length) return;

    function applyFilter(category) {
      sessionStorage.setItem('activeQueueFilter', category);

      filterButtons.forEach(btn => {
        const isCurrent = btn.getAttribute('data-queue-filter') === category;
        btn.classList.toggle('active', isCurrent);
      });

      let visible = 0;
      queueRows.forEach(row => {
        const rowCategory = row.getAttribute('data-category');
        if (category === 'all' || rowCategory === category) {
          row.classList.remove('d-none');
          visible++;
        } else {
          row.classList.add('d-none');
        }
      });

      if (emptyMsg) {
        if (visible === 0) {
          emptyMsg.classList.remove('d-none');
        } else {
          emptyMsg.classList.add('d-none');
        }
      }

      if (queueTitle) {
        const titleMap = {
          'all': 'Live Patient Queue — Total Today',
          'waiting': 'Queue — Waiting Patients',
          'completed': 'Queue — Completed Consultations',
          'pending_rx': 'Queue — Pending Prescription'
        };
        queueTitle.textContent = titleMap[category] || 'Live Patient Queue';
      }
    }

    filterButtons.forEach(btn => {
      btn.addEventListener('click', function () {
        const cat = this.getAttribute('data-queue-filter');
        applyFilter(cat);
      });
    });

    const saved = sessionStorage.getItem('activeQueueFilter') || 'all';
    applyFilter(saved);
  }

  document.addEventListener('DOMContentLoaded', initDoctorQueue);
})();
