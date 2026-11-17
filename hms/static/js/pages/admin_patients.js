/**
 * Hedgewar Hospital Management System - Admin Patients Page
 */

(function () {
  'use strict';

  document.addEventListener('DOMContentLoaded', function () {
    const modalEl = document.getElementById('patientProfileModal');
    if (!modalEl) return;

    const profileModal = new bootstrap.Modal(modalEl);
    const avatarEl = document.getElementById('profileAvatar');
    const nameEl = document.getElementById('profileName');
    const emailEl = document.getElementById('profileEmail');
    const idEl = document.getElementById('profileId');
    const apptLink = document.getElementById('profileApptLink');

    document.addEventListener('click', function (e) {
      const btn = e.target.closest('[data-action="view-patient"]');
      if (!btn) return;

      const id = btn.getAttribute('data-id') || '';
      const name = btn.getAttribute('data-name') || '';
      const email = btn.getAttribute('data-email') || '';

      if (avatarEl) avatarEl.textContent = name.charAt(0).toUpperCase();
      if (nameEl) nameEl.textContent = name;
      if (emailEl) emailEl.textContent = email;
      if (idEl) idEl.textContent = `PID-${id}`;
      if (apptLink) {
        apptLink.href = `/admin/appointments?search=${encodeURIComponent(email)}&date=all`;
      }

      profileModal.show();
    });
  });
})();
