# ============================================================
# HR EXIT PROCESS — Flask App  (Updated)
# DB : alcovedb_2024 (Employee_Master, Password_Records)
#      fms_exit_process_annex (exit_requests, exit_stage_log)
#      alcove_checklist (holidaylist)
# ============================================================
from flask import Flask, render_template, request, redirect, flash, url_for, session, jsonify
from flask_mysqldb import MySQL
from werkzeug.utils import secure_filename
from MySQLdb.cursors import DictCursor
import os
from datetime import datetime, timedelta, time as dt_time

# ================================== App + DB Config ==========================================

app = Flask(__name__)
app.secret_key = "secret_key_here"

app.config['MYSQL_HOST']     = 'localhost'
app.config['MYSQL_USER']     = 'root'
app.config['MYSQL_PASSWORD'] = 'Alcove@123'
app.config['MYSQL_DB']       = 'alcovedb_2024'

app.config['MYSQL_CHARSET']  = 'utf8mb4'
app.config['MYSQL_CUSTOM_OPTIONS'] = {
    'charset': 'utf8mb4',
    'collation': 'utf8mb4_unicode_ci',
    'init_command': 'SET NAMES utf8mb4 COLLATE utf8mb4_unicode_ci, '
                    'collation_connection = utf8mb4_unicode_ci, '
                    'collation_database   = utf8mb4_unicode_ci'
}

app.config['PROFILE_PHOTO_FOLDER'] = 'static/uploads/profile_photos'

mysql = MySQL(app)

_COLLATION_SQL = (
    "SET NAMES utf8mb4 COLLATE utf8mb4_unicode_ci; "
    "SET collation_connection = utf8mb4_unicode_ci; "
    "SET collation_database   = utf8mb4_unicode_ci"
)

@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        emp_code = request.form['emp_code'].strip()
        password = request.form['password']

        # Determine if they might be a dept HOD (not in HR whitelist)
        in_hr_whitelist = emp_code in EXIT_ALL_ACCESS

        # Fetch user from DB
        cur = mysql.connection.cursor()
        cur.execute("""
            SELECT Emp_Code, password, Designation, Department,
                   Admin, Photo_Link, Email_ID_Official, Contact_number,
                   user_Access, Person_Accountable, Reporting_DOER
            FROM alcovedb_2024.Employee_Master
            WHERE Emp_Code=%s AND STATUS='ACTIVE'
        """, (emp_code,))
        user = cur.fetchone()
        cur.close()

        if not user or user[1] != password:
            flash('Invalid Credentials', 'danger')
            return render_template('login.html')

        # Check if dept HOD (appears as HOD_ID in Employee_Master)
        dept_hod_ids = fms_hr_exit__get_all_dept_hod_ids()
        is_a_dept_hod = emp_code in dept_hod_ids

        if not in_hr_whitelist and not is_a_dept_hod:
            flash('Access denied. You are not authorised for this system.', 'danger')
            return render_template('login.html')

        session['emp_code']           = user[0]
        session['designation']        = user[2]
        session['department']         = user[3]
        session['admin']              = user[4]
        session['photo']              = fms_hr_exit_get_default_photo(user[5])
        session['email']              = user[6]
        session['contact']            = user[7]
        session['user_Access']        = user[8]
        session['person_Accountable'] = user[9]
        session['Reporting_DOER']     = user[10]
        session['role'] = (
            'admin'      if emp_code in ADMIN_IDS
            else 'primary'    if emp_code in PRIMARY_DOER_IDS
            else 'secondary'  if emp_code in SECONDARY_DOER_IDS
            else 'dept_hod'
        )
        return redirect(url_for('dashboard'))

    return render_template('login.html')


# ================================== Upload Profile Photo =====================================

@app.route('/upload_photo', methods=['POST'])
def upload_photo():
    if 'emp_code' not in session:
        return redirect(url_for('login'))

    file = request.files.get('photo')
    if not file or file.filename == '':
        flash('No file selected', 'danger')
        return redirect(url_for('dashboard'))

    ext = file.filename.rsplit('.', 1)[-1].lower() if '.' in file.filename else ''
    if ext not in {'png', 'jpg', 'jpeg', 'webp'}:
        flash('Invalid file type. Use PNG, JPG or WEBP.', 'danger')
        return redirect(url_for('dashboard'))

    filename      = secure_filename(f"{session['emp_code']}.{ext}")
    upload_folder = app.config['PROFILE_PHOTO_FOLDER']
    os.makedirs(upload_folder, exist_ok=True)
    file.save(os.path.join(upload_folder, filename))
    db_path = f"uploads/profile_photos/{filename}"

    cur = mysql.connection.cursor()
    cur.execute("""
        UPDATE alcovedb_2024.Employee_Master SET Photo_Link=%s WHERE Emp_Code=%s
    """, (db_path, session['emp_code']))
    mysql.connection.commit()
    cur.close()

    session['photo'] = db_path
    flash('Profile photo updated', 'success')
    return redirect(url_for('dashboard'))


# ================================== Dashboard ================================================

@app.route('/dashboard')
def dashboard():
    if 'emp_code' not in session:
        return redirect(url_for('login'))

    emp_code = session['emp_code']
    role     = session.get('role')

    cur = mysql.connection.cursor(DictCursor)
    cur.execute("""
        SELECT
            COUNT(*)                                                  AS total,
            SUM(CASE WHEN status='OPEN'      THEN 1 ELSE 0 END)     AS open_count,
            SUM(CASE WHEN status='CLOSED'    THEN 1 ELSE 0 END)     AS closed_count,
            SUM(CASE WHEN status='REJECTED'  THEN 1 ELSE 0 END)     AS rejected_count,
            0 AS parallel_count
        FROM fms_exit_process_annex.exit_requests
    """)
    metrics = cur.fetchone() or {}
    cur.close()

    fixed_menus = {
        "HR Exit Process": [
            ("Exit Process Panel", url_for('exit_panel')),
        ]
    }
    if fms_hr_exit_is_admin(emp_code):
        fixed_menus["HR Exit Process"].append(
            ("Admin Dashboard", url_for('fms_hr_exit_exit_admin_dashboard'))
        )

    return render_template(
        'dashboard.html',
        fixed_menus=fixed_menus,
        person_Accountable=session['person_Accountable'],
        emp_code=emp_code,
        photo=session['photo'],
        role=role,
        metrics=metrics,
        fms_hr_exit_is_primary=fms_hr_exit_is_primary(emp_code),
        fms_hr_exit_is_secondary=fms_hr_exit_is_secondary(emp_code),
        is_admin_user=fms_hr_exit_is_admin(emp_code),
        is_dept_hod_user=(role == 'dept_hod'),
        is_hr_staff_user=fms_hr_exit_is_hr_staff(emp_code),
    )


# ================================== Forgot Password ==========================================

@app.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    emp_code    = session.get('emp_code', '')
    is_logged_in = 'readonly' if emp_code else ''

    if request.method == 'POST':
        emp_code     = request.form['emp_code']
        old_password = request.form['old_password']
        new_password = request.form['new_password']

        cur = mysql.connection.cursor()
        cur.execute("""
            SELECT password FROM alcovedb_2024.Employee_Master WHERE Emp_Code=%s
        """, (emp_code,))
        user = cur.fetchone()

        if not user:
            flash('Employee ID not found!', 'danger')
            return redirect(url_for('forgot_password'))

        if user[0] != old_password:
            flash('Old password incorrect!', 'danger')
            return redirect(url_for('forgot_password'))

        cur.execute("""
            UPDATE alcovedb_2024.Employee_Master SET password=%s WHERE Emp_Code=%s
        """, (new_password, emp_code))
        cur.execute("""
            INSERT INTO alcovedb_2024.Password_Records (Emp_Code, New_Password)
            VALUES (%s,%s)
        """, (emp_code, new_password))
        mysql.connection.commit()
        cur.close()

        flash('Password reset successfully', 'success')
        return redirect(url_for('login'))

    return render_template('forgot_password.html', emp_code=emp_code, is_logged_in=is_logged_in)


# ================================== Logout ===================================================

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))



def _fix_collation():
    conn = mysql.connection
    for stmt in _COLLATION_SQL.split(';'):
        stmt = stmt.strip()
        if stmt:
            conn.query(stmt)
            try:
                conn.store_result()
            except Exception:
                pass

@app.before_request
def before_request_collation():
    try:
        _fix_collation()
    except Exception:
        pass

# ================================== Role / Access Config =====================================
# HR Executive — Primary Doer (full HR exit powers)
PRIMARY_DOER_IDS   = {"AR000004"}   # Ayan Das

# HR HOD — Secondary Doer (same powers as Primary for exit process)
SECONDARY_DOER_IDS = {"AR000003"}   # Subhodeep Kundu Chowdhury

# Admin — full access
ADMIN_IDS          = {"admin"}

# Departmental HODs — can ONLY see/action P4 tasks (Mail System Team)
# Populated dynamically from Employee_Master (HOD_ID column) at login.
# We store them in session as role='dept_hod'.
# Any employee whose emp_code appears as a HOD_ID in Employee_Master qualifies.
# We also support a hardcoded set for fallback.
DEPT_HOD_IDS: set = set()   # filled dynamically — see login()

# HR staff (Primary + Secondary) share full exit access
HR_STAFF_IDS = PRIMARY_DOER_IDS | SECONDARY_DOER_IDS

# Everyone who can log in at all
EXIT_ALL_ACCESS = PRIMARY_DOER_IDS | SECONDARY_DOER_IDS | ADMIN_IDS
# NOTE: dept_hod logins are also allowed — verified via DB lookup in login()

# ================================== Workflow Help Data =======================================

WORKFLOW_HELP = {
    "P1": {
        "who":  "HR Executive / HR HOD",
        "what": "Receive Resignation — Mail & Exit Form Fill Up",
        "when": "Anytime",
        "how":  "Mail and Exit Form Fill Up"
    },
    "P2": {
        "who":  "HR Executive / HR HOD",
        "what": "Confirm Resignation Accepted by HOD?",
        "when": "Within 2 Days",
        "how":  "Mail — YES → P3 | NO → P9 (Reject)"
    },
    "P3": {
        "who":  "HR Executive / HR HOD",
        "what": "Update Exit Details",
        "when": "Within 2 Hours",
        "how":  "ERP, G Sheet, Intrasite V2 & Org Chart"
    },
    "P4": {
        "who":  "Dept HOD",
        "what": "Mail System Team for Task Transfer",
        "when": "7 Days Before Exit Date",
        "how":  "Email with new assigned person name"
    },
    "P5": {
        "who":  "HR Executive / HR HOD",
        "what": "Share Exit Interview Link",
        "when": "Exit Date 11 AM",
        "how":  "Email"
    },
    "P6": {
        "who":  "HR Executive / HR HOD",
        "what": "Handover Doc + Asset / Clearance",
        "when": "Exit Date 2 PM",
        "how":  "Email, Hard Copy"
    },
    "P7": {
        "who":  "HR Executive / HR HOD",
        "what": "Issue Release Letter + Experience Letter",
        "when": "Exit Date 4 PM",
        "how":  "Email, Hard Copy"
    },
    "P8": {
        "who":  "HR Executive / HR HOD",
        "what": "Mark Employee Inactive",
        "when": "Exit Date 5 PM",
        "how":  "HR Master Data"
    },
    "P9": {
        "who":  "HR Executive / HR HOD",
        "what": "Reject Resignation — Process Ends",
        "when": "Within 2 Hours",
        "how":  "Mail"
    }
}

STAGE_TIME_LIMITS = {
    "P1":    0,
    "P2":    2 * 24 * 60 * 60,   # 2 days
    "P3":    2 * 60 * 60,         # 2 hours
    "P4":    7 * 24 * 60 * 60,   # 7 days before exit
    "P5":    0,
    "P6":    0,
    "P7":    0,
    "P8":    0,
    "P9":    2 * 60 * 60,         # 2 hours (rejection)
}

# ================================== Holiday-Aware Deadline Calculator ========================
# Rules:
#   - Every Sunday is a holiday
#   - Holidays fetched from alcove_checklist.holidaylist (filtered by location)
#   - Weekday cutoff:  6:30 PM  → carry leftover to next working day @ 10:00 AM
#   - Saturday cutoff: 4:30 PM  → shift to Monday 10:00 AM
#   - Skips public holidays from DB

WORKDAY_START = dt_time(10, 0)     # 10:00 AM
WEEKDAY_END   = dt_time(18, 30)   # 6:30 PM  (Mon–Fri)
SATURDAY_END  = dt_time(16, 30)   # 4:30 PM  (Saturday)

def fms_hr_exit__fetch_holidays(location=None):
    """Return a set of date objects that are public holidays."""
    try:
        cur = mysql.connection.cursor(DictCursor)
        if location:
            cur.execute(
                "SELECT date FROM alcove_checklist.holidaylist WHERE location=%s OR location IS NULL",
                (location,)
            )
        else:
            cur.execute("SELECT date FROM alcove_checklist.holidaylist")
        rows = cur.fetchall()
        cur.close()
        return {r['date'] for r in rows if r['date']}
    except Exception:
        return set()

def fms_hr_exit__is_working_day(d, holidays):
    """True if d (date) is not Sunday and not a public holiday."""
    if d.weekday() == 6:   # Sunday
        return False
    if d in holidays:
        return False
    return True

def fms_hr_exit__day_end(d):
    """Return the cutoff time for a given date."""
    if d.weekday() == 5:   # Saturday
        return datetime.combine(d, SATURDAY_END)
    return datetime.combine(d, WEEKDAY_END)

def fms_hr_exit__day_start(d):
    return datetime.combine(d, WORKDAY_START)

def fms_hr_exit_calculate_deadline(start_dt, duration_seconds, location=None):
    """
    Calculate deadline from start_dt + duration_seconds, respecting:
    - Office hours (10 AM – 6:30 PM weekdays, 10 AM – 4:30 PM Saturdays)
    - Sundays off
    - Public holidays from DB
    Returns a datetime.
    """
    if duration_seconds <= 0:
        return start_dt

    holidays = fms_hr_exit__fetch_holidays(location)
    remaining = duration_seconds   # seconds left to schedule

    current = start_dt
    # If we start outside working hours, snap to next working day start
    d = current.date()
    if not fms_hr_exit__is_working_day(d, holidays):
        # advance to next working day
        d += timedelta(days=1)
        while not fms_hr_exit__is_working_day(d, holidays):
            d += timedelta(days=1)
        current = fms_hr_exit__day_start(d)
    else:
        end_today = fms_hr_exit__day_end(d)
        if current >= end_today:
            # Already past cutoff — move to next working day
            d += timedelta(days=1)
            while not fms_hr_exit__is_working_day(d, holidays):
                d += timedelta(days=1)
            current = fms_hr_exit__day_start(d)

    while remaining > 0:
        d = current.date()
        end_today = fms_hr_exit__day_end(d)
        available = (end_today - current).total_seconds()
        if available <= 0:
            # Move to next working day
            d += timedelta(days=1)
            while not fms_hr_exit__is_working_day(d, holidays):
                d += timedelta(days=1)
            current = fms_hr_exit__day_start(d)
            continue
        if remaining <= available:
            current = current + timedelta(seconds=remaining)
            remaining = 0
        else:
            remaining -= available
            d += timedelta(days=1)
            while not fms_hr_exit__is_working_day(d, holidays):
                d += timedelta(days=1)
            current = fms_hr_exit__day_start(d)

    # Final check: if result is past cutoff, push to next working day start
    d = current.date()
    end_today = fms_hr_exit__day_end(d)
    if current > end_today:
        d += timedelta(days=1)
        while not fms_hr_exit__is_working_day(d, holidays):
            d += timedelta(days=1)
        current = fms_hr_exit__day_start(d)

    return current


def fms_hr_exit_calculate_deadline_days(start_dt, n_working_days, location=None):
    """
    Advance exactly n_working_days from start_dt, landing at end-of-day cutoff
    on the Nth working day.

    RULE: The start day is NEVER counted — counting always begins from the NEXT
    working day after start_dt, regardless of what time it currently is.
    e.g. start = Thu 13 Mar, n=2  →  Fri 14 = day 1, Sat 15 = day 2
                                     → deadline = 4:30 PM Sat 15 Mar.

    Rules: skips Sundays + DB holidays;
           cutoff = 6:30 PM Mon–Fri, 4:30 PM Saturday;
           work starts at 10:00 AM.
    """
    if n_working_days <= 0:
        return start_dt

    holidays = fms_hr_exit__fetch_holidays(location)
    d = start_dt.date()

    # Always skip the start/current day — day 1 is always the next working day
    d += timedelta(days=1)
    while not fms_hr_exit__is_working_day(d, holidays):
        d += timedelta(days=1)

    # Count n_working_days; d is already day 1
    count = 1
    while count < n_working_days:
        d += timedelta(days=1)
        if fms_hr_exit__is_working_day(d, holidays):
            count += 1

    return fms_hr_exit__day_end(d)

def fms_hr_exit_get_default_photo(photo_link):
    return photo_link if photo_link else "images/placeholder-user.png"

def fms_hr_exit_save_attachment(file, folder_name):
    if not file or not file.filename:
        return None
    allowed = {'png','jpg','jpeg','webp','pdf','doc','docx','xls','xlsx'}
    ext = file.filename.rsplit('.', 1)[-1].lower() if '.' in file.filename else ''
    if ext not in allowed:
        return None
    filename = secure_filename(f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{file.filename}")
    folder   = f"static/uploads/{folder_name}"
    os.makedirs(folder, exist_ok=True)
    file.save(os.path.join(folder, filename))
    return f"uploads/{folder_name}/{filename}"

def fms_hr_exit__get_all_dept_hod_ids():
    """Return set of emp_codes that appear as HOD_ID in Employee_Master (i.e. are dept HODs)."""
    try:
        cur = mysql.connection.cursor()
        cur.execute("""
            SELECT DISTINCT HOD_ID FROM alcovedb_2024.Employee_Master
            WHERE HOD_ID IS NOT NULL AND HOD_ID != ''
        """)
        rows = cur.fetchall()
        cur.close()
        return {r[0] for r in rows if r[0]}
    except Exception:
        return set()

# ================================== Role Helpers =============================================

def fms_hr_exit_is_primary(emp_code):    return emp_code in PRIMARY_DOER_IDS
def fms_hr_exit_is_secondary(emp_code):  return emp_code in SECONDARY_DOER_IDS
def fms_hr_exit_is_admin(emp_code):      return emp_code in ADMIN_IDS
def fms_hr_exit_is_hr_staff(emp_code):   return emp_code in HR_STAFF_IDS or fms_hr_exit_is_admin(emp_code)

def fms_hr_exit_is_dept_hod(emp_code):
    """True if this user is a departmental HOD (not HR staff)."""
    return session.get('role') == 'dept_hod'

def fms_hr_exit_can_access_exit(emp_code):
    """HR staff, admin, and dept HODs can all access the exit panel."""
    return (emp_code in EXIT_ALL_ACCESS) or (session.get('role') == 'dept_hod')

# ================================== Login ====================================================

# ================================== Stage Log + FMS Sync =====================================

def fms_hr_exit_log_stage(cur, exit_request_id, stage, action, done_by, remarks, attachment):
    cur.execute("""
        INSERT INTO fms_exit_process_annex.exit_stage_log
        (exit_request_id, stage, action, done_by, remarks, attachment)
        VALUES (%s,%s,%s,%s,%s,%s)
    """, (exit_request_id, stage, action, done_by, remarks, attachment))


FMS_PROJECT = 'HR Exit Process'
FMS_NAME    = 'fms_hr_exit_process_annex'

STAGE_STATUS_MAP = {
    'P1': 'OPEN',
    'P2': 'OPEN',
    'P3': 'OPEN',
    'P4': 'OPEN',
    'P5': 'OPEN',
    'P6': 'OPEN',
    'P7': 'OPEN',
    'P8': 'CLOSED',
    'P9': 'REJECTED',
}


def fms_hr_exit_fms_sync(main_cur, req_id, from_stage, to_stage, emp_id,
             remarks=None, attachment=None, planned_end_time=None,
             decision=None, allocate_to=None, allocate_emp_id=None):
    try:
        conn = main_cur.connection if hasattr(main_cur, 'connection') else mysql.connection
        cur  = conn.cursor(DictCursor)

        cur.execute("""
            SELECT er.id, er.employee_code, er.employee_name,
                   er.hod, er.hod_id, er.reporting_doer, er.reporting_doer_id,
                   er.department, er.date_of_exit, er.created_by,
                   COALESCE(em.Location, '') AS location
            FROM fms_exit_process_annex.exit_requests er
            LEFT JOIN alcovedb_2024.Employee_Master em
                   ON er.employee_code COLLATE utf8mb4_unicode_ci
                    = em.Emp_Code      COLLATE utf8mb4_unicode_ci
            WHERE er.id = %s
        """, (req_id,))
        er = cur.fetchone()
        if not er:
            cur.close(); return

        task_name   = str(er['id'])
        status      = STAGE_STATUS_MAP.get(to_stage, 'OPEN')
        task_detail = (
            f"Exit: {er['employee_name']} ({er['employee_code']}) "
            f"| Dept: {er.get('department', '')} "
            f"| Exit Date: {er.get('date_of_exit', '')} "
            f"| Stage: {to_stage}"
        )
        created_emp = er.get('created_by') or emp_id
        eff_planned = planned_end_time
        if eff_planned is None and er.get('date_of_exit'):
            eff_planned = datetime.combine(er['date_of_exit'], datetime.min.time())

        cur.execute("""
            INSERT INTO fms_exit_process_annex.tasks
                (task_name, current_stage, from_stage, status,
                 remark, attachment_path, planned_end_time, `1st_planned_end_time`,
                 submit_emp_id, emp_id, emp_name,
                 hod_id, hod_name,
                 actual_time, allocate_to, allocate_emp_id,
                 created_emp_id, project, task_details,
                 pc_update_stage, fms_name, location)
            VALUES (%s,%s,%s,%s, %s,%s,%s,%s, %s,%s,%s, %s,%s,
                    NOW(),%s,%s, %s,%s,%s, %s,%s,%s)
            ON DUPLICATE KEY UPDATE
                current_stage    = VALUES(current_stage),
                from_stage       = VALUES(from_stage),
                status           = VALUES(status),
                remark           = VALUES(remark),
                attachment_path  = VALUES(attachment_path),
                planned_end_time = VALUES(planned_end_time),
                submit_emp_id    = VALUES(submit_emp_id),
                emp_id           = VALUES(emp_id),
                emp_name         = VALUES(emp_name),
                actual_time      = NOW(),
                allocate_to      = VALUES(allocate_to),
                allocate_emp_id  = VALUES(allocate_emp_id),
                hod_id           = VALUES(hod_id),
                hod_name         = VALUES(hod_name),
                pc_update_stage  = VALUES(pc_update_stage),
                task_details     = VALUES(task_details),
                location         = VALUES(location)
        """, (
            task_name, to_stage, from_stage, status,
            remarks, attachment, eff_planned, eff_planned,
            emp_id, emp_id, er['employee_name'],
            er.get('hod_id', ''), er.get('hod', ''),
            allocate_to or er.get('reporting_doer', ''),
            allocate_emp_id or er.get('reporting_doer_id', ''),
            created_emp, FMS_PROJECT, task_detail,
            to_stage, FMS_NAME, er.get('location', '')
        ))

        cur.execute("""
            SELECT task_id FROM fms_exit_process_annex.tasks WHERE task_name = %s
        """, (task_name,))
        t = cur.fetchone()
        if not t:
            cur.close(); return
        task_id = t['task_id']

        cur.execute("""
            SELECT COALESCE(MAX(update_id), 0) + 1 AS nxt
            FROM fms_exit_process_annex.task_updates
        """)
        nxt      = cur.fetchone()
        next_uid = int(nxt['nxt']) if nxt else 1

        cur.execute("""
            INSERT INTO fms_exit_process_annex.task_updates
                (update_id, task_id, task_name, from_stage, to_stage,
                 remark, attachment_path, planned_end_time,
                 decision, emp_id, actual_time,
                 allocate_to, allocate_emp_id,
                 project, fms_name)
            VALUES (%s,%s,%s,%s,%s, %s,%s,%s, %s,%s,NOW(), %s,%s, %s,%s)
        """, (
            next_uid, task_id, task_name, from_stage, to_stage,
            remarks, attachment, eff_planned,
            decision, emp_id,
            allocate_to or er.get('reporting_doer', ''),
            allocate_emp_id or er.get('reporting_doer_id', ''),
            FMS_PROJECT, FMS_NAME
        ))

        cur.close()

    except Exception as exc:
        app.logger.error(
            f"[FMS] FAILED req={req_id} {from_stage}→{to_stage}: {exc}",
            exc_info=True
        )


# ================================== AJAX — Fetch Employee ====================================

@app.route('/exit/fetch_employee/<emp_code_query>')
def fms_hr_exit_exit_fetch_employee(emp_code_query):
    if 'emp_code' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    cur = mysql.connection.cursor(DictCursor)
    cur.execute("""
        SELECT Emp_Code, Person_Accountable, Department,
               HOD, HOD_ID, DOJ, Reporting_DOER, Reporting_DOER_id,
               Designation, Location, Company, STATUS
        FROM alcovedb_2024.Employee_Master
        WHERE Emp_Code=%s
    """, (emp_code_query.upper(),))
    emp = cur.fetchone()
    cur.close()

    if not emp:
        return jsonify({'error': 'Employee not found'}), 404

    if emp.get('DOJ') and hasattr(emp['DOJ'], 'strftime'):
        emp['DOJ'] = emp['DOJ'].strftime('%d/%m/%Y')

    return jsonify(emp)


@app.route('/exit/all_employees')
def fms_hr_exit_exit_all_employees():
    if 'emp_code' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    cur = mysql.connection.cursor(DictCursor)
    cur.execute("""
        SELECT Emp_Code, Person_Accountable, STATUS
        FROM alcovedb_2024.Employee_Master
        ORDER BY Person_Accountable ASC
    """)
    employees = cur.fetchall()
    cur.close()

    result = []
    for e in employees:
        result.append({
            'code':   e['Emp_Code'],
            'name':   e['Person_Accountable'] or e['Emp_Code'],
            'active': (e['STATUS'] or '').upper() == 'ACTIVE'
        })
    return jsonify(result)


# ================================== Exit Panel (List View) ===================================

@app.route('/exit')
def exit_panel():
    if 'emp_code' not in session:
        return redirect(url_for('login'))

    emp_code = session['emp_code']
    role     = session.get('role')

    if not fms_hr_exit_can_access_exit(emp_code):
        flash('Access denied.', 'danger')
        return redirect(url_for('dashboard'))

    show_archived = bool(request.args.get('show_archived'))

    cur = mysql.connection.cursor(DictCursor)

    if show_archived:
        cur.execute("""
            SELECT er.*,
                   COALESCE(em.Person_Accountable, er.employee_name) AS employee_name,
                   COALESCE(em.Department, er.department)            AS department,
                   em.Designation
            FROM   fms_exit_process_annex.exit_requests er
            LEFT JOIN alcovedb_2024.Employee_Master em
                   ON er.employee_code COLLATE utf8mb4_unicode_ci = em.Emp_Code COLLATE utf8mb4_unicode_ci
            WHERE  er.status IN ('CLOSED','CANCELLED')
            ORDER  BY er.id DESC
        """)
    else:
        cur.execute("""
            SELECT er.*,
                   COALESCE(em.Person_Accountable, er.employee_name) AS employee_name,
                   COALESCE(em.Department, er.department)            AS department,
                   em.Designation
            FROM   fms_exit_process_annex.exit_requests er
            LEFT JOIN alcovedb_2024.Employee_Master em
                   ON er.employee_code COLLATE utf8mb4_unicode_ci = em.Emp_Code COLLATE utf8mb4_unicode_ci
            WHERE  er.status IN ('OPEN','REJECTED')
            ORDER  BY er.id DESC
        """)

    raw_tasks = cur.fetchall()

    # ── Build display rows ──────────────────────────────────────────────────────
    # For P4 stage, split into TWO rows — one for P5 (HR staff) and one for P4
    # (Dept HOD). Each row keeps the same id so they appear grouped.
    # Role-based visibility is handled in the template via row_type field.
    display_tasks = []
    for t in raw_tasks:
        t = dict(t)
        t['_row_type'] = t.get('workflow_stage', '')
        display_tasks.append(t)

    # Totals for metric cards
    cur.execute("""
        SELECT
            SUM(CASE WHEN status IN ('OPEN','REJECTED')           THEN 1 ELSE 0 END) AS pending,
            SUM(CASE WHEN status='CLOSED'                         THEN 1 ELSE 0 END) AS completed,
            SUM(CASE WHEN status='CANCELLED'                      THEN 1 ELSE 0 END) AS rejected,
            0 AS parallel
        FROM fms_exit_process_annex.exit_requests
    """)
    counts = cur.fetchone() or {}
    cur.close()

    metrics = {
        "pending":        int(counts.get('pending')   or 0),
        "completed":      int(counts.get('completed') or 0),
        "rejected":       int(counts.get('rejected')  or 0),
        "parallel_count": 0,
    }

    return render_template(
        'exit_panel.html',
        tasks=display_tasks,
        metrics=metrics,
        show_archived=show_archived,
        help_data=WORKFLOW_HELP,
        now=datetime.now(),
        person_Accountable=session['person_Accountable'],
        emp_code=emp_code,
        photo=session['photo'],
        role=role,
        fms_hr_exit_is_primary=fms_hr_exit_is_primary(emp_code),
        fms_hr_exit_is_secondary=fms_hr_exit_is_secondary(emp_code),
        is_admin_user=fms_hr_exit_is_admin(emp_code),
        is_dept_hod_user=(role == 'dept_hod'),
        is_hr_staff_user=fms_hr_exit_is_hr_staff(emp_code),
    )


# ================================== P1 — Create Exit Request =================================

@app.route('/exit/create', methods=['POST'])
def fms_hr_exit_exit_create():
    if 'emp_code' not in session:
        return redirect(url_for('login'))

    emp_code = session['emp_code']
    # Only HR staff / admin can create exit requests (not dept HOD)
    if not fms_hr_exit_is_hr_staff(emp_code):
        flash('Access denied. Only HR staff can initiate exit requests.', 'danger')
        return redirect(url_for('exit_panel'))

    employee_code     = request.form.get('employee_code', '').strip().upper()
    employee_name     = request.form.get('employee_name', '').strip()
    department        = request.form.get('department', '').strip()
    hod               = request.form.get('hod', '').strip()
    hod_id            = request.form.get('hod_id', '').strip()
    doj               = request.form.get('doj', '') or None
    reporting_doer    = request.form.get('reporting_doer', '').strip()
    reporting_doer_id = request.form.get('reporting_doer_id', '').strip()
    date_of_exit      = request.form.get('date_of_exit', '')
    remarks           = request.form.get('remarks', '').strip()

    if not employee_code or not date_of_exit:
        flash('Employee Code and Date of Exit are required.', 'danger')
        return redirect(url_for('exit_panel'))

    cur_check = mysql.connection.cursor(DictCursor)
    cur_check.execute("""
        SELECT Emp_Code, STATUS, Location FROM alcovedb_2024.Employee_Master
        WHERE Emp_Code=%s
    """, (employee_code,))
    emp_check = cur_check.fetchone()
    cur_check.close()

    if not emp_check:
        flash(f'Employee {employee_code} not found in HR Master. Cannot create exit request.', 'danger')
        return redirect(url_for('exit_panel'))

    if (emp_check.get('STATUS') or '').upper() != 'ACTIVE':
        flash(f'Warning: Employee {employee_code} is currently INACTIVE in HR Master. Exit request created, but please verify.', 'warning')

    location    = emp_check.get('Location') or ''
    attach_path = fms_hr_exit_save_attachment(request.files.get('attachment'), 'exit_p1')
    # P2 deadline = end-of-day on the 2nd working day from now (skips Sundays + holidays)
    deadline    = fms_hr_exit_calculate_deadline_days(datetime.now(), 2, location)

    cur = mysql.connection.cursor()
    cur.execute("""
        INSERT INTO fms_exit_process_annex.exit_requests
            (employee_code, employee_name, department, hod, hod_id,
             doj, reporting_doer, reporting_doer_id, date_of_exit,
             status, workflow_stage,
             p1_remarks, p1_attachment, p1_done_by, p1_done_at,
             stage_started_at, deadline_at, created_by, created_at)
        VALUES (%s,%s,%s,%s,%s, %s,%s,%s,%s,
                'OPEN','P2',
                %s,%s,%s,NOW(),
                NOW(),%s,%s,NOW())
    """, (
        employee_code, employee_name, department, hod, hod_id,
        doj, reporting_doer, reporting_doer_id, date_of_exit,
        remarks, attach_path, emp_code,
        deadline, emp_code
    ))
    new_id = cur.lastrowid
    fms_hr_exit_log_stage(cur, new_id, 'P1', 'Exit request initiated', emp_code, remarks, attach_path)
    fms_hr_exit_fms_sync(cur, new_id, 'P1', 'P2', emp_code,
             remarks=remarks, attachment=attach_path, planned_end_time=deadline)
    mysql.connection.commit()
    cur.close()

    flash(f'Exit request initiated for {employee_name}. Now at P2 — HOD Confirmation.', 'success')
    return redirect(url_for('exit_panel'))


# ================================== P2 — HOD Confirmation Decision ===========================

@app.route('/exit/<int:req_id>/p2_decision', methods=['POST'])
def fms_hr_exit_exit_p2_decision(req_id):
    if 'emp_code' not in session:
        return redirect(url_for('login'))

    emp_code = session['emp_code']
    if not fms_hr_exit_is_hr_staff(emp_code):
        flash('Access denied.', 'danger')
        return redirect(url_for('exit_panel'))

    decision    = request.form.get('decision', '').upper()
    remarks     = request.form.get('remarks', '').strip()
    attach_path = fms_hr_exit_save_attachment(request.files.get('attachment'), 'exit_p2')

    if decision not in ('YES', 'NO'):
        flash('Invalid decision value.', 'danger')
        return redirect(url_for('exit_panel'))

    # Get employee location for holiday-aware deadline
    cur_loc = mysql.connection.cursor(DictCursor)
    cur_loc.execute("""
        SELECT em.Location FROM fms_exit_process_annex.exit_requests er
        LEFT JOIN alcovedb_2024.Employee_Master em
               ON er.employee_code COLLATE utf8mb4_unicode_ci = em.Emp_Code COLLATE utf8mb4_unicode_ci
        WHERE er.id=%s
    """, (req_id,))
    loc_row  = cur_loc.fetchone()
    cur_loc.close()
    location = (loc_row or {}).get('Location') or ''

    cur = mysql.connection.cursor()

    if decision == 'YES':
        deadline = fms_hr_exit_calculate_deadline(datetime.now(), STAGE_TIME_LIMITS['P3'], location)
        cur.execute("""
            UPDATE fms_exit_process_annex.exit_requests
            SET workflow_stage='P3',
                p2_decision='YES', p2_remarks=%s, p2_attachment=%s,
                p2_done_by=%s, p2_done_at=NOW(),
                stage_started_at=NOW(), deadline_at=%s
            WHERE id=%s AND status='OPEN'
        """, (remarks, attach_path, emp_code, deadline, req_id))
        fms_hr_exit_log_stage(cur, req_id, 'P2', 'Resignation accepted by HOD → P3', emp_code, remarks, attach_path)
        fms_hr_exit_fms_sync(cur, req_id, 'P2', 'P3', emp_code,
                 remarks=remarks, attachment=attach_path,
                 planned_end_time=deadline, decision='YES')
        flash('Resignation accepted by HOD. Moved to P3 — Update Exit Details.', 'success')

    else:  # NO → P9
        # P9 deadline = 2 working hours from now
        p9_deadline = fms_hr_exit_calculate_deadline(datetime.now(), STAGE_TIME_LIMITS['P9'], location)
        cur.execute("""
            UPDATE fms_exit_process_annex.exit_requests
            SET workflow_stage='P9', status='REJECTED',
                p2_decision='NO', p2_remarks=%s, p2_attachment=%s,
                p2_done_by=%s, p2_done_at=NOW(),
                p9_remarks=%s, p9_done_by=%s, p9_done_at=NOW(),
                stage_started_at=NOW(), deadline_at=%s
            WHERE id=%s AND status='OPEN'
        """, (remarks, attach_path, emp_code, remarks, emp_code, p9_deadline, req_id))
        fms_hr_exit_log_stage(cur, req_id, 'P2', 'Resignation rejected by HOD → P9 end', emp_code, remarks, attach_path)
        fms_hr_exit_fms_sync(cur, req_id, 'P2', 'P9', emp_code,
                 remarks=remarks, attachment=attach_path, decision='NO',
                 planned_end_time=p9_deadline)
        flash('Resignation rejected. Process ended at P9.', 'warning')

    mysql.connection.commit()
    cur.close()
    return redirect(url_for('exit_panel'))


# ================================== P9 — Acknowledge Rejection (Close) ======================

@app.route('/exit/<int:req_id>/p9_close', methods=['POST'])
def fms_hr_exit_exit_p9_close(req_id):
    """HR acknowledges the rejection — marks P9 as fully closed."""
    if 'emp_code' not in session:
        return redirect(url_for('login'))

    emp_code = session['emp_code']
    if not fms_hr_exit_is_hr_staff(emp_code):
        flash('Access denied.', 'danger')
        return redirect(url_for('exit_panel'))

    remarks = request.form.get('remarks', '').strip()

    cur = mysql.connection.cursor()
    cur.execute("""
        UPDATE fms_exit_process_annex.exit_requests
        SET status='CANCELLED',
            p8_remarks=%s, p8_done_by=%s, p8_done_at=NOW()
        WHERE id=%s AND workflow_stage='P9' AND status='REJECTED'
    """, (remarks or 'Rejection acknowledged — process closed.', emp_code, req_id))
    fms_hr_exit_log_stage(cur, req_id, 'P9', 'Rejection acknowledged — process fully closed', emp_code,
              remarks or 'Rejection acknowledged.', None)
    fms_hr_exit_fms_sync(cur, req_id, 'P9', 'P9', emp_code,
             remarks=remarks or 'Rejection acknowledged — process closed.')
    mysql.connection.commit()
    cur.close()

    flash('P9 acknowledged. Rejection process closed.', 'success')
    return redirect(url_for('exit_panel'))


# ================================== P3 — Update Exit Details =================================

@app.route('/exit/<int:req_id>/p3_update', methods=['POST'])
def fms_hr_exit_exit_p3_update(req_id):
    if 'emp_code' not in session:
        return redirect(url_for('login'))

    emp_code = session['emp_code']
    if not fms_hr_exit_is_hr_staff(emp_code):
        flash('Access denied.', 'danger')
        return redirect(url_for('exit_panel'))

    remarks     = request.form.get('remarks', '').strip()
    attach_path = fms_hr_exit_save_attachment(request.files.get('attachment'), 'exit_p3')

    cur = mysql.connection.cursor(DictCursor)
    cur.execute("""
        SELECT er.date_of_exit, em.Location
        FROM fms_exit_process_annex.exit_requests er
        LEFT JOIN alcovedb_2024.Employee_Master em
               ON er.employee_code COLLATE utf8mb4_unicode_ci = em.Emp_Code COLLATE utf8mb4_unicode_ci
        WHERE er.id=%s
    """, (req_id,))
    row      = cur.fetchone()
    cur.close()

    location = (row or {}).get('Location') or ''

    p4_deadline = None
    if row and row.get('date_of_exit'):
        # P4 deadline = end-of-working-day on the date 7 calendar days before exit
        p4_date     = row['date_of_exit'] - timedelta(days=7)
        p4_holidays = fms_hr_exit__fetch_holidays(location)
        # If that date is a non-working day, roll back to the nearest prior working day
        while not fms_hr_exit__is_working_day(p4_date, p4_holidays):
            p4_date -= timedelta(days=1)
        p4_deadline = fms_hr_exit__day_end(p4_date)

    cur2 = mysql.connection.cursor()
    cur2.execute("""
        UPDATE fms_exit_process_annex.exit_requests
        SET workflow_stage='P4',
            p3_remarks=%s, p3_attachment=%s,
            p3_done_by=%s, p3_done_at=NOW(),
            p4_status='PENDING',
            stage_started_at=NOW(), deadline_at=%s
        WHERE id=%s AND status='OPEN'
    """, (remarks, attach_path, emp_code, p4_deadline, req_id))
    fms_hr_exit_log_stage(cur2, req_id, 'P3', 'Exit details updated — moving to P4 (Dept HOD: System Team Mail)', emp_code, remarks, attach_path)
    fms_hr_exit_fms_sync(cur2, req_id, 'P3', 'P4', emp_code,
             remarks=remarks, attachment=attach_path, planned_end_time=p4_deadline)
    mysql.connection.commit()
    cur2.close()

    flash('Exit details updated. Now at P4 — Dept HOD to mail System Team for task transfer.', 'success')
    return redirect(url_for('exit_panel'))


# ================================== P5 — Share Exit Interview Link ===========================

@app.route('/exit/<int:req_id>/p5_done', methods=['POST'])
def fms_hr_exit_exit_p5_done(req_id):
    if 'emp_code' not in session:
        return redirect(url_for('login'))

    emp_code = session['emp_code']
    if not fms_hr_exit_is_hr_staff(emp_code):
        flash('Only HR Executive or HR HOD can complete P5.', 'danger')
        return redirect(url_for('exit_panel'))

    remarks     = request.form.get('remarks', '').strip()
    attach_path = fms_hr_exit_save_attachment(request.files.get('attachment'), 'exit_p5')

    cur = mysql.connection.cursor(DictCursor)
    cur.execute("""
        SELECT date_of_exit FROM fms_exit_process_annex.exit_requests
        WHERE id=%s AND status='OPEN' AND workflow_stage='P5'
    """, (req_id,))
    row = cur.fetchone()
    cur.close()

    if not row:
        flash('Request not found or already closed.', 'danger')
        return redirect(url_for('exit_panel'))

    p6_dl = datetime.combine(row['date_of_exit'], dt_time(14, 0)) if row.get('date_of_exit') else None

    cur2 = mysql.connection.cursor()
    cur2.execute("""
        UPDATE fms_exit_process_annex.exit_requests
        SET workflow_stage='P6',
            p5_remarks=%s, p5_attachment=%s,
            p5_done_by=%s, p5_done_at=NOW(),
            stage_started_at=NOW(), deadline_at=%s
        WHERE id=%s
    """, (remarks, attach_path, emp_code, p6_dl, req_id))
    fms_hr_exit_log_stage(cur2, req_id, 'P5', 'Exit interview link shared — advancing to P6', emp_code, remarks, attach_path)
    fms_hr_exit_fms_sync(cur2, req_id, 'P5', 'P6', emp_code,
             remarks=remarks, attachment=attach_path, planned_end_time=p6_dl)
    mysql.connection.commit()
    cur2.close()

    flash('P5 done. Moved to P6 — Handover Doc + Asset Clearance.', 'success')
    return redirect(url_for('exit_panel'))


# ================================== P4 — Mail System Team (Dept HOD) → advance to P5 =========

@app.route('/exit/<int:req_id>/p4_done', methods=['POST'])
def fms_hr_exit_exit_p4_done(req_id):
    if 'emp_code' not in session:
        return redirect(url_for('login'))

    emp_code = session['emp_code']
    role     = session.get('role')

    # P4 is exclusively for Dept HOD (or Admin)
    if role not in ('dept_hod', 'admin'):
        flash('Only Departmental HOD can complete P4.', 'danger')
        return redirect(url_for('exit_panel'))

    remarks     = request.form.get('remarks', '').strip()
    new_person  = request.form.get('new_assigned_person', '').strip()
    attach_path = fms_hr_exit_save_attachment(request.files.get('attachment'), 'exit_p4')

    cur = mysql.connection.cursor(DictCursor)
    cur.execute("""
        SELECT date_of_exit FROM fms_exit_process_annex.exit_requests
        WHERE id=%s AND status='OPEN' AND workflow_stage='P4'
    """, (req_id,))
    row = cur.fetchone()
    cur.close()

    if not row:
        flash('Request not found, already closed, or not at P4 stage.', 'danger')
        return redirect(url_for('exit_panel'))

    p5_deadline = datetime.combine(row['date_of_exit'], dt_time(11, 0)) if row.get('date_of_exit') else None

    cur2 = mysql.connection.cursor()
    cur2.execute("""
        UPDATE fms_exit_process_annex.exit_requests
        SET workflow_stage='P5',
            p4_status='DONE',
            p9_new_assigned_person=%s,
            p4_remarks=%s, p4_attachment=%s,
            p4_done_by=%s, p4_done_at=NOW(),
            stage_started_at=NOW(), deadline_at=%s
        WHERE id=%s
    """, (new_person, remarks, attach_path, emp_code, p5_deadline, req_id))

    fms_hr_exit_log_stage(cur2, req_id, 'P4', f'System team mail sent — new person: {new_person} — advancing to P5', emp_code, remarks, attach_path)
    fms_hr_exit_fms_sync(cur2, req_id, 'P4', 'P5', emp_code,
             remarks=remarks, attachment=attach_path,
             planned_end_time=p5_deadline, allocate_to=new_person)
    mysql.connection.commit()
    cur2.close()

    flash('P4 done. System team mail confirmed. Now at P5 — Share Exit Interview Link.', 'success')
    return redirect(url_for('exit_panel'))


# ================================== P6 — Handover + Clearance ================================

@app.route('/exit/<int:req_id>/p6_done', methods=['POST'])
def fms_hr_exit_exit_p6_done(req_id):
    if 'emp_code' not in session:
        return redirect(url_for('login'))

    emp_code = session['emp_code']
    if not fms_hr_exit_is_hr_staff(emp_code):
        flash('Access denied.', 'danger')
        return redirect(url_for('exit_panel'))

    remarks     = request.form.get('remarks', '').strip()
    attach_path = fms_hr_exit_save_attachment(request.files.get('attachment'), 'exit_p6')

    cur_dt5 = mysql.connection.cursor(DictCursor)
    cur_dt5.execute("SELECT date_of_exit FROM fms_exit_process_annex.exit_requests WHERE id=%s", (req_id,))
    dt_row5 = cur_dt5.fetchone(); cur_dt5.close()
    p6_dl = datetime.combine(dt_row5['date_of_exit'], dt_time(16, 0)) if dt_row5 and dt_row5['date_of_exit'] else None

    cur = mysql.connection.cursor()
    cur.execute("""
        UPDATE fms_exit_process_annex.exit_requests
        SET workflow_stage='P7',
            p6_remarks=%s, p6_attachment=%s,
            p6_done_by=%s, p6_done_at=NOW(),
            stage_started_at=NOW(), deadline_at=%s
        WHERE id=%s AND status='OPEN'
    """, (remarks, attach_path, emp_code, p6_dl, req_id))
    fms_hr_exit_log_stage(cur, req_id, 'P6', 'Handover doc + asset clearance done', emp_code, remarks, attach_path)
    fms_hr_exit_fms_sync(cur, req_id, 'P6', 'P7', emp_code,
             remarks=remarks, attachment=attach_path)
    mysql.connection.commit()
    cur.close()

    flash('P6 done. Moved to P7 — Issue Release & Experience Letter.', 'success')
    return redirect(url_for('exit_panel'))


# ================================== P7 — Issue Release + Experience Letter ===================

@app.route('/exit/<int:req_id>/p7_done', methods=['POST'])
def fms_hr_exit_exit_p7_done(req_id):
    if 'emp_code' not in session:
        return redirect(url_for('login'))

    emp_code = session['emp_code']
    if not fms_hr_exit_is_hr_staff(emp_code):
        flash('Access denied.', 'danger')
        return redirect(url_for('exit_panel'))

    remarks     = request.form.get('remarks', '').strip()
    attach_path = fms_hr_exit_save_attachment(request.files.get('attachment'), 'exit_p7')

    cur_dt6 = mysql.connection.cursor(DictCursor)
    cur_dt6.execute("SELECT date_of_exit FROM fms_exit_process_annex.exit_requests WHERE id=%s", (req_id,))
    dt_row6 = cur_dt6.fetchone(); cur_dt6.close()
    p7_dl = datetime.combine(dt_row6['date_of_exit'], dt_time(17, 0)) if dt_row6 and dt_row6['date_of_exit'] else None

    cur = mysql.connection.cursor()
    cur.execute("""
        UPDATE fms_exit_process_annex.exit_requests
        SET workflow_stage='P8',
            p7_remarks=%s, p7_attachment=%s,
            p7_done_by=%s, p7_done_at=NOW(),
            stage_started_at=NOW(), deadline_at=%s
        WHERE id=%s AND status='OPEN'
    """, (remarks, attach_path, emp_code, p7_dl, req_id))
    fms_hr_exit_log_stage(cur, req_id, 'P7', 'Release letter + experience letter issued', emp_code, remarks, attach_path)
    fms_hr_exit_fms_sync(cur, req_id, 'P7', 'P8', emp_code,
             remarks=remarks, attachment=attach_path)
    mysql.connection.commit()
    cur.close()

    flash('P7 done. Moved to P8 — Complete Exit.', 'success')
    return redirect(url_for('exit_panel'))


# ================================== P8 — Mark Inactive & Close (FINAL) ======================

@app.route('/exit/<int:req_id>/p8_done', methods=['POST'])
def fms_hr_exit_exit_p8_done(req_id):
    if 'emp_code' not in session:
        return redirect(url_for('login'))

    emp_code = session['emp_code']
    if not fms_hr_exit_is_hr_staff(emp_code):
        flash('Access denied.', 'danger')
        return redirect(url_for('exit_panel'))

    remarks     = request.form.get('remarks', '').strip()
    attach_path = fms_hr_exit_save_attachment(request.files.get('attachment'), 'exit_p8')

    cur = mysql.connection.cursor(DictCursor)
    cur.execute("""
        SELECT employee_code, employee_name, p4_status
        FROM fms_exit_process_annex.exit_requests WHERE id=%s
    """, (req_id,))
    row = cur.fetchone()
    cur.close()

    if not row:
        flash('Exit request not found.', 'danger')
        return redirect(url_for('exit_panel'))

    if row.get('p4_status') != 'DONE':
        flash('Cannot complete exit (P8) — P4 (System Team Mail by Dept HOD) must be completed first.', 'danger')
        return redirect(url_for('exit_panel'))

    emp_name = row['employee_name'] or ''

    # NOTE: Employee is marked INACTIVE via the HR portal by HR staff.
    # No automatic Employee_Master update is performed here.
    cur2 = mysql.connection.cursor()
    cur2.execute("""
        UPDATE fms_exit_process_annex.exit_requests
        SET workflow_stage='P8', status='CLOSED',
            p8_remarks=%s, p8_attachment=%s,
            p8_done_by=%s, p8_done_at=NOW()
        WHERE id=%s
    """, (remarks, attach_path, emp_code, req_id))

    fms_hr_exit_log_stage(cur2, req_id, 'P8', 'Exit process closed — employee marked inactive via HR portal', emp_code, remarks, attach_path)
    fms_hr_exit_fms_sync(cur2, req_id, 'P8', 'P8', emp_code,
             remarks=remarks, attachment=attach_path)
    mysql.connection.commit()
    cur2.close()

    flash(f'P8 complete. Exit process for {emp_name} is now CLOSED. Please ensure employee is marked INACTIVE in the HR portal.', 'success')
    return redirect(url_for('exit_panel'))


# ================================== Exit Request Detail ======================================

@app.route('/exit/<int:req_id>/detail')
def fms_hr_exit_exit_detail(req_id):
    if 'emp_code' not in session:
        return redirect(url_for('login'))

    emp_code = session['emp_code']
    if not fms_hr_exit_can_access_exit(emp_code):
        flash('Access denied.', 'danger')
        return redirect(url_for('dashboard'))

    cur = mysql.connection.cursor(DictCursor)
    cur.execute("""
        SELECT er.*,
               em.Person_Accountable AS employee_name_full,
               em.Designation, em.Location, em.Company,
               em.Contact_number, em.Email_ID_Official
        FROM   fms_exit_process_annex.exit_requests er
        LEFT JOIN alcovedb_2024.Employee_Master em ON er.employee_code COLLATE utf8mb4_unicode_ci = em.Emp_Code COLLATE utf8mb4_unicode_ci
        WHERE  er.id=%s
    """, (req_id,))
    req_data = cur.fetchone()

    cur.execute("""
        SELECT * FROM fms_exit_process_annex.exit_stage_log
        WHERE exit_request_id=%s ORDER BY done_at ASC
    """, (req_id,))
    audit_log = cur.fetchall()
    cur.close()

    if not req_data:
        flash('Exit request not found.', 'danger')
        return redirect(url_for('exit_panel'))

    role = session.get('role')
    return render_template(
        'fms_hr_exit_exit_detail.html',
        req=req_data,
        audit_log=audit_log,
        help_data=WORKFLOW_HELP,
        now=datetime.now(),
        person_Accountable=session['person_Accountable'],
        emp_code=emp_code,
        photo=session['photo'],
        role=role,
        fms_hr_exit_is_primary=fms_hr_exit_is_primary(emp_code),
        fms_hr_exit_is_secondary=fms_hr_exit_is_secondary(emp_code),
        is_admin_user=fms_hr_exit_is_admin(emp_code),
        is_dept_hod_user=(role == 'dept_hod'),
        is_hr_staff_user=fms_hr_exit_is_hr_staff(emp_code),
    )


# ================================== Admin Dashboard ==========================================

@app.route('/exit/admin_dashboard')
def fms_hr_exit_exit_admin_dashboard():
    if 'emp_code' not in session:
        return redirect(url_for('login'))

    emp_code = session['emp_code']
    if not fms_hr_exit_is_admin(emp_code):
        flash('Admin access only.', 'danger')
        return redirect(url_for('exit_panel'))

    cur = mysql.connection.cursor(DictCursor)
    cur.execute("""
        SELECT er.*,
               COALESCE(em.Person_Accountable, er.employee_name) AS employee_name,
               COALESCE(em.Department, er.department)            AS department,
               em.Designation
        FROM   fms_exit_process_annex.exit_requests er
        LEFT JOIN alcovedb_2024.Employee_Master em ON er.employee_code COLLATE utf8mb4_unicode_ci = em.Emp_Code COLLATE utf8mb4_unicode_ci
        ORDER  BY er.id DESC
    """)
    tasks = cur.fetchall()
    cur.close()

    metrics = {
        "total":     len(tasks),
        "pending":   sum(1 for t in tasks if t['status'] == 'OPEN'),
        "completed": sum(1 for t in tasks if t['status'] == 'CLOSED'),
        "rejected":  sum(1 for t in tasks if t['status'] in ('REJECTED', 'CANCELLED')),
    }

    return render_template(
        'exit_admin_stage_dashboard.html',
        tasks=tasks,
        metrics=metrics,
        help_data=WORKFLOW_HELP,
        now=datetime.now(),
        person_Accountable=session['person_Accountable'],
        emp_code=emp_code,
        photo=session['photo'],
        role=session.get('role'),
        is_admin_user=True,
        is_dept_hod_user=False,
        is_hr_staff_user=True,
    )


# ================================== Admin All-Stage Dashboard ================================

@app.route('/exit/admin_stage_dashboard')
def exit_admin_stage_dashboard():
    if 'emp_code' not in session:
        return redirect(url_for('login'))

    emp_code = session['emp_code']
    if not fms_hr_exit_is_admin(emp_code):
        flash('Admin access only.', 'danger')
        return redirect(url_for('exit_panel'))

    import time
    from collections import defaultdict
    t0 = time.time()

    cur = mysql.connection.cursor(DictCursor)
    cur.execute("""
        SELECT er.*,
               COALESCE(em.Person_Accountable, er.employee_name) AS employee_name,
               COALESCE(em.Department, er.department)            AS department,
               em.Designation, em.Location, em.Company
        FROM   fms_exit_process_annex.exit_requests er
        LEFT JOIN alcovedb_2024.Employee_Master em
               ON er.employee_code COLLATE utf8mb4_unicode_ci = em.Emp_Code COLLATE utf8mb4_unicode_ci
        ORDER  BY er.id DESC
    """)
    tasks_raw = cur.fetchall()

    cur.execute("""
        SELECT * FROM fms_exit_process_annex.exit_stage_log
        ORDER BY exit_request_id ASC, done_at ASC
    """)
    all_logs = cur.fetchall()
    cur.close()

    log_map = defaultdict(list)
    for log in all_logs:
        log_map[log['exit_request_id']].append(log)

    tasks = []
    for t in tasks_raw:
        t = dict(t)
        t['audit_log'] = log_map.get(t['id'], [])
        tasks.append(t)

    query_ms = (time.time() - t0) * 1000

    return render_template(
        'exit_admin_stage_dashboard.html',
        tasks=tasks,
        query_ms=query_ms,
        now=datetime.now(),
        person_Accountable=session['person_Accountable'],
        emp_code=emp_code,
        photo=session['photo'],
        role=session.get('role'),
        is_admin_user=True,
        fms_hr_exit_is_primary=fms_hr_exit_is_primary(emp_code),
        fms_hr_exit_is_secondary=fms_hr_exit_is_secondary(emp_code),
        is_dept_hod_user=False,
        is_hr_staff_user=True,
    )


# ================================== Holidays API =============================================

@app.route('/exit/holidays')
def fms_hr_exit_exit_holidays():
    """Return holidays list as JSON (for front-end date picker awareness)."""
    if 'emp_code' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    try:
        cur = mysql.connection.cursor(DictCursor)
        cur.execute("""
            SELECT id, holiday_name, location,
                   DATE_FORMAT(date, '%%Y-%%m-%%d') AS date
            FROM alcove_checklist.holidaylist
            ORDER BY date ASC
        """)
        rows = cur.fetchall()
        cur.close()
        return jsonify(rows)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ================================== Run =============================================

if __name__ == "__main__":
    app.run(debug=True, port=5001)