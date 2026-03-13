# FMS HR Recruitment Workflow System
### Annexure 1 — R3 | October 2025

> A workflow-driven recruitment management system built with **Flask + MySQL** that automates the internal HR hiring process using stage-based approvals, role permissions, and deadline tracking.
>
> The system strictly follows the HR Recruitment Annexure workflow **(P0 → P14)** with role-based access for HOD, HR Manager, HR Executive, and Site HR.

---

## 1. System Overview

The application manages the complete recruitment lifecycle from job request creation to salary confirmation.

The system enforces:

- Stage-based workflow approvals (P0 – P14)
- Role-based task visibility and action rights
- Time-bound stage deadlines with overdue tracking
- File attachment support at every approval step
- Candidate evaluation loops (accept / reject)
- Dual workflow paths: **Main Path** and **Group-D Path**

---

## 2. Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python 3, Flask, Flask-MySQLdb |
| Frontend | HTML5, Bootstrap 4, Jinja2, JavaScript, jQuery |
| Database | MySQL (InnoDB) — `fms_hr_recruitment_annex1` |
| File Storage | Server filesystem via `static/uploads/` |
| Authentication | Flask session-based login |

---

## 3. System Architecture

```
User Login
     │
     ▼
Dashboard  (role-filtered menu)
     │
     ▼
Recruitment Workflow Panel
     │
     ▼
Stage-Based Task Engine  (P0 → P14)
     │
     ▼
Role-Based Action Buttons
     │
     ▼
MySQL  fms_hr_recruitment_annex1  (UPDATE / INSERT)
```

Each task is visible and actionable by exactly one role per stage.  
The **HR Manager** can view and cancel tasks at any stage.

---

## 4. User Roles

| Role | Responsibility | Employee IDs |
|---|---|---|
| HOD | Create job requests, CV shortlisting, final candidate approval | AR000011 |
| HR Manager | Approve requests, issue LOI, cancel tasks at any stage | AR000004 |
| HR Executive | Group-D check, CV collection, interview scheduling, IT handover | AR000003 |
| Site HR | Group-D path: CV intake, interview scheduling, salary confirmation | AR000003 |

---

## 5. Workflow Stages

### 5.1 Main Recruitment Path

| Stage | Description | Actor | Time Limit | Previous | Next |
|---|---|---|---|---|---|
| P0 | Give recruitment for new post | HOD / Mgmt | Anytime | — Start — | P1 |
| P1 | Is recruitment approved by management? | HR Manager | 4 Hours | P0 | YES → P2 / NO → Closed |
| P2 | Is post for Group-D? | HR Executive | 2 Hours | P1 | YES → P11 / NO → P3 |
| P3 | Confirm JD with HOD & share with consultant | HR Executive | 2 Hours | P2 | P4 |
| P4 | Receive CVs | HR Executive | 2 Days | P3 / P8(NO) | P5 |
| P5 | Send CVs to HOD | HR Executive | 2 Hours | P4 | P6 |
| P6 | Shortlist / Reject CVs & forward to HR | HOD | 1 Day | P5 | P7 |
| P7 | Schedule interview & intimate HOD | HR Executive | 1 Day | P6 | P8 |
| P8 | Is candidate selected after interview? | HOD | 3 Days | P7 | YES → P9 / NO → P4 |
| P9 | Confirm candidate & issue LOI | HR Manager | 2 Days | P8 (YES) | P10 |
| P10 | Share details to IT for resource allocation | HR Executive | 1 Day | P9 | ✓ Closed |

### 5.2 Group-D Path (P2 YES branch)

| Stage | Description | Actor | Time Limit | Previous | Next |
|---|---|---|---|---|---|
| P11 | Receive CVs from HOD / Reference | Site HR | 2 Days | P2 (YES) | P12 |
| P12 | Schedule interview & intimate HOD | Site HR | 3 Days | P11 | P13 |
| P13 | Confirmation of candidate for final selection | HOD | 2 Days | P12 | P14 |
| P14 | Confirm salary as per bracket & sign to PM | Site HR | 1 Day | P13 | ✓ Closed |

---

## 6. Role Permissions

### HR Manager
- Approve or reject recruitment requests (P1)
- Confirm candidate selection and issue LOI (P9)
- Cancel workflow tasks at any point in time

### HR Executive
- Group-D check (P2)
- Confirm JD with HOD (P3)
- Receive and send CVs (P4, P5)
- Schedule interviews (P7)
- Share candidate details with IT (P10)

### HOD
- Create new recruitment requests (P0)
- Shortlist / reject CVs (P6)
- Candidate selection decision after interview (P8)
- Final candidate selection — Group-D path (P13)

### Site HR
- Receive CVs from HOD / References (P11)
- Schedule interview — Group-D path (P12)
- Confirm salary and sign to PM (P14)

---

## 7. Database Schema

**Database:** `fms_hr_recruitment_annex1`

### 7.1 `Employee_Master`

| Column | Type / Notes |
|---|---|
| Emp_Code (PK) | VARCHAR — Primary key, employee ID |
| Person_Accountable | VARCHAR — Full name |
| Designation | VARCHAR |
| Department | VARCHAR |
| Location | VARCHAR |
| Company | VARCHAR |
| Reporting_Manager_ID | VARCHAR — FK to Emp_Code |
| HOD_ID | VARCHAR — FK to Emp_Code |
| Email_ID_Official | VARCHAR |
| Contact_number | VARCHAR |
| Photo_Link | VARCHAR — Relative path in static/ |
| password | VARCHAR |
| user_Access | VARCHAR |
| Admin | VARCHAR |
| STATUS | ENUM: ACTIVE / INACTIVE |

### 7.2 `recruitment_requests`

| Column | Type / Notes |
|---|---|
| id (PK) | INT AUTO_INCREMENT |
| project_id | INT — FK to projects.id |
| job_designation | VARCHAR |
| job_responsibilities | TEXT |
| attachment_path | VARCHAR — Relative to static/ |
| location_id | INT — FK to locations.id |
| reporting_authority_id | VARCHAR — FK to Emp_Code |
| position_type | ENUM: NEW / REPLACEMENT |
| replacement_employee_id | VARCHAR — FK to Emp_Code (nullable) |
| educational_qualification | VARCHAR |
| experience_required | VARCHAR |
| gender_preference | ENUM: ANY / MALE / FEMALE |
| age | INT |
| monthly_gross_salary | VARCHAR |
| number_of_positions | INT |
| additional_note | TEXT |
| workflow_stage | VARCHAR — P0 through P14 |
| status | ENUM: OPEN / CLOSED / CANCELLED |
| stage_started_at | DATETIME |
| deadline_at | DATETIME |
| hr_manager_remarks | TEXT |
| hr_manager_approved_by | VARCHAR |
| hr_manager_approved_at | DATETIME |
| candidate_decision | ENUM: YES / NO (nullable) |
| loi_process_remarks | TEXT |
| loi_processed_by | VARCHAR |
| loi_processed_at | DATETIME |
| site_hr_remarks | TEXT |
| hod_final_remarks | TEXT |
| hod_final_attachment | VARCHAR |
| hod_final_approved_by | VARCHAR |
| hod_final_approved_at | DATETIME |
| salary_confirmation_remarks | TEXT |
| salary_confirmed_by | VARCHAR |
| salary_confirmed_at | DATETIME |
| workflow_remarks | TEXT |
| workflow_attachment | VARCHAR |
| workflow_updated_by | VARCHAR |
| workflow_updated_at | DATETIME |

### 7.3 `projects`

| Column | Type / Notes |
|---|---|
| id (PK) | INT AUTO_INCREMENT |
| project_name | VARCHAR |

### 7.4 `locations`

| Column | Type / Notes |
|---|---|
| id (PK) | INT AUTO_INCREMENT |
| project_id | INT — FK to projects.id |
| location_name | VARCHAR |

### 7.5 `Password_Records`

| Column | Type / Notes |
|---|---|
| id (PK) | INT AUTO_INCREMENT |
| Emp_Code | VARCHAR — FK to Employee_Master |
| New_Password | VARCHAR |
| changed_at | DATETIME (default NOW) |

---

## 8. API Endpoints

| Method | Route | Function | Description |
|---|---|---|---|
| GET/POST | `/` | `login` | User login |
| GET | `/dashboard` | `dashboard` | Role-filtered dashboard |
| GET/POST | `/forgot_password` | `forgot_password` | Change password |
| GET | `/logout` | `logout` | Clear session |
| POST | `/upload_photo` | `upload_photo` | Update profile photo |
| GET | `/recruitment` | `fms_hr_recruitment_panel` | Recruitment workflow panel |
| POST | `/recruitment/create` | `fms_hr_recruitment_create` | Create new request (HOD) |
| POST | `/recruitment/<id>/approve` | `fms_hr_recruitment_approve` | P1: HR Manager YES/NO decision |
| POST | `/recruitment/<id>/groupd` | `fms_hr_recruitment_groupd_check` | P2: Group-D YES→P11 / NO→P3 |
| POST | `/recruitment/<id>/stage_approve` | `fms_hr_recruitment_stage_approve` | P3–P7: General stage advance |
| POST | `/recruitment/<id>/candidate_decision` | `fms_hr_recruitment_candidate_decision` | P8: HOD YES→P9 / NO→P4 |
| POST | `/recruitment/<id>/loi_process` | `fms_hr_recruitment_loi_process` | P9–P10: LOI / IT handover → Closed |
| POST | `/recruitment/<id>/sitehr_approve` | `fms_hr_recruitment_sitehr_approve` | P11–P12: Site HR advance |
| POST | `/recruitment/<id>/hod_final_approve` | `fms_hr_recruitment_hod_final_approve` | P13: HOD final selection |
| POST | `/recruitment/<id>/salary_confirm` | `fms_hr_recruitment_salary_confirm` | P14: Confirm salary → Closed |
| POST | `/recruitment/<id>/cancel` | `fms_hr_recruitment_cancel` | HR Manager cancel at any stage |
| POST | `/recruitment/<id>/next` | `fms_hr_recruitment_next_stage` | Generic next-stage advance |
| GET | `/locations/<project_id>` | `fms_hr_recruitment_get_locations` | AJAX: fetch locations by project |

---

## 9. Recruitment Form Fields

| Field | Type | Required |
|---|---|---|
| Project | Dropdown (from DB) | Yes |
| Job Designation | Text input | Yes |
| Job Responsibilities | Textarea | Yes |
| Attachment | File upload | No |
| Location | Dropdown (AJAX) | Yes |
| Reporting Authority | Employee dropdown | Yes |
| Position Type | NEW / REPLACEMENT | Yes |
| Replacement Employee | Employee dropdown | Conditional |
| Educational Qualification | Text input | Yes |
| Experience Required | Dropdown | Yes |
| Gender Preference | ANY / MALE / FEMALE | Yes |
| Age | Number | No |
| Monthly Gross Salary | Text / Numeric | No |
| Number of Positions | Dropdown (1–10) | Yes |
| Additional Notes | Textarea | No |

---

## 10. Security

### Session Authentication
- All routes check for `session['emp_code']` before processing
- Unauthorized requests are redirected to `/login`
- Session stores: `emp_code`, `designation`, `department`, `photo`, `user_Access`

### Role-Based Access Control
- Tasks are filtered by `fms_hr_recruitment_can_view_task()` — users only see tasks assigned to their role
- Each action route validates the caller's `emp_code` against the authorised ID set
- Unauthorised action calls return HTTP `403` JSON error
- HR Manager has cross-stage read access and cancel rights at all times

---

## 11. Deadline System

| Stage | Time Limit |
|---|---|
| P1 | 4 Hours |
| P2 | 2 Hours |
| P3 | 2 Hours |
| P4 | 2 Days |
| P5 | 2 Hours |
| P6 | 1 Day |
| P7 | 1 Day |
| P8 | 3 Days |
| P9 | 2 Days |
| P10 | 1 Day |
| P11 | 2 Days |
| P12 | 3 Days |
| P13 | 2 Days |
| P14 | 1 Day |

Deadline is calculated as `datetime.now() + timedelta(seconds=STAGE_TIME_LIMITS[stage])` and stored in `deadline_at`. The workflow panel shows **Overdue** in red if `deadline_at < now`.

---

## 12. UI Components

| Component | Description |
|---|---|
| Top Navbar | Sticky dark navbar with brand, nav links, profile chip (photo + name + emp ID), Back to Dashboard, logout |
| Recruitment Panel | Bootstrap table showing only tasks visible to the logged-in role with role-gated action buttons |
| Create Form Modal | Large Bootstrap modal (HOD only) for submitting new recruitment requests |
| Approval Modal | HR Manager YES/NO decision modal with dynamic button colour (green = approve / red = reject) |
| Group-D Modal | HR Executive decision modal routing to P11 (YES) or P3 (NO) |
| Workflow Modal | General stage-advance modal with remarks and optional file attachment |
| Candidate Modal | HOD interview decision modal (YES→P9, NO→P4) with attachment |
| LOI Modal | HR Manager (P9) and HR Executive (P10) LOI processing modal |
| Site HR Modal | Site HR remarks modal for P11 / P12 |
| HOD Final Modal | HOD final selection modal with assessment attachment (P13) |
| Salary Modal | Site HR salary confirmation modal — closes task on submit (P14) |

---

## 13. Folder Structure

```
project/
│
├── app.py                        # Main Flask application
│
├── templates/
│    ├── login.html
│    ├── dashboard.html
│    ├── recruitment.html          # Workflow panel
│    └── forgot_password.html
│
├── static/
│    ├── images/
│    │    └── Logo.png
│    └── uploads/
│         ├── profile_photos/      # Employee photos
│         ├── recruitment/         # Request attachments
│         ├── workflow/            # Stage attachments
│         ├── candidate_decision/
│         ├── loi_process/
│         ├── hod_final/
│         └── salary_confirmation/
│
└── requirements.txt
```

---

## 14. Installation

### Install dependencies
```bash
pip install flask flask-mysqldb
```

### Configure database connection in `app.py`
```python
app.config['MYSQL_HOST']     = 'localhost'
app.config['MYSQL_USER']     = 'root'
app.config['MYSQL_PASSWORD'] = 'your_password'
app.config['MYSQL_DB']       = 'fms_hr_recruitment_annex1'
```

### Run server
```bash
python app.py
```

Application runs at: `http://127.0.0.1:5001`

---

## 15. Future Enhancements

- AI Job Description Generator — auto-generate JD from designation and department
- Email Notifications — alert next approver when a task advances
- Candidate Pipeline Management — track multiple candidates per request
- Analytics Dashboard — hiring statistics, average TAT per stage, bottleneck detection
- HR Score System — deadline-violation tracking with penalty points
- Password Hashing — migrate from plain-text to bcrypt
- Audit Log Table — full history of who acted on what stage and when

---

## 16. Author

**Tathagata Sengupta**  
FMS HR Recruitment Workflow System — Annexure 1  
Version R3 | October 2025

#   h r - e x i t - a l c o v e  
 