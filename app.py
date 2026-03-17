# ============================================================
# HR EXIT PROCESS — Flask App  (Updated)
# DB : alcovedb_2024 (Employee_Master, Password_Records)
#      fms_exit_process_annex (exit_requests, exit_stage_log)
#      alcove_checklist (holidaylist)
# ============================================================
from flask import Flask, render_template, request, redirect, flash, url_for, session, jsonify, send_from_directory
from flask_mysqldb import MySQL
from werkzeug.utils import secure_filename
from MySQLdb.cursors import DictCursor
import os
import uuid
from datetime import datetime, timedelta, time as dt_time

app = Flask(__name__)
app.secret_key = "secret_key_here"

app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'Alcove@123'
app.config['MYSQL_DB'] = 'alcovedb_2024'

app.config['PROFILE_PHOTO_FOLDER'] = 'static/uploads/profile_photos'

mysql = MySQL(app)

# =====================================Config Folders (Attachments or others )==========================================
# ======================================Other Functions(helpers) =======================================================

def get_default_photo(photo_link):
    return photo_link if photo_link else "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcSosHI4JH3vNxpQnFvuWx7OJY84XotRh9_h-g&s"

def allowed_file(filename):
    return (
        '.' in filename and
        filename.rsplit('.', 1)[1].lower() in {'png', 'jpg', 'jpeg', 'webp'}
    )

# ================================= Login, Dashboard, uploadphoto, logout, forgot_password==============================
@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        emp_code = request.form['emp_code']
        password = request.form['password']

        cur = mysql.connection.cursor()
        cur.execute(
            "SELECT Emp_Code, password, Designation, Department, Admin, Photo_Link, Email_ID_Official, Contact_number, user_Access, Person_Accountable,Reporting_DOER FROM Employee_Master WHERE Emp_Code=%s and STATUS='ACTIVE'",
            (emp_code,))
        user = cur.fetchone()
        cur.close()

        if user and user[1] == password:
            session['emp_code'] = user[0]
            session['designation'] = user[2]
            session['department'] = user[3]
            session['admin'] = user[4]
            session['photo'] = get_default_photo(user[5])
            session['email'] = user[6]
            session['contact'] = user[7]
            session['user_Access'] = user[8]
            session['person_Accountable'] = user[9]
            session['Reporting_DOER'] = user[10]
            print("Debug in if  ")
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid Credentials', 'danger')
            print("Debug in else  ")
            return render_template('login.html')

    return render_template('login.html')

@app.route('/upload_photo', methods=['POST'])
def upload_photo():
    if 'emp_code' not in session:
        return redirect(url_for('login'))

    file = request.files.get('photo')

    if not file or file.filename == '':
        flash('No file selected', 'danger')
        return redirect(url_for('dashboard'))

    if not allowed_file(file.filename):
        flash('Invalid file type', 'danger')
        return redirect(url_for('dashboard'))

    ext = file.filename.rsplit('.', 1)[1].lower()
    filename = secure_filename(f"{session['emp_code']}.{ext}")

    upload_folder = app.config['PROFILE_PHOTO_FOLDER']
    os.makedirs(upload_folder, exist_ok=True)

    file_path = os.path.join(upload_folder, filename)
    try:
        file.save(file_path)
        # print("FIle Saved Successfully ")
    except Exception as e:
        print(e)

    db_path = f"uploads/profile_photos/{filename}"

    cur = mysql.connection.cursor(DictCursor)
    cur.execute(
        "UPDATE Employee_Master SET Photo_Link=%s WHERE Emp_Code=%s",
        (db_path, session['emp_code'])
    )
    mysql.connection.commit()
    cur.close()
    flash('Profile photo updated', 'success')
    return redirect(url_for('dashboard'))

@app.route('/dashboard')
def dashboard():
    if 'emp_code' not in session:
        return redirect(url_for('login'))
    # =========================== Fixed Menus that will be shown on the left hand side side bar=========================
    fixed_menus = {
        "HR Exit Process": [
            ("Exit Process Panel", url_for('fms_hr_exit_exit_panel')),
        ],
    }
    return render_template(
        'dashboard.html',
        fixed_menus=fixed_menus, person_Accountable=session['person_Accountable'], emp_code=session['emp_code']
    )



@app.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    emp_code = session.get('emp_code', '')  # Prefill if logged in
    is_logged_in = 'readonly' if emp_code else ''  # Set read-only if logged in

    if request.method == 'POST':
        emp_code = request.form['emp_code']
        old_password = request.form['old_password']
        new_password = request.form['new_password']

        cur = mysql.connection.cursor()
        cur.execute("SELECT password FROM Employee_Master WHERE Emp_Code=%s", (emp_code,))
        user = cur.fetchone()

        if not user:
            flash('Employee ID not found!', 'danger')
            return redirect(url_for('forgot_password'))

        if user[0] != old_password:
            flash('Old password is incorrect!', 'danger')
            return redirect(url_for('forgot_password'))

        # Update the password in the Employee_Master table
        cur.execute("UPDATE Employee_Master SET password=%s WHERE Emp_Code=%s", (new_password, emp_code))

        # Insert a record into the Password_Records table to keep history
        cur.execute("INSERT INTO Password_Records (Emp_Code, New_Password) VALUES (%s, %s)",
                    (emp_code, new_password))

        mysql.connection.commit()
        cur.close()

        flash('Password reset successfully', 'success')
        return redirect(url_for('login'))

    return render_template('forgot_password.html', emp_code=emp_code, is_logged_in=is_logged_in)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

#=========================================SERVER CODE FMS HR EXIT==================================================

# ================================== Serve Uploaded Files =====================================

@app.route('/uploads/<path:token>')
def uploaded_file(token):
    from flask import Response, abort
    try:
        cur = mysql.connection.cursor(DictCursor)
        cur.execute(
            "SELECT filename, mimetype, filedata FROM fms_exit_process_annex.exit_attachments WHERE token=%s",
            (token,)
        )
        row = cur.fetchone()
        cur.close()
        if not row:
            print(f"[SERVE] token={token} not found in DB")
            abort(404)
        print(f"[SERVE] OK: {row['filename']} ({len(row['filedata'])} bytes)")
        return Response(
            bytes(row['filedata']),
            mimetype=row['mimetype'],
            headers={"Content-Disposition": f"inline; filename={row['filename']}"}
        )
    except Exception as e:
        print(f"[SERVE ERROR] {e}")
        abort(500)

fms_hr_exit__COLLATION_SQL = (
    "SET NAMES utf8mb4 COLLATE utf8mb4_unicode_ci; "
    "SET collation_connection = utf8mb4_unicode_ci; "
    "SET collation_database   = utf8mb4_unicode_ci"
)
def fms_hr_exit__fix_collation():
    conn = mysql.connection
    for stmt in fms_hr_exit__COLLATION_SQL.split(';'):
        stmt = stmt.strip()
        if stmt:
            conn.query(stmt)
            try:
                conn.store_result()
            except Exception:
                pass

@app.before_request
def fms_hr_exit_before_request_collation():
    try:
        fms_hr_exit__fix_collation()
    except Exception:
        pass

@app.before_request
def fms_hr_exit_before_request_role():
    emp_code = session.get('emp_code')
    if emp_code and 'role' not in session:
        try:
            fms_hr_exit_get_session_role(emp_code)
        except Exception:
            pass

# ================================== Role / Access Config =====================================

fms_hr_exit_PRIMARY_DOER_IDS   = {"AR000356"}   # Ayan Das
fms_hr_exit_SECONDARY_DOER_IDS = {"AR001866"}   # Subhodeep Kundu Chowdhury
fms_hr_exit_ADMIN_IDS          = {"AR000623"}
fms_hr_exit_DEPT_HOD_IDS: set  = set()

fms_hr_exit_HR_STAFF_IDS    = fms_hr_exit_PRIMARY_DOER_IDS | fms_hr_exit_SECONDARY_DOER_IDS
fms_hr_exit_EXIT_ALL_ACCESS = fms_hr_exit_PRIMARY_DOER_IDS | fms_hr_exit_SECONDARY_DOER_IDS | fms_hr_exit_ADMIN_IDS

# ================================== Workflow Help Data =======================================

fms_hr_exit_WORKFLOW_HELP = {
    "P1": {"who": "HR Executive / HR HOD", "what": "Receive Resignation — Mail & Exit Form Fill Up", "when": "Anytime",            "how": "Mail and Exit Form Fill Up"},
    "P2": {"who": "HR Executive / HR HOD", "what": "Confirm Resignation Accepted by HOD?",          "when": "Within 2 Days",       "how": "Mail — YES → P3 | NO → P9 (Reject)"},
    "P3": {"who": "HR Executive / HR HOD", "what": "Update Exit Details",                            "when": "Within 2 Hours",      "how": "ERP, G Sheet, Intrasite V2 & Org Chart"},
    "P4": {"who": "Dept HOD",              "what": "Mail System Team for Task Transfer",             "when": "7 Days Before Exit Date", "how": "Email with new assigned person name"},
    "P5": {"who": "HR Executive / HR HOD", "what": "Share Exit Interview Link",                      "when": "Exit Date 11 AM",     "how": "Email"},
    "P6": {"who": "HR Executive / HR HOD", "what": "Handover Doc + Asset / Clearance",              "when": "Exit Date 2 PM",      "how": "Email, Hard Copy"},
    "P7": {"who": "HR Executive / HR HOD", "what": "Issue Release Letter + Experience Letter",       "when": "Exit Date 4 PM",      "how": "Email, Hard Copy"},
    "P8": {"who": "HR Executive / HR HOD", "what": "Mark Employee Inactive",                         "when": "Exit Date 5 PM",      "how": "HR Master Data"},
    "P9": {"who": "HR Executive / HR HOD", "what": "Reject Resignation — Process Ends",              "when": "Within 2 Hours",      "how": "Mail"},
}

fms_hr_exit_STAGE_TIME_LIMITS = {
    "P1": 0,
    "P2": 2 * 24 * 60 * 60,
    "P3": 2 * 60 * 60,
    "P4": 7 * 24 * 60 * 60,
    "P5": 0, "P6": 0, "P7": 0, "P8": 0,
    "P9": 2 * 60 * 60,
}

# ================================== Holiday-Aware Deadline Calculator ========================

fms_hr_exit_WORKDAY_START = dt_time(10, 0)
fms_hr_exit_WEEKDAY_END   = dt_time(18, 30)
fms_hr_exit_SATURDAY_END  = dt_time(16, 30)

def fms_hr_exit__fetch_holidays(location=None):
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
    if d.weekday() == 6:
        return False
    if d in holidays:
        return False
    return True

def fms_hr_exit__day_end(d):
    if d.weekday() == 5:
        return datetime.combine(d, fms_hr_exit_SATURDAY_END)
    return datetime.combine(d, fms_hr_exit_WEEKDAY_END)

def fms_hr_exit__day_start(d):
    return datetime.combine(d, fms_hr_exit_WORKDAY_START)

def fms_hr_exit_calculate_deadline(start_dt, duration_seconds, location=None):
    if duration_seconds <= 0:
        return start_dt

    holidays  = fms_hr_exit__fetch_holidays(location)
    remaining = duration_seconds
    current   = start_dt

    d = current.date()
    if not fms_hr_exit__is_working_day(d, holidays):
        d += timedelta(days=1)
        while not fms_hr_exit__is_working_day(d, holidays):
            d += timedelta(days=1)
        current = fms_hr_exit__day_start(d)
    else:
        end_today = fms_hr_exit__day_end(d)
        if current >= end_today:
            d += timedelta(days=1)
            while not fms_hr_exit__is_working_day(d, holidays):
                d += timedelta(days=1)
            current = fms_hr_exit__day_start(d)

    while remaining > 0:
        d         = current.date()
        end_today = fms_hr_exit__day_end(d)
        available = (end_today - current).total_seconds()
        if available <= 0:
            d += timedelta(days=1)
            while not fms_hr_exit__is_working_day(d, holidays):
                d += timedelta(days=1)
            current = fms_hr_exit__day_start(d)
            continue
        if remaining <= available:
            current   = current + timedelta(seconds=remaining)
            remaining = 0
        else:
            remaining -= available
            d += timedelta(days=1)
            while not fms_hr_exit__is_working_day(d, holidays):
                d += timedelta(days=1)
            current = fms_hr_exit__day_start(d)

    d         = current.date()
    end_today = fms_hr_exit__day_end(d)
    if current > end_today:
        d += timedelta(days=1)
        while not fms_hr_exit__is_working_day(d, holidays):
            d += timedelta(days=1)
        current = fms_hr_exit__day_start(d)

    return current


def fms_hr_exit_calculate_deadline_days(start_dt, n_working_days, location=None):
    if n_working_days <= 0:
        return start_dt

    holidays = fms_hr_exit__fetch_holidays(location)
    d        = start_dt.date()

    d += timedelta(days=1)
    while not fms_hr_exit__is_working_day(d, holidays):
        d += timedelta(days=1)

    count = 1
    while count < n_working_days:
        d += timedelta(days=1)
        if fms_hr_exit__is_working_day(d, holidays):
            count += 1

    return fms_hr_exit__day_end(d)


def fms_hr_exit_deadline_on_exit_day(date_of_exit, target_time, location=None):
    """
    Return a deadline datetime on or after date_of_exit at target_time,
    respecting holidays and Saturday end time.
    - If date_of_exit is a Sunday or holiday → roll to next working day, use day_end.
    - If date_of_exit is a Saturday and target_time > SATURDAY_END → use SATURDAY_END.
    - Otherwise → use target_time but cap at day_end.
    """
    from datetime import date as _date
    holidays = fms_hr_exit__fetch_holidays(location)
    d = date_of_exit if isinstance(date_of_exit, _date.__class__) else date_of_exit

    # Roll forward if not a working day
    while not fms_hr_exit__is_working_day(d, holidays):
        d += timedelta(days=1)

    day_end = fms_hr_exit__day_end(d)

    # Cap target_time to day_end for that day
    candidate = datetime.combine(d, target_time)
    if candidate > day_end:
        candidate = day_end

    return candidate



def fms_hr_exit_get_default_photo(photo_link):
    return photo_link if photo_link else "images/placeholder-user.png"


def fms_hr_exit_save_attachment(file, folder_name=None):
    """
    Save attachment as BLOB in MySQL.
    Bypasses Windows Defender / disk permission issues entirely.
    Returns token string "db:<uuid>" stored in the attachment columns.
    """
    if not file or not file.filename:
        return None
    allowed = {'png', 'jpg', 'jpeg', 'webp', 'pdf', 'doc', 'docx', 'xls', 'xlsx'}
    ext = file.filename.rsplit('.', 1)[-1].lower() if '.' in file.filename else ''
    if ext not in allowed:
        return None
    try:
        file_bytes  = file.read()
        orig_name   = secure_filename(file.filename)
        token       = uuid.uuid4().hex
        stored_name = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{token[:8]}_{orig_name}"
        mime_map = {
            'pdf':  'application/pdf',
            'doc':  'application/msword',
            'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'xls':  'application/vnd.ms-excel',
            'xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            'png':  'image/png',
            'jpg':  'image/jpeg',
            'jpeg': 'image/jpeg',
            'webp': 'image/webp',
        }
        mimetype = mime_map.get(ext, 'application/octet-stream')
        cur = mysql.connection.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS fms_exit_process_annex.exit_attachments (
                id          INT AUTO_INCREMENT PRIMARY KEY,
                token       VARCHAR(64) NOT NULL UNIQUE,
                filename    VARCHAR(255) NOT NULL,
                mimetype    VARCHAR(100) NOT NULL,
                filedata    LONGBLOB NOT NULL,
                uploaded_at DATETIME DEFAULT NOW()
            )
        """)
        cur.execute("""
            INSERT INTO fms_exit_process_annex.exit_attachments
                (token, filename, mimetype, filedata)
            VALUES (%s, %s, %s, %s)
        """, (token, stored_name, mimetype, file_bytes))
        mysql.connection.commit()
        cur.close()
        print(f"[UPLOAD] DB blob saved: {stored_name} ({len(file_bytes)} bytes) token={token}")
        return f"db:{token}"
    except Exception as e:
        import traceback
        print(f"[UPLOAD ERROR] {e}")
        traceback.print_exc()
        return None



def fms_hr_exit__get_all_dept_hod_ids():
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

def fms_hr_exit_is_primary(emp_code):   return emp_code in fms_hr_exit_PRIMARY_DOER_IDS
def fms_hr_exit_is_secondary(emp_code): return emp_code in fms_hr_exit_SECONDARY_DOER_IDS
def fms_hr_exit_is_admin(emp_code):     return emp_code in fms_hr_exit_ADMIN_IDS
def fms_hr_exit_is_hr_staff(emp_code):  return emp_code in fms_hr_exit_HR_STAFF_IDS or fms_hr_exit_is_admin(emp_code)

def fms_hr_exit_is_dept_hod(emp_code):
    return session.get('role') == 'dept_hod'

def fms_hr_exit_can_access_exit(emp_code):
    return (emp_code in fms_hr_exit_EXIT_ALL_ACCESS) or (session.get('role') == 'dept_hod')


def fms_hr_exit_get_session_role(emp_code):
    """
    Resolve and cache the FMS role for the given emp_code into session['role'].
    Called lazily on first access (e.g. dashboard, exit panel) rather than at login,
    so that the login route stays app-agnostic.
    Returns the resolved role string.
    """
    if 'role' in session:
        return session['role']

    dept_hod_ids  = fms_hr_exit__get_all_dept_hod_ids()
    is_a_dept_hod = emp_code in dept_hod_ids

    role = (
        'admin'      if emp_code in fms_hr_exit_ADMIN_IDS
        else 'primary'   if emp_code in fms_hr_exit_PRIMARY_DOER_IDS
        else 'secondary' if emp_code in fms_hr_exit_SECONDARY_DOER_IDS
        else 'dept_hod'  if is_a_dept_hod
        else 'employee'
    )
    session['role'] = role
    return role


# ================================== Stage Log + FMS Sync =====================================

def fms_hr_exit_log_stage(cur, exit_request_id, stage, action, done_by, remarks, attachment):
    cur.execute("""
        INSERT INTO fms_exit_process_annex.exit_stage_log
        (exit_request_id, stage, action, done_by, remarks, attachment)
        VALUES (%s,%s,%s,%s,%s,%s)
    """, (exit_request_id, stage, action, done_by, remarks, attachment))


fms_hr_exit_FMS_PROJECT = 'alcove'
fms_hr_exit_FMS_NAME    = 'hr_exit_process'

fms_hr_exit_STAGE_STATUS_MAP = {
    'P1': 'PENDING', 'P2': 'PENDING', 'P3': 'PENDING', 'P4': 'PENDING',
    'P5': 'PENDING', 'P6': 'PENDING', 'P7': 'PENDING',
    'P8': 'PENDING', 'P9': 'PENDING',   # COMPLETE only after action via close_all_tasks
}


def fms_hr_exit_fms_sync(main_cur, req_id, from_stage, to_stage, current_user_emp_id,
                         remarks=None, attachment=None, planned_end_time=None,
                         decision=None, allocate_to=None, allocate_emp_id=None):
    try:
        # ── 1. Get a fresh cursor from the active connection ──────────────────
        conn = main_cur.connection if hasattr(main_cur, 'connection') else mysql.connection
        cur  = conn.cursor(DictCursor)

        # ── 2. Fetch exit request + employee location ─────────────────────────
        cur.execute("""
            SELECT er.id,
                   er.employee_code,
                   er.employee_name,
                   er.hod,
                   er.hod_id,
                   er.reporting_doer,
                   er.reporting_doer_id,
                   er.department,
                   er.date_of_exit,
                   er.created_by,
                   COALESCE(em.Location, \'\') AS location
            FROM   fms_exit_process_annex.exit_requests er
            LEFT JOIN alcovedb_2024.Employee_Master em
                   ON er.employee_code COLLATE utf8mb4_unicode_ci
                    = em.Emp_Code      COLLATE utf8mb4_unicode_ci
            WHERE  er.id = %s
        """, (req_id,))
        er = cur.fetchone()
        if not er:
            cur.close()
            return

        # ── 3. Build field values ─────────────────────────────────────────────
        wf          = fms_hr_exit_WORKFLOW_HELP.get(to_stage, {})
        who         = wf.get('who', '')
        what        = wf.get('what', '')

        # task_name → one fixed name per request (updated in-place each stage)
        task_name   = f"REQ-{er['id']} | {er['employee_name']}"

        # task_details → current stage description
        task_detail = f"{who} — {what}" if (who or what) else to_stage

        # status → PENDING / COMPLETE / REJECTED
        status      = fms_hr_exit_STAGE_STATUS_MAP.get(to_stage, 'PENDING')

        # planned_end_time
        eff_planned = planned_end_time
        if eff_planned is None and er.get('date_of_exit'):
            eff_planned = fms_hr_exit_deadline_on_exit_day(er['date_of_exit'], dt_time(17, 0), er.get('location'))
        if isinstance(eff_planned, datetime):
            eff_planned = eff_planned.strftime('%Y-%m-%d %H:%M:%S')

        created_emp  = er.get('created_by') or current_user_emp_id
        alloc_to     = allocate_to     or er.get('reporting_doer',    '')
        alloc_emp_id = allocate_emp_id or er.get('reporting_doer_id', '')

        # ── 4. emp_id = all doers (persistent access list on the task row)
        #       actual_emp_id / submit_emp_id = current acting user only ────────
        all_doer_ids = sorted(
            fms_hr_exit_PRIMARY_DOER_IDS
            | fms_hr_exit_SECONDARY_DOER_IDS
            | fms_hr_exit_ADMIN_IDS
            | ({er['hod_id']} if er.get('hod_id') else set())
        )
        all_doers_str = ','.join(all_doer_ids)

        # ── 5. Check if a task row already exists for this request ────────────
        cur.execute("""
            SELECT task_id FROM fms_exit_process_annex.tasks
            WHERE  task_name = %s
            LIMIT  1
        """, (task_name,))
        existing = cur.fetchone()

        if existing is None:
            # ── 5a. P1 INSERT — submit_emp_id=current actor, actual_emp_id=current actor, emp_id=all doers
            cur.execute("""
                INSERT INTO fms_exit_process_annex.tasks
                    (task_name, current_stage, from_stage, status,
                     remark, attachment_path, planned_end_time, `1st_planned_end_time`,
                     submit_emp_id, actual_emp_id, emp_id, emp_name,
                     hod_id, hod_name,
                     actual_time,
                     allocate_to, allocate_emp_id,
                     created_emp_id, project, task_details,
                     pc_update_stage, fms_name, location)
                VALUES
                    (%s, %s, %s, %s,
                     %s, %s, %s, %s,
                     %s, %s, %s, %s,
                     %s, %s,
                     NOW(),
                     %s, %s,
                     %s, %s, %s,
                     %s, %s, %s)
            """, (
                task_name,              to_stage,               from_stage,             status,
                remarks,                attachment,             eff_planned,            eff_planned,
                current_user_emp_id,    current_user_emp_id,    all_doers_str,          er['employee_name'],
                er.get('hod_id', ''),   er.get('hod', ''),
                alloc_to,               alloc_emp_id,
                created_emp,            fms_hr_exit_FMS_PROJECT, task_detail,
                to_stage,               fms_hr_exit_FMS_NAME,   er.get('location', '')
            ))
            task_id = cur.lastrowid

        else:
            # ── 5b. UPDATE — current_stage=to_stage, from_stage, pc_update_stage=to_stage
            # submit_emp_id=current actor, actual_emp_id=current actor, emp_id=all doers
            task_id = existing['task_id']
            cur.execute("""
                UPDATE fms_exit_process_annex.tasks
                SET    current_stage    = %s,
                       from_stage       = %s,
                       status           = %s,
                       remark           = %s,
                       attachment_path  = %s,
                       planned_end_time = %s,
                       actual_time      = NOW(),
                       submit_emp_id    = %s,
                       actual_emp_id    = %s,
                       emp_id           = %s,
                       allocate_to      = %s,
                       allocate_emp_id  = %s,
                       task_details     = %s,
                       pc_update_stage  = %s
                WHERE  task_id = %s
            """, (
                to_stage,               from_stage,             status,
                remarks,                attachment,             eff_planned,
                current_user_emp_id,    current_user_emp_id,    all_doers_str,
                alloc_to,               alloc_emp_id,
                task_detail,            to_stage,
                task_id
            ))

        # ── 6. Next update_id ─────────────────────────────────────────────────
        cur.execute("""
            SELECT COALESCE(MAX(update_id), 0) + 1 AS nxt
            FROM   fms_exit_process_annex.task_updates
        """)
        nxt      = cur.fetchone()
        next_uid = int(nxt['nxt']) if nxt else 1

        # ── 7. INSERT task_updates — emp_id = current actor (only actor field in this table)
        cur.execute("""
            INSERT INTO fms_exit_process_annex.task_updates
                (update_id, task_id, task_name,
                 from_stage, to_stage,
                 remark, attachment_path, planned_end_time,
                 decision, emp_id, actual_time,
                 allocate_to, allocate_emp_id,
                 project, fms_name)
            VALUES
                (%s, %s, %s,
                 %s, %s,
                 %s, %s, %s,
                 %s, %s, NOW(),
                 %s, %s,
                 %s, %s)
        """, (
            next_uid,               task_id,                task_name,
            from_stage,             to_stage,
            remarks,                attachment,             eff_planned,
            decision,               current_user_emp_id,
            alloc_to,               alloc_emp_id,
            fms_hr_exit_FMS_PROJECT, fms_hr_exit_FMS_NAME
        ))

        cur.close()

    except Exception as exc:
        app.logger.error(f"[FMS] FAILED req={req_id} {from_stage}→{to_stage}: {exc}", exc_info=True)


def fms_hr_exit_close_all_tasks(main_cur, req_id, current_user_emp_id, remarks, final_stage):
    """
    At P8 (complete) or P9 (rejected): update the task row to COMPLETE /
    REJECTED and insert a final task_updates row as the closing audit entry.
    """
    try:
        conn = main_cur.connection if hasattr(main_cur, 'connection') else mysql.connection
        cur  = conn.cursor(DictCursor)

        # ── 1. Rebuild all_doers_str from the exit request ────────────────────
        cur.execute("""
            SELECT hod_id FROM fms_exit_process_annex.exit_requests WHERE id = %s
        """, (req_id,))
        er_row = cur.fetchone()

        all_doer_ids = sorted(
            fms_hr_exit_PRIMARY_DOER_IDS
            | fms_hr_exit_SECONDARY_DOER_IDS
            | fms_hr_exit_ADMIN_IDS
            | ({er_row['hod_id']} if er_row and er_row.get('hod_id') else set())
        )
        all_doers_str = ','.join(all_doer_ids)
        close_remark  = remarks or f"Process closed at stage {final_stage}"
        final_status  = 'COMPLETE'   # always COMPLETE — this runs only after P8/P9 action is taken

        # ── 2. Fetch the single task row for this request ─────────────────────
        cur.execute("""
            SELECT task_id, task_name, current_stage, fms_name,
                   allocate_to, allocate_emp_id, planned_end_time
            FROM   fms_exit_process_annex.tasks
            WHERE  task_name LIKE %s
            LIMIT  1
        """, (f"REQ-{req_id} |%",))
        task = cur.fetchone()

        if not task:
            cur.close()
            return

        task_id    = task['task_id']
        task_name  = task['task_name']
        from_stage = task['current_stage'] or task['fms_name'] or final_stage
        alloc_to   = task.get('allocate_to', '')
        alloc_eid  = task.get('allocate_emp_id', '')
        planned    = task.get('planned_end_time')
        if isinstance(planned, datetime):
            planned = planned.strftime('%Y-%m-%d %H:%M:%S')

        # ── 3. UPDATE tasks → COMPLETE after P8/P9 action ────────────────────
        cur.execute("""
            UPDATE fms_exit_process_annex.tasks
            SET    status           = %s,
                   current_stage    = %s,
                   from_stage       = %s,
                   actual_time      = NOW(),
                   remark           = %s,
                   submit_emp_id    = %s,
                   actual_emp_id    = %s,
                   emp_id           = %s,
                   task_details     = %s,
                   pc_update_stage  = %s
            WHERE  task_id = %s
        """, (
            final_status,           final_stage,            from_stage,
            close_remark,
            current_user_emp_id,    current_user_emp_id,    all_doers_str,
            f"Process closed at {final_stage} — {close_remark}",
            final_stage,            task_id
        ))

        # ── 4. Next update_id ─────────────────────────────────────────────────
        cur.execute("""
            SELECT COALESCE(MAX(update_id), 0) + 1 AS nxt
            FROM   fms_exit_process_annex.task_updates
        """)
        nxt_row  = cur.fetchone()
        next_uid = int(nxt_row['nxt']) if nxt_row else 1

        # ── 5. INSERT final task_updates row — emp_id = current actor
        cur.execute("""
            INSERT INTO fms_exit_process_annex.task_updates
                (update_id, task_id, task_name,
                 from_stage, to_stage,
                 remark, attachment_path, planned_end_time,
                 decision, emp_id, actual_time,
                 allocate_to, allocate_emp_id,
                 project, fms_name)
            VALUES
                (%s, %s, %s,
                 %s, %s,
                 %s, NULL, %s,
                 %s, %s, NOW(),
                 %s, %s,
                 %s, %s)
        """, (
            next_uid,               task_id,                task_name,
            from_stage,             final_stage,
            close_remark,           planned,
            final_status,           current_user_emp_id,
            alloc_to,               alloc_eid,
            fms_hr_exit_FMS_PROJECT, fms_hr_exit_FMS_NAME
        ))

        cur.close()

    except Exception as exc:
        app.logger.error(f"[FMS] close_all_tasks FAILED req={req_id}: {exc}", exc_info=True)


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
def fms_hr_exit_exit_panel():
    if 'emp_code' not in session:
        return redirect(url_for('login'))

    emp_code = session['emp_code']
    role     = session.get('role')

    no_pending_tasks = not fms_hr_exit_can_access_exit(emp_code)
    show_archived    = bool(request.args.get('show_archived'))

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
            WHERE  er.status IN ('COMPLETE','CANCELLED')
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
            WHERE  er.status IN ('PENDING','REJECTED')
            ORDER  BY er.id DESC
        """)

    raw_tasks     = cur.fetchall()
    display_tasks = []
    for t in raw_tasks:
        t = dict(t)
        t['_row_type'] = t.get('workflow_stage', '')
        display_tasks.append(t)

    cur.execute("""
        SELECT
            SUM(CASE WHEN status IN ('PENDING','REJECTED') THEN 1 ELSE 0 END) AS pending,
            SUM(CASE WHEN status='COMPLETE'               THEN 1 ELSE 0 END) AS completed,
            SUM(CASE WHEN status='CANCELLED'            THEN 1 ELSE 0 END) AS rejected,
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
        no_pending_tasks=no_pending_tasks,
        metrics=metrics,
        show_archived=show_archived,
        help_data=fms_hr_exit_WORKFLOW_HELP,
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
    if not fms_hr_exit_is_hr_staff(emp_code):
        return redirect(url_for('fms_hr_exit_exit_panel'))

    employee_code     = request.form.get('employee_code', '').strip().upper()
    employee_name     = request.form.get('employee_name', '').strip()
    department        = request.form.get('department', '').strip()
    hod               = request.form.get('hod', '').strip()
    hod_id            = request.form.get('hod_id', '').strip()
    _doj_raw = request.form.get('doj', '').strip()
    doj = None
    if _doj_raw:
        for _fmt in ('%Y-%m-%d', '%d/%m/%Y', '%d-%m-%Y', '%m/%d/%Y'):
            try:
                doj = datetime.strptime(_doj_raw, _fmt).strftime('%Y-%m-%d')
                break
            except ValueError:
                pass
    reporting_doer    = request.form.get('reporting_doer', '').strip()
    reporting_doer_id = request.form.get('reporting_doer_id', '').strip()
    _doe_raw = request.form.get('date_of_exit', '').strip()
    date_of_exit = None
    if _doe_raw:
        for _fmt in ('%Y-%m-%d', '%d/%m/%Y', '%d-%m-%Y', '%m/%d/%Y'):
            try:
                date_of_exit = datetime.strptime(_doe_raw, _fmt).strftime('%Y-%m-%d')
                break
            except ValueError:
                pass
    remarks           = request.form.get('remarks', '').strip()

    if not employee_code or not date_of_exit:
        return redirect(url_for('fms_hr_exit_exit_panel'))

    cur_check = mysql.connection.cursor(DictCursor)
    cur_check.execute("""
        SELECT Emp_Code, STATUS, Location FROM alcovedb_2024.Employee_Master
        WHERE Emp_Code=%s
    """, (employee_code,))
    emp_check = cur_check.fetchone()
    cur_check.close()

    if not emp_check:
        return redirect(url_for('fms_hr_exit_exit_panel'))

    location    = emp_check.get('Location') or ''
    attach_path = fms_hr_exit_save_attachment(request.files.get('attachment'), 'exit_p1')
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
                'PENDING','P2',
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

    return redirect(url_for('fms_hr_exit_exit_panel'))


# ================================== P2 — HOD Confirmation Decision ===========================

@app.route('/exit/<int:req_id>/p2_decision', methods=['POST'])
def fms_hr_exit_exit_p2_decision(req_id):
    if 'emp_code' not in session:
        return redirect(url_for('login'))

    emp_code = session['emp_code']
    if not fms_hr_exit_is_hr_staff(emp_code):
        return redirect(url_for('fms_hr_exit_exit_panel'))

    decision    = request.form.get('decision', '').upper()
    remarks     = request.form.get('remarks', '').strip()
    attach_path = fms_hr_exit_save_attachment(request.files.get('attachment'), 'exit_p2')

    if decision not in ('YES', 'NO'):
        return redirect(url_for('fms_hr_exit_exit_panel'))

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
        deadline = fms_hr_exit_calculate_deadline(datetime.now(), fms_hr_exit_STAGE_TIME_LIMITS['P3'], location)
        cur.execute("""
            UPDATE fms_exit_process_annex.exit_requests
            SET workflow_stage='P3',
                p2_decision='YES', p2_remarks=%s, p2_attachment=%s,
                p2_done_by=%s, p2_done_at=NOW(),
                stage_started_at=NOW(), deadline_at=%s
            WHERE id=%s AND status='PENDING'
        """, (remarks, attach_path, emp_code, deadline, req_id))
        fms_hr_exit_log_stage(cur, req_id, 'P2', 'Resignation accepted by HOD → P3', emp_code, remarks, attach_path)
        fms_hr_exit_fms_sync(cur, req_id, 'P2', 'P3', emp_code,
                 remarks=remarks, attachment=attach_path, planned_end_time=deadline, decision='YES')
    else:
        p9_deadline = fms_hr_exit_calculate_deadline(datetime.now(), fms_hr_exit_STAGE_TIME_LIMITS['P9'], location)
        cur.execute("""
            UPDATE fms_exit_process_annex.exit_requests
            SET workflow_stage='P9', status='REJECTED',
                p2_decision='NO', p2_remarks=%s, p2_attachment=%s,
                p2_done_by=%s, p2_done_at=NOW(),
                p9_remarks=%s, p9_done_by=%s, p9_done_at=NOW(),
                stage_started_at=NOW(), deadline_at=%s
            WHERE id=%s AND status='PENDING'
        """, (remarks, attach_path, emp_code, remarks, emp_code, p9_deadline, req_id))
        fms_hr_exit_log_stage(cur, req_id, 'P2', 'Resignation rejected by HOD → P9 end', emp_code, remarks, attach_path)
        fms_hr_exit_fms_sync(cur, req_id, 'P2', 'P9', emp_code,
                 remarks=remarks, attachment=attach_path, decision='NO', planned_end_time=p9_deadline)

    mysql.connection.commit()
    cur.close()
    return redirect(url_for('fms_hr_exit_exit_panel'))


# ================================== P9 — Acknowledge Rejection (Close) ======================

@app.route('/exit/<int:req_id>/p9_close', methods=['POST'])
def fms_hr_exit_exit_p9_close(req_id):
    if 'emp_code' not in session:
        return redirect(url_for('login'))

    emp_code = session['emp_code']
    if not fms_hr_exit_is_hr_staff(emp_code):
        return redirect(url_for('fms_hr_exit_exit_panel'))

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
    fms_hr_exit_close_all_tasks(cur, req_id, emp_code, remarks or 'Rejection acknowledged — process closed.', 'P9')
    mysql.connection.commit()
    cur.close()

    return redirect(url_for('fms_hr_exit_exit_panel'))


# ================================== P3 — Update Exit Details =================================

@app.route('/exit/<int:req_id>/p3_update', methods=['POST'])
def fms_hr_exit_exit_p3_update(req_id):
    if 'emp_code' not in session:
        return redirect(url_for('login'))

    emp_code = session['emp_code']
    if not fms_hr_exit_is_hr_staff(emp_code):
        return redirect(url_for('fms_hr_exit_exit_panel'))

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
    row = cur.fetchone()
    cur.close()

    location    = (row or {}).get('Location') or ''
    p4_deadline = None
    if row and row.get('date_of_exit'):
        p4_date     = row['date_of_exit'] - timedelta(days=7)
        p4_holidays = fms_hr_exit__fetch_holidays(location)
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
        WHERE id=%s AND status='PENDING'
    """, (remarks, attach_path, emp_code, p4_deadline, req_id))
    fms_hr_exit_log_stage(cur2, req_id, 'P3', 'Exit details updated — moving to P4 (Dept HOD: System Team Mail)', emp_code, remarks, attach_path)
    fms_hr_exit_fms_sync(cur2, req_id, 'P3', 'P4', emp_code,
             remarks=remarks, attachment=attach_path, planned_end_time=p4_deadline)
    mysql.connection.commit()
    cur2.close()

    return redirect(url_for('fms_hr_exit_exit_panel'))


# ================================== P5 — Share Exit Interview Link ===========================

@app.route('/exit/<int:req_id>/p5_done', methods=['POST'])
def fms_hr_exit_exit_p5_done(req_id):
    if 'emp_code' not in session:
        return redirect(url_for('login'))

    emp_code = session['emp_code']
    if not fms_hr_exit_is_hr_staff(emp_code):
        return redirect(url_for('fms_hr_exit_exit_panel'))

    remarks     = request.form.get('remarks', '').strip()
    attach_path = fms_hr_exit_save_attachment(request.files.get('attachment'), 'exit_p5')

    cur = mysql.connection.cursor(DictCursor)
    cur.execute("""
        SELECT date_of_exit FROM fms_exit_process_annex.exit_requests
        WHERE id=%s AND status='PENDING' AND workflow_stage='P5'
    """, (req_id,))
    row = cur.fetchone()
    cur.close()

    if not row:
        return redirect(url_for('fms_hr_exit_exit_panel'))

    p6_dl = fms_hr_exit_deadline_on_exit_day(row['date_of_exit'], dt_time(14, 0), row.get('location')) if row.get('date_of_exit') else None

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

    return redirect(url_for('fms_hr_exit_exit_panel'))


# ================================== P4 — Mail System Team (Dept HOD) → advance to P5 =========

@app.route('/exit/<int:req_id>/p4_done', methods=['POST'])
def fms_hr_exit_exit_p4_done(req_id):
    if 'emp_code' not in session:
        return redirect(url_for('login'))

    emp_code = session['emp_code']
    role     = session.get('role')

    if role not in ('dept_hod', 'admin'):
        return redirect(url_for('fms_hr_exit_exit_panel'))

    remarks     = request.form.get('remarks', '').strip()
    new_person  = request.form.get('new_assigned_person', '').strip()
    attach_path = fms_hr_exit_save_attachment(request.files.get('attachment'), 'exit_p4')

    cur = mysql.connection.cursor(DictCursor)
    cur.execute("""
        SELECT date_of_exit FROM fms_exit_process_annex.exit_requests
        WHERE id=%s AND status='PENDING' AND workflow_stage='P4'
    """, (req_id,))
    row = cur.fetchone()
    cur.close()

    if not row:
        return redirect(url_for('fms_hr_exit_exit_panel'))

    p5_deadline = fms_hr_exit_deadline_on_exit_day(row['date_of_exit'], dt_time(11, 0), row.get('location')) if row.get('date_of_exit') else None

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

    return redirect(url_for('fms_hr_exit_exit_panel'))


# ================================== P6 — Handover + Clearance ================================

@app.route('/exit/<int:req_id>/p6_done', methods=['POST'])
def fms_hr_exit_exit_p6_done(req_id):
    if 'emp_code' not in session:
        return redirect(url_for('login'))

    emp_code = session['emp_code']
    if not fms_hr_exit_is_hr_staff(emp_code):
        return redirect(url_for('fms_hr_exit_exit_panel'))

    remarks     = request.form.get('remarks', '').strip()
    attach_path = fms_hr_exit_save_attachment(request.files.get('attachment'), 'exit_p6')

    cur_dt5 = mysql.connection.cursor(DictCursor)
    cur_dt5.execute("SELECT date_of_exit FROM fms_exit_process_annex.exit_requests WHERE id=%s", (req_id,))
    dt_row5 = cur_dt5.fetchone(); cur_dt5.close()
    p6_dl = fms_hr_exit_deadline_on_exit_day(dt_row5['date_of_exit'], dt_time(16, 0)) if dt_row5 and dt_row5['date_of_exit'] else None

    cur = mysql.connection.cursor()
    cur.execute("""
        UPDATE fms_exit_process_annex.exit_requests
        SET workflow_stage='P7',
            p6_remarks=%s, p6_attachment=%s,
            p6_done_by=%s, p6_done_at=NOW(),
            stage_started_at=NOW(), deadline_at=%s
        WHERE id=%s AND status='PENDING'
    """, (remarks, attach_path, emp_code, p6_dl, req_id))
    fms_hr_exit_log_stage(cur, req_id, 'P6', 'Handover doc + asset clearance done', emp_code, remarks, attach_path)
    fms_hr_exit_fms_sync(cur, req_id, 'P6', 'P7', emp_code, remarks=remarks, attachment=attach_path, planned_end_time=p6_dl)
    mysql.connection.commit()
    cur.close()

    return redirect(url_for('fms_hr_exit_exit_panel'))


# ================================== P7 — Issue Release + Experience Letter ===================

@app.route('/exit/<int:req_id>/p7_done', methods=['POST'])
def fms_hr_exit_exit_p7_done(req_id):
    if 'emp_code' not in session:
        return redirect(url_for('login'))

    emp_code = session['emp_code']
    if not fms_hr_exit_is_hr_staff(emp_code):
        return redirect(url_for('fms_hr_exit_exit_panel'))

    remarks     = request.form.get('remarks', '').strip()
    attach_path = fms_hr_exit_save_attachment(request.files.get('attachment'), 'exit_p7')

    cur_dt6 = mysql.connection.cursor(DictCursor)
    cur_dt6.execute("SELECT date_of_exit FROM fms_exit_process_annex.exit_requests WHERE id=%s", (req_id,))
    dt_row6 = cur_dt6.fetchone(); cur_dt6.close()
    p7_dl = fms_hr_exit_deadline_on_exit_day(dt_row6['date_of_exit'], dt_time(17, 0)) if dt_row6 and dt_row6['date_of_exit'] else None

    cur = mysql.connection.cursor()
    cur.execute("""
        UPDATE fms_exit_process_annex.exit_requests
        SET workflow_stage='P8',
            p7_remarks=%s, p7_attachment=%s,
            p7_done_by=%s, p7_done_at=NOW(),
            stage_started_at=NOW(), deadline_at=%s
        WHERE id=%s AND status='PENDING'
    """, (remarks, attach_path, emp_code, p7_dl, req_id))
    fms_hr_exit_log_stage(cur, req_id, 'P7', 'Release letter + experience letter issued', emp_code, remarks, attach_path)
    fms_hr_exit_fms_sync(cur, req_id, 'P7', 'P8', emp_code, remarks=remarks, attachment=attach_path, planned_end_time=p7_dl)
    mysql.connection.commit()
    cur.close()

    return redirect(url_for('fms_hr_exit_exit_panel'))


# ================================== P8 — Mark Inactive & Close (FINAL) ======================

@app.route('/exit/<int:req_id>/p8_done', methods=['POST'])
def fms_hr_exit_exit_p8_done(req_id):
    if 'emp_code' not in session:
        return redirect(url_for('login'))

    emp_code = session['emp_code']
    if not fms_hr_exit_is_hr_staff(emp_code):
        return redirect(url_for('fms_hr_exit_exit_panel'))

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
        return redirect(url_for('fms_hr_exit_exit_panel'))

    if row.get('p4_status') != 'DONE':
        return redirect(url_for('fms_hr_exit_exit_panel'))

    cur2 = mysql.connection.cursor(DictCursor)
    cur2.execute("SELECT date_of_exit FROM fms_exit_process_annex.exit_requests WHERE id=%s", (req_id,))
    dt_row8 = cur2.fetchone()
    p8_dl = fms_hr_exit_deadline_on_exit_day(dt_row8['date_of_exit'], dt_time(17, 0)) if dt_row8 and dt_row8.get('date_of_exit') else None

    cur2.execute("""
        UPDATE fms_exit_process_annex.exit_requests
        SET workflow_stage='P8', status='COMPLETE',
            p8_remarks=%s, p8_attachment=%s,
            p8_done_by=%s, p8_done_at=NOW()
        WHERE id=%s
    """, (remarks, attach_path, emp_code, req_id))
    fms_hr_exit_log_stage(cur2, req_id, 'P8', 'Exit process closed — employee marked inactive via HR portal', emp_code, remarks, attach_path)
    fms_hr_exit_close_all_tasks(cur2, req_id, emp_code, remarks, 'P8')
    mysql.connection.commit()
    cur2.close()

    return redirect(url_for('fms_hr_exit_exit_panel'))


# ================================== Exit Request Detail ======================================

@app.route('/exit/<int:req_id>/detail')
def fms_hr_exit_exit_detail(req_id):
    if 'emp_code' not in session:
        return redirect(url_for('login'))

    emp_code = session['emp_code']
    if not fms_hr_exit_can_access_exit(emp_code):
        return redirect(url_for('fms_hr_exit_exit_admin_dashboard'))

    cur = mysql.connection.cursor(DictCursor)
    cur.execute("""
        SELECT er.*,
               em.Person_Accountable AS employee_name_full,
               em.Designation, em.Location, em.Company,
               em.Contact_number, em.Email_ID_Official
        FROM   fms_exit_process_annex.exit_requests er
        LEFT JOIN alcovedb_2024.Employee_Master em
               ON er.employee_code COLLATE utf8mb4_unicode_ci = em.Emp_Code COLLATE utf8mb4_unicode_ci
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
        return redirect(url_for('fms_hr_exit_exit_panel'))

    role = session.get('role')
    return render_template(
        'fms_hr_exit_exit_detail.html',
        req=req_data,
        audit_log=audit_log,
        help_data=fms_hr_exit_WORKFLOW_HELP,
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
        return redirect(url_for('fms_hr_exit_exit_panel'))

    cur = mysql.connection.cursor(DictCursor)
    cur.execute("""
        SELECT er.*,
               COALESCE(em.Person_Accountable, er.employee_name) AS employee_name,
               COALESCE(em.Department, er.department)            AS department,
               em.Designation
        FROM   fms_exit_process_annex.exit_requests er
        LEFT JOIN alcovedb_2024.Employee_Master em
               ON er.employee_code COLLATE utf8mb4_unicode_ci = em.Emp_Code COLLATE utf8mb4_unicode_ci
        ORDER  BY er.id DESC
    """)
    tasks = cur.fetchall()
    cur.close()

    metrics = {
        "total":     len(tasks),
        "pending":   sum(1 for t in tasks if t['status'] == 'PENDING'),
        "completed": sum(1 for t in tasks if t['status'] == 'COMPLETE'),
        "rejected":  sum(1 for t in tasks if t['status'] in ('REJECTED', 'CANCELLED')),
    }

    return render_template(
        'exit_admin_stage_dashboard.html',
        tasks=tasks,
        metrics=metrics,
        help_data=fms_hr_exit_WORKFLOW_HELP,
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
def fms_hr_exit_exit_admin_stage_dashboard():
    if 'emp_code' not in session:
        return redirect(url_for('login'))

    emp_code = session['emp_code']
    if not fms_hr_exit_is_admin(emp_code):
        return redirect(url_for('fms_hr_exit_exit_panel'))

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

#==============================================FMS CODE ENDS HERE================================================
# ================================== Run =============================================

if __name__ == "__main__":
    app.run(debug=True, port=5001)