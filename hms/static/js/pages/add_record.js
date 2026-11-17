/**
 * Hedgewar Hospital Management System - Add Record Admission Toggle
 */

(function () {
  'use strict';

  document.addEventListener('DOMContentLoaded', function () {
    const admitToggle = document.getElementById('admitToggle');
    const admissionSection = document.getElementById('admissionSection');
    const roomSelect = document.getElementById('room_id');

    if (!admitToggle || !admissionSection) return;

    admitToggle.addEventListener('change', function () {
      if (this.checked) {
        admissionSection.classList.remove('d-none');
        if (roomSelect) roomSelect.required = true;
      } else {
        admissionSection.classList.add('d-none');
        if (roomSelect) {
          roomSelect.required = false;
          roomSelect.value = '';
        }
      }
    });
  });
})();
