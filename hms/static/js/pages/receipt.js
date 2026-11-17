/**
 * Hedgewar Hospital Management System - Printable Receipt Script
 */

(function () {
  'use strict';

  document.addEventListener('DOMContentLoaded', function () {
    const printBtn = document.getElementById('print-receipt-btn');
    if (printBtn) {
      printBtn.addEventListener('click', function () {
        window.print();
      });
    }
  });
})();
