/**
 * Hedgewar Hospital Management System - Payment Checkout Script
 * Accessible payment mode selection without inline onclick.
 */

(function () {
  'use strict';

  function initPaymentCheckout() {
    const modeRadios = document.querySelectorAll('input[name="payment_mode_radio"]');
    const hiddenModeInput = document.getElementById('paymentMode');
    const bankSection = document.getElementById('bankSelection');
    const bankSelect = document.getElementById('bankSelect');
    const hiddenBankInput = document.getElementById('bankName');
    const payBtn = document.getElementById('pay-submit-btn');

    if (!modeRadios.length || !hiddenModeInput) return;

    modeRadios.forEach(radio => {
      radio.addEventListener('change', function () {
        hiddenModeInput.value = this.value;
        if (this.value === 'netbanking') {
          if (bankSection) bankSection.classList.remove('d-none');
          if (hiddenBankInput && bankSelect) hiddenBankInput.value = bankSelect.value;
        } else {
          if (bankSection) bankSection.classList.add('d-none');
          if (hiddenBankInput) hiddenBankInput.value = '';
        }
        if (payBtn) payBtn.disabled = false;
      });
    });

    if (bankSelect && hiddenBankInput) {
      bankSelect.addEventListener('change', function () {
        hiddenBankInput.value = this.value;
      });
    }
  }

  document.addEventListener('DOMContentLoaded', initPaymentCheckout);
})();
