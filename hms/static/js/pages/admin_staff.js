/**
 * Hedgewar Hospital Management System - Admin Staff Management
 */

(function () {
  'use strict';

  document.addEventListener('DOMContentLoaded', function () {
    // Edit modal
    const editModalEl = document.getElementById('editStaffModal');
    const editModal = editModalEl ? new bootstrap.Modal(editModalEl) : null;
    const editStaffId = document.getElementById('editStaffId');
    const editStaffName = document.getElementById('editStaffName');
    const editStaffEmail = document.getElementById('editStaffEmail');

    // Password modal
    const pwModalEl = document.getElementById('changePasswordModal');
    const pwModal = pwModalEl ? new bootstrap.Modal(pwModalEl) : null;
    const pwStaffId = document.getElementById('pwStaffId');
    const pwStaffName = document.getElementById('pwStaffName');
    const newPwField = document.getElementById('newPwField');
    const confirmPwField = document.getElementById('confirmPwField');

    // Delete modal
    const deleteModalEl = document.getElementById('deleteStaffModal');
    const deleteModal = deleteModalEl ? new bootstrap.Modal(deleteModalEl) : null;
    const deleteStaffId = document.getElementById('deleteStaffId');
    const deleteStaffName = document.getElementById('deleteStaffName');

    document.addEventListener('click', function (e) {
      // Edit button
      const editBtn = e.target.closest('[data-action="edit-staff"]');
      if (editBtn && editModal) {
        if (editStaffId) editStaffId.value = editBtn.getAttribute('data-id') || '';
        if (editStaffName) editStaffName.value = editBtn.getAttribute('data-name') || '';
        if (editStaffEmail) editStaffEmail.value = editBtn.getAttribute('data-email') || '';
        editModal.show();
        return;
      }

      // Password button
      const pwBtn = e.target.closest('[data-action="change-password"]');
      if (pwBtn && pwModal) {
        if (pwStaffId) pwStaffId.value = pwBtn.getAttribute('data-id') || '';
        if (pwStaffName) pwStaffName.textContent = pwBtn.getAttribute('data-name') || '';
        if (newPwField) newPwField.value = '';
        if (confirmPwField) confirmPwField.value = '';
        pwModal.show();
        return;
      }

      // Delete button
      const delBtn = e.target.closest('[data-action="delete-staff"]');
      if (delBtn && deleteModal) {
        if (deleteStaffId) deleteStaffId.value = delBtn.getAttribute('data-id') || '';
        if (deleteStaffName) deleteStaffName.textContent = delBtn.getAttribute('data-name') || '';
        deleteModal.show();
        return;
      }

      // Password visibility toggle
      const pwToggle = e.target.closest('[data-action="toggle-pw"]');
      if (pwToggle) {
        const targetId = pwToggle.getAttribute('data-target');
        const targetInput = document.getElementById(targetId);
        if (targetInput) {
          const isText = targetInput.type === 'text';
          targetInput.type = isText ? 'password' : 'text';
          const icon = pwToggle.querySelector('i');
          if (icon) {
            icon.className = isText ? 'fas fa-eye' : 'fas fa-eye-slash';
          }
        }
      }
    });
  });
})();
