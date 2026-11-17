/**
 * Hedgewar Hospital Management System - Booking Wizard Page Script
 * Multi-step accessible stepper, server-side slot availability, zero inline JS.
 */

(function () {
  'use strict';

  function initBookingWizard() {
    const wizardForm = document.getElementById('booking-wizard-form');
    if (!wizardForm) return;

    let currentStep = 1;
    const totalSteps = 4;

    const deptSelect = document.getElementById('wizard-dept');
    const doctorCards = document.querySelectorAll('.wizard-doctor-card');
    const selectedDoctorInput = document.getElementById('wizard-selected-doctor');
    const dateInput = document.getElementById('wizard-date');
    const slotContainer = document.getElementById('wizard-slots-container');
    const selectedTimeInput = document.getElementById('wizard-selected-time');
    const reasonInput = document.getElementById('wizard-reason');

    const nextBtn = document.getElementById('wizard-next-btn');
    const prevBtn = document.getElementById('wizard-prev-btn');
    const submitBtn = document.getElementById('wizard-submit-btn');

    // Review elements
    const revDept = document.getElementById('review-dept');
    const revDoctor = document.getElementById('review-doctor');
    const revDate = document.getElementById('review-date');
    const revTime = document.getElementById('review-time');
    const revReason = document.getElementById('review-reason');

    // Slots definition (standard clinic hours: 09:00 AM - 05:00 PM)
    const STANDARD_SLOTS = [
      '09:00 AM', '09:30 AM', '10:00 AM', '10:30 AM',
      '11:00 AM', '11:30 AM', '12:00 PM', '12:30 PM',
      '02:00 PM', '02:30 PM', '03:00 PM', '03:30 PM',
      '04:00 PM', '04:30 PM'
    ];

    function updateStepper() {
      document.querySelectorAll('.hms-step').forEach((el, idx) => {
        const stepNum = idx + 1;
        el.classList.toggle('active', stepNum === currentStep);
        el.classList.toggle('completed', stepNum < currentStep);
      });

      document.querySelectorAll('.wizard-panel').forEach((panel, idx) => {
        const stepNum = idx + 1;
        panel.classList.toggle('d-none', stepNum !== currentStep);
      });

      if (prevBtn) {
        prevBtn.classList.toggle('d-none', currentStep === 1);
      }

      if (nextBtn && submitBtn) {
        if (currentStep === totalSteps) {
          nextBtn.classList.add('d-none');
          submitBtn.classList.remove('d-none');
          updateReview();
        } else {
          nextBtn.classList.remove('d-none');
          submitBtn.classList.add('d-none');
        }
      }
    }

    function filterDoctorsByDept(dept) {
      doctorCards.forEach(card => {
        const cardDept = card.getAttribute('data-doctor-dept');
        if (!dept || cardDept.toLowerCase() === dept.toLowerCase()) {
          card.classList.remove('d-none');
        } else {
          card.classList.add('d-none');
          if (card.classList.contains('selected')) {
            card.classList.remove('selected');
            selectedDoctorInput.value = '';
          }
        }
      });
    }

    function selectDoctorCard(card) {
      doctorCards.forEach(c => c.classList.remove('selected'));
      card.classList.add('selected');
      const docName = card.getAttribute('data-doctor-name');
      selectedDoctorInput.value = docName;
      loadAvailableSlots();
    }

    doctorCards.forEach(card => {
      card.addEventListener('click', function () {
        selectDoctorCard(this);
      });
      card.addEventListener('keydown', function (e) {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          selectDoctorCard(this);
        }
      });
    });

    if (deptSelect) {
      deptSelect.addEventListener('change', function () {
        filterDoctorsByDept(this.value);
      });
    }

    function loadAvailableSlots() {
      const doc = selectedDoctorInput.value;
      const dateVal = dateInput ? dateInput.value : '';

      if (!slotContainer) return;
      slotContainer.innerHTML = '';

      if (!doc || !dateVal) {
        slotContainer.innerHTML = '<p class="text-xs text-muted mb-0">Please select a doctor and date first.</p>';
        return;
      }

      slotContainer.innerHTML = '<div class="py-3 text-center text-muted"><i class="fa-solid fa-spinner fa-spin me-2"></i>Checking live slot availability...</div>';

      const csrfMeta = document.querySelector('meta[name="csrf-token"]');
      const csrfToken = csrfMeta ? csrfMeta.getAttribute('content') : '';

      fetch('/get_booked_slots', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': csrfToken
        },
        body: JSON.stringify({ doctor: doc, date: dateVal })
      })
      .then(res => res.json())
      .then(bookedSlots => {
        slotContainer.innerHTML = '';
        const grid = document.createElement('div');
        grid.className = 'd-flex flex-wrap gap-2';

        const bookedSet = new Set(bookedSlots.map(s => s.trim().toUpperCase()));

        STANDARD_SLOTS.forEach(slot => {
          const isBooked = bookedSet.has(slot.toUpperCase());
          const slotBtn = document.createElement('button');
          slotBtn.type = 'button';
          slotBtn.className = isBooked
            ? 'btn-hms btn-hms-sm btn-hms-secondary disabled text-muted'
            : 'btn-hms btn-hms-sm btn-hms-secondary wizard-slot-btn';
          slotBtn.textContent = slot;
          if (isBooked) {
            slotBtn.disabled = true;
            slotBtn.title = 'Slot taken';
          } else {
            slotBtn.addEventListener('click', function () {
              grid.querySelectorAll('.wizard-slot-btn').forEach(b => b.classList.remove('btn-hms-primary', 'active'));
              slotBtn.classList.add('btn-hms-primary', 'active');
              selectedTimeInput.value = slot;
            });
          }
          grid.appendChild(slotBtn);
        });

        slotContainer.appendChild(grid);
      })
      .catch(() => {
        slotContainer.innerHTML = '<p class="text-xs text-danger mb-0">Could not fetch slots. Please check your connection.</p>';
      });
    }

    if (dateInput) {
      dateInput.addEventListener('change', loadAvailableSlots);
    }

    function updateReview() {
      if (revDept) revDept.textContent = deptSelect ? deptSelect.value || 'Not selected' : '—';
      if (revDoctor) revDoctor.textContent = selectedDoctorInput.value || 'Not selected';
      if (revDate) revDate.textContent = dateInput ? dateInput.value || 'Not selected' : '—';
      if (revTime) revTime.textContent = selectedTimeInput.value || 'Not selected';
      if (revReason) revReason.textContent = reasonInput ? reasonInput.value || 'General Consultation' : '—';
    }

    function validateCurrentStep() {
      if (currentStep === 1) {
        if (deptSelect && !deptSelect.value) {
          alert('Please select a department to proceed.');
          return false;
        }
      } else if (currentStep === 2) {
        if (!selectedDoctorInput.value) {
          alert('Please select a physician from the list.');
          return false;
        }
      } else if (currentStep === 3) {
        if (!dateInput || !dateInput.value) {
          alert('Please choose an appointment date.');
          return false;
        }
        if (!selectedTimeInput.value) {
          alert('Please pick an available time slot.');
          return false;
        }
      } else if (currentStep === 4) {
        if (!reasonInput || !reasonInput.value.trim()) {
          alert('Please describe your medical symptoms or consultation reason.');
          return false;
        }
      }
      return true;
    }

    if (nextBtn) {
      nextBtn.addEventListener('click', function () {
        if (validateCurrentStep()) {
          currentStep = Math.min(totalSteps, currentStep + 1);
          updateStepper();
        }
      });
    }

    if (prevBtn) {
      prevBtn.addEventListener('click', function () {
        currentStep = Math.max(1, currentStep - 1);
        updateStepper();
      });
    }

    // Set minimum date to today
    if (dateInput) {
      const today = new Date().toISOString().split('T')[0];
      dateInput.min = today;
      if (!dateInput.value) {
        dateInput.value = today;
      }
    }

    // Check pre-selected doctor / dept from query string
    const preDept = wizardForm.getAttribute('data-pre-dept');
    const preDoc = wizardForm.getAttribute('data-pre-doc');

    if (preDept && deptSelect) {
      deptSelect.value = preDept;
      filterDoctorsByDept(preDept);
    }
    if (preDoc) {
      doctorCards.forEach(c => {
        if (c.getAttribute('data-doctor-name') === preDoc) {
          selectDoctorCard(c);
        }
      });
    }

    updateStepper();
  }

  document.addEventListener('DOMContentLoaded', initBookingWizard);
})();
