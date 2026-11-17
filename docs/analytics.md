# Hospital Operations & Clinical Analytics

**Hedgewar Hospital Care — Operations & Business Intelligence**

---

## 1. Executive Analytics Overview

Hedgewar Hospital Care provides real-time operational reporting and administrative analytics across outpatient volume, bed occupancy rates, departmental revenue, and clinician caseloads.

All analytics endpoints respect Role-Based Access Control (RBAC):
- **Administrators:** Full access to clinical, financial, and bed utilization dashboards, plus automated CSV exports.
- **Clinicians:** Access to their specific patient volume, wait time metrics, and completed consultations.
- **Receptionists:** Front-desk registration velocity and daily cash settlement audit summaries.

---

## 2. Key Operational Metrics & Formulas

### Bed Occupancy Rate (BOR)
Measures the percentage of inpatient beds occupied at any given time:
$$\text{BOR} = \left( \frac{\text{Total Occupied Beds}}{\text{Total Operational Beds}} \right) \times 100$$
- **Target Range:** 75% – 85% (optimal clinical staffing and emergency buffer).

### Average Length of Stay (ALOS)
Evaluates inpatient clinical efficiency and recovery velocity:
$$\text{ALOS} = \frac{\sum (\text{Discharge Date} - \text{Admission Date})}{\text{Total Discharged Inpatients}}$$

### Outpatient No-Show Rate
Monitors clinic slot utilization and patient attendance:
$$\text{No-Show Rate} = \left( \frac{\text{Missed Appointments}}{\text{Scheduled} + \text{Completed} + \text{Missed}} \right) \times 100$$

### Revenue Realization Rate
Tracks hospital invoice settlement efficiency:
$$\text{Realization Rate} = \left( \frac{\sum \text{Settled Payments}}{\sum \text{Total Invoiced Amount}} \right) \times 100$$

---

## 3. Administrative CSV Data Exports (F-09)

Administrators can extract sanitized, HIPAA-aligned reporting streams in standard CSV format from `/admin/reports`:

1. **Appointments Export (`/admin/export/appointments.csv`):**
   - Columns: `Appointment ID`, `Date`, `Time`, `Department`, `Doctor Name`, `Patient ID`, `Status`, `Cancellation Reason`.
   - Filters: Date range (`from_date`, `to_date`), department, and status.

2. **Inpatient Admissions Export (`/admin/export/admissions.csv`):**
   - Columns: `Admission ID`, `Patient ID`, `Doctor Name`, `Room Number`, `Ward Type`, `Admitted At`, `Discharged At`, `Length of Stay (Days)`, `Total Bill (₹)`, `Status`.

3. **Financial Revenue Ledger (`/admin/export/financials.csv`):**
   - Columns: `Invoice ID`, `Invoice Number`, `Patient ID`, `Service Type`, `Issued Date`, `Subtotal`, `Discount`, `Tax`, `Total (₹)`, `Payment Method`, `Settlement Status`.
