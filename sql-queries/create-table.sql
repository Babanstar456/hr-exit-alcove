-- ============================================================
-- HR EXIT PROCESS — Full Table Creation SQL
-- Databases: fms_exit_process_annex, alcovedb_2024, alcove_checklist
-- ============================================================

-- ── Create schemas if not exists ─────────────────────────────
CREATE DATABASE IF NOT EXISTS fms_exit_process_annex
    CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

CREATE DATABASE IF NOT EXISTS alcovedb_2024
    CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

CREATE DATABASE IF NOT EXISTS alcove_checklist
    CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;


-- ============================================================
-- DATABASE: alcovedb_2024
-- ============================================================

CREATE TABLE IF NOT EXISTS alcovedb_2024.Employee_Master (
    Emp_Code            VARCHAR(20)     NOT NULL PRIMARY KEY,
    Person_Accountable  VARCHAR(255)    DEFAULT NULL,
    password            VARCHAR(255)    DEFAULT NULL,
    Designation         VARCHAR(255)    DEFAULT NULL,
    Department          VARCHAR(255)    DEFAULT NULL,
    Admin               TINYINT(1)      DEFAULT 0,
    Photo_Link          VARCHAR(500)    DEFAULT NULL,
    Email_ID_Official   VARCHAR(255)    DEFAULT NULL,
    Contact_number      VARCHAR(20)     DEFAULT NULL,
    user_Access         VARCHAR(100)    DEFAULT NULL,
    Reporting_DOER      VARCHAR(255)    DEFAULT NULL,
    Reporting_DOER_id   VARCHAR(20)     DEFAULT NULL,
    HOD                 VARCHAR(255)    DEFAULT NULL,
    HOD_ID              VARCHAR(20)     DEFAULT NULL,
    DOJ                 DATE            DEFAULT NULL,
    Location            VARCHAR(255)    DEFAULT NULL,
    Company             VARCHAR(255)    DEFAULT NULL,
    STATUS              VARCHAR(20)     DEFAULT 'ACTIVE'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


CREATE TABLE IF NOT EXISTS alcovedb_2024.Password_Records (
    id          INT             NOT NULL AUTO_INCREMENT PRIMARY KEY,
    Emp_Code    VARCHAR(20)     NOT NULL,
    New_Password VARCHAR(255)   NOT NULL,
    changed_at  DATETIME        DEFAULT NOW()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


-- ============================================================
-- DATABASE: alcove_checklist
-- ============================================================

CREATE TABLE IF NOT EXISTS alcove_checklist.holidaylist (
    id              INT             NOT NULL AUTO_INCREMENT PRIMARY KEY,
    holiday_name    VARCHAR(255)    NOT NULL,
    date            DATE            NOT NULL,
    location        VARCHAR(255)    DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


-- ============================================================
-- DATABASE: fms_exit_process_annex
-- ============================================================

-- ── 1. exit_requests ─────────────────────────────────────────
CREATE TABLE IF NOT EXISTS fms_exit_process_annex.exit_requests (
    id                  INT             NOT NULL AUTO_INCREMENT PRIMARY KEY,

    -- Employee info
    employee_code       VARCHAR(20)     DEFAULT NULL,
    employee_name       VARCHAR(255)    DEFAULT NULL,
    department          VARCHAR(255)    DEFAULT NULL,
    hod                 VARCHAR(255)    DEFAULT NULL,
    hod_id              VARCHAR(20)     DEFAULT NULL,
    doj                 DATE            DEFAULT NULL,
    reporting_doer      VARCHAR(255)    DEFAULT NULL,
    reporting_doer_id   VARCHAR(20)     DEFAULT NULL,
    date_of_exit        DATE            DEFAULT NULL,

    -- Workflow control
    status              ENUM('PENDING','COMPLETE','REJECTED','CANCELLED')
                                        NOT NULL DEFAULT 'PENDING',
    workflow_stage      VARCHAR(10)     DEFAULT 'P1',
    stage_started_at    DATETIME        DEFAULT NULL,
    deadline_at         DATETIME        DEFAULT NULL,
    created_by          VARCHAR(20)     DEFAULT NULL,
    created_at          DATETIME        DEFAULT NOW(),

    -- P1 — Receive Resignation
    p1_remarks          TEXT            DEFAULT NULL,
    p1_attachment       VARCHAR(255)    DEFAULT NULL,
    p1_done_by          VARCHAR(20)     DEFAULT NULL,
    p1_done_at          DATETIME        DEFAULT NULL,

    -- P2 — HOD Confirmation
    p2_decision         VARCHAR(10)     DEFAULT NULL,
    p2_remarks          TEXT            DEFAULT NULL,
    p2_attachment       VARCHAR(255)    DEFAULT NULL,
    p2_done_by          VARCHAR(20)     DEFAULT NULL,
    p2_done_at          DATETIME        DEFAULT NULL,

    -- P3 — Update Exit Details
    p3_remarks          TEXT            DEFAULT NULL,
    p3_attachment       VARCHAR(255)    DEFAULT NULL,
    p3_done_by          VARCHAR(20)     DEFAULT NULL,
    p3_done_at          DATETIME        DEFAULT NULL,

    -- P4 — Mail System Team for Task Transfer
    p4_status           VARCHAR(20)     DEFAULT NULL,
    p4_remarks          TEXT            DEFAULT NULL,
    p4_attachment       VARCHAR(255)    DEFAULT NULL,
    p4_done_by          VARCHAR(20)     DEFAULT NULL,
    p4_done_at          DATETIME        DEFAULT NULL,

    -- P5 — Share Exit Interview Link
    p5_remarks          TEXT            DEFAULT NULL,
    p5_attachment       VARCHAR(255)    DEFAULT NULL,
    p5_done_by          VARCHAR(20)     DEFAULT NULL,
    p5_done_at          DATETIME        DEFAULT NULL,

    -- P6 — Handover Doc + Asset / Clearance
    p6_remarks          TEXT            DEFAULT NULL,
    p6_attachment       VARCHAR(255)    DEFAULT NULL,
    p6_done_by          VARCHAR(20)     DEFAULT NULL,
    p6_done_at          DATETIME        DEFAULT NULL,

    -- P7 — Issue Release + Experience Letter
    p7_remarks          TEXT            DEFAULT NULL,
    p7_attachment       VARCHAR(255)    DEFAULT NULL,
    p7_done_by          VARCHAR(20)     DEFAULT NULL,
    p7_done_at          DATETIME        DEFAULT NULL,

    -- P8 — Mark Employee Inactive
    p8_remarks          TEXT            DEFAULT NULL,
    p8_attachment       VARCHAR(255)    DEFAULT NULL,
    p8_done_by          VARCHAR(20)     DEFAULT NULL,
    p8_done_at          DATETIME        DEFAULT NULL,

    -- P9 — Reject Resignation
    p9_remarks          TEXT            DEFAULT NULL,
    p9_attachment       VARCHAR(255)    DEFAULT NULL,
    p9_done_by          VARCHAR(20)     DEFAULT NULL,
    p9_done_at          DATETIME        DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


-- ── 2. exit_stage_log ────────────────────────────────────────
CREATE TABLE IF NOT EXISTS fms_exit_process_annex.exit_stage_log (
    id                  INT             NOT NULL AUTO_INCREMENT PRIMARY KEY,
    exit_request_id     INT             NOT NULL,
    stage               VARCHAR(10)     NOT NULL,
    action              TEXT            DEFAULT NULL,
    done_by             VARCHAR(20)     DEFAULT NULL,
    remarks             TEXT            DEFAULT NULL,
    attachment          VARCHAR(255)    DEFAULT NULL,
    done_at             DATETIME        DEFAULT NOW(),

    INDEX idx_exit_request_id (exit_request_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


-- ── 3. exit_attachments ──────────────────────────────────────
CREATE TABLE IF NOT EXISTS fms_exit_process_annex.exit_attachments (
    id              INT             NOT NULL AUTO_INCREMENT PRIMARY KEY,
    token           VARCHAR(64)     NOT NULL UNIQUE,
    filename        VARCHAR(255)    NOT NULL,
    mimetype        VARCHAR(100)    NOT NULL,
    filedata        LONGBLOB        NOT NULL,
    uploaded_at     DATETIME        DEFAULT NOW()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


-- ── 4. tasks ─────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS fms_exit_process_annex.tasks (
    task_id             INT             NOT NULL AUTO_INCREMENT PRIMARY KEY,
    task_name           VARCHAR(255)    DEFAULT NULL UNIQUE,
    current_stage       VARCHAR(10)     DEFAULT NULL,
    from_stage          VARCHAR(10)     DEFAULT NULL,
    status              ENUM('PENDING','COMPLETE')
                                        NOT NULL DEFAULT 'PENDING',
    remark              TEXT            DEFAULT NULL,
    attachment_path     VARCHAR(255)    DEFAULT NULL,
    planned_end_time    DATETIME        DEFAULT NULL,
    `1st_planned_end_time` DATETIME     DEFAULT NULL,
    submit_emp_id       VARCHAR(255)    DEFAULT NULL,
    emp_id              VARCHAR(255)    DEFAULT NULL,
    emp_name            VARCHAR(255)    DEFAULT NULL,
    actual_emp_id       VARCHAR(255)    DEFAULT NULL,
    location            VARCHAR(255)    DEFAULT NULL,
    hod_id              VARCHAR(255)    DEFAULT NULL,
    hod_name            VARCHAR(255)    DEFAULT NULL,
    actual_time         DATETIME        DEFAULT NULL,
    created_at          DATETIME        DEFAULT CURRENT_TIMESTAMP,
    allocate_to         VARCHAR(255)    DEFAULT NULL,
    allocate_emp_id     VARCHAR(255)    DEFAULT NULL,
    created_emp_id      VARCHAR(255)    DEFAULT NULL,
    project             VARCHAR(255)    DEFAULT NULL,
    task_details        VARCHAR(500)    DEFAULT NULL,
    pc_update_stage     VARCHAR(10)     DEFAULT NULL,
    fms_name            VARCHAR(50)     DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


-- ── 5. task_updates ──────────────────────────────────────────
CREATE TABLE IF NOT EXISTS fms_exit_process_annex.task_updates (
    update_id           INT             NOT NULL PRIMARY KEY,
    task_id             INT             DEFAULT NULL,
    task_name           VARCHAR(255)    DEFAULT NULL,
    from_stage          VARCHAR(10)     DEFAULT NULL,
    to_stage            VARCHAR(10)     DEFAULT NULL,
    remark              TEXT            DEFAULT NULL,
    attachment_path     VARCHAR(255)    DEFAULT NULL,
    planned_end_time    DATETIME        DEFAULT NULL,
    decision            VARCHAR(10)     DEFAULT NULL,
    emp_id              VARCHAR(50)     DEFAULT NULL,
    actual_time         DATETIME        DEFAULT NULL,
    allocate_to         VARCHAR(255)    DEFAULT NULL,
    allocate_emp_id     VARCHAR(50)     DEFAULT NULL,
    project             VARCHAR(255)    DEFAULT NULL,
    fms_name            VARCHAR(50)     DEFAULT NULL,

    INDEX idx_task_id (task_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;