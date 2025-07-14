from flask import Flask, render_template, request, redirect, session, jsonify, send_file
from datetime import datetime, timedelta
import pdfkit
from io import BytesIO
import psycopg2
import platform
import shutil

app = Flask(__name__)
app.secret_key = 'your_secret_key'

if platform.system() == "Windows":
    # Use local Windows path
    config = pdfkit.configuration(wkhtmltopdf=r".\wkhtmltopdf\bin\wkhtmltopdf.exe")
else:
    # On Render (Linux), ensure wkhtmltopdf is in PATH
    wkhtmltopdf_path = shutil.which("wkhtmltopdf")
    if wkhtmltopdf_path is None:
        raise OSError("wkhtmltopdf not found on system PATH. Please install it.")
    config = pdfkit.configuration(wkhtmltopdf=wkhtmltopdf_path)


def get_db_connection():
    return psycopg2.connect(
        database="MCPL01",
        host="dpg-d1h20lvgi27c73c75i9g-a.oregon-postgres.render.com",
        port="5432",
        user="mahesh",
        password="Jk3YQreoLTe05itpp3mz0vI4ssBCzB4x"
    )

@app.route("/")
def dashboard():
    if "emp_name" in session:
        return render_template("dashboard.html")
    else:
        return render_template("login.html", message="Your session has been timed out. Please Log in again.")
    

@app.route("/get_project_history_by_code")
def get_project_history_by_code():
    project_code = request.args.get("code")
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT ph."ProjectHistoryID", ph."EventDate", um."EmpName", ph."Event", ph."Remarks", wm."WorkType", ph."IsHistory"
    FROM "ProjectHistory" ph
    JOIN "UserMaster" um ON ph."UserID" = um."UserID"
    JOIN "ProjectMaster" pm ON ph."ProjectID" = pm."ProjectID"
    JOIN "WorkTypeMaster" wm ON ph."WorkTypeID" = wm."WorkTypeID"
    WHERE pm."ProjectCode" = %s
    ORDER BY ph."EventDate" DESC
    """, (project_code,))
    data = cursor.fetchall()
    records = [
        {
            "SrNo": i+1,
            "ProjectHistoryID": row[0],
            "EventDate": row[1].strftime('%d %b %Y'),
            "EmpName": row[2],
            "Event": row[3],
            "Remarks": row[4],
            "WorkType": row[5],
            "IsHistory": row[6]
        }
        for i, row in enumerate(data)
    ]
    return jsonify(records)


@app.route("/get_project_history_by_id/<int:history_id>")
def get_project_history_by_id(history_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT "ProjectHistoryID", "EventDate", "Event", "Remarks", "WorkTypeID", "IsHistory"
        FROM "ProjectHistory"
        WHERE "ProjectHistoryID" = %s
    ''', (history_id,))
    row = cursor.fetchone()
    if row:
        return jsonify({
            "ProjectHistoryID": row[0],
            "EventDate": row[1].strftime("%Y-%m-%d"),
            "Event": row[2],
            "Remarks": row[3],
            "WorkTypeID": row[4],
            "IsHistory": row[5]# Send this too
        })
    return jsonify({})


    
# Also used for task performed
@app.route("/project_hist", methods=["GET", "POST"])
def project_history():
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('SELECT "ProjectCode", "ProjectName" FROM "ProjectMaster" ORDER BY "ProjectCode"')
    projects = [{"code": row[0], "name": row[1]} for row in cursor.fetchall()]
    
    cursor.execute('SELECT "WorkTypeID", "WorkType" FROM "WorkTypeMaster" ORDER BY "WorkType"')
    work_type = [{"id": row[0], "work_type": row[1]} for row in cursor.fetchall()]

    today = datetime.today().strftime('%Y-%m-%d')

    if request.method == "POST":
        project_code = request.form['project_code']
        emp_name = session['emp_name']
        workType = request.form['work_type']
        entry_date = request.form['entry_date']
        event_date = request.form['event_date']
        event_desc = request.form['event_desc']
        remarks = request.form['remarks']
        isHistory = request.form.get("isHistory","false").lower() == "true"
        history_id = request.form.get("project_history_id")


        cursor.execute('SELECT "ProjectID" FROM "ProjectMaster" WHERE "ProjectCode" = %s', (project_code,))
        project_row = cursor.fetchone()
        project_id = project_row[0] if project_row else None

        cursor.execute('SELECT "UserID" FROM "UserMaster" WHERE "EmpName" = %s', (emp_name,))
        user_row = cursor.fetchone()
        user_id = user_row[0] if user_row else None
        

        if project_id and user_id:
            if history_id:
                cursor.execute('''
                    UPDATE "ProjectHistory"
                    SET "EventDate" = %s,
                        "Event" = %s,
                        "Remarks" = %s,
                        "IsHistory" = %s,
                        "WorkTypeID" = %s
                    WHERE "ProjectHistoryID" = %s
                ''', (event_date, event_desc, remarks, isHistory, workType, history_id))
                conn.commit()
                message = "Record Updated Successfully"
            else:
                cursor.execute('''
                    INSERT INTO "ProjectHistory" (
                    "ProjectID", "UserID", "ProjectHistoryGUID", 
                    "DateOfEntry", "EventDate", "Event", "Remarks", 
                    "IsHistory", "WorkTypeID"
                )
                VALUES (%s, %s, gen_random_uuid(), %s, %s, %s, %s, %s, %s)
            ''', (project_id, user_id, entry_date, event_date, event_desc, remarks, isHistory, workType))
                conn.commit()
                message = "Record Saved Successfully"

        return render_template("project_history.html", 
                               message=message, 
                               projects=projects, 
                               today=today,work_type=work_type)

    return render_template("project_history.html", projects=projects, today=today, work_type=work_type)



@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == 'POST':
        print("In Login")
        org_code = request.form.get('org_code', '').strip().upper()
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()

        conn = get_db_connection()
        cursor = conn.cursor()

        # Get OrganisationID from OrgCode
        cursor.execute('SELECT "OrganisationID" FROM "OrganisationMaster" WHERE "OrgCode" = %s', (org_code,))
        org = cursor.fetchone()

        if not org:
            conn.close()
            return render_template('login.html', error="Invalid Organization Code")

        org_id = org[0]

        # Validate user
        cursor.execute('''
            SELECT "EmpName", "UserName", "UserCategory", "DesignationID"
            FROM "UserMaster"
            WHERE "UserName" = %s AND "UserPWD" = %s AND "OrganisationID" = %s
        ''', (username, password, org_id))

        user = cursor.fetchone()
        

        if user:
            session['username'] = user[1]
            session['emp_name'] = user[0]
            session['user_category'] = user[2]
            session['organisation_id'] = org_id
            cursor.execute('SELECT "DesignationName" FROM "DesignationMaster" WHERE "DesignationID" = %s',(user[3],))
            designation = cursor.fetchone()
            session['designation'] = designation[0]
            return redirect('/')
        else:
            return render_template('login.html', error="Invalid Username or Password")

    return render_template("login.html")


@app.route("/validate_org")
def validate_org():
    org_code = request.args.get('org_code', '').strip().upper()
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT 1 FROM "OrganisationMaster" WHERE "OrgCode" = %s', (org_code.upper(),))
    result = cursor.fetchone()
    print(result)
    conn.close()
    return jsonify({'valid': bool(result)})


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

@app.route("/tasks_performed", methods=["GET","POST"])
def tasks_performed():

    return render_template("tasks_performed.html",message="This Page is under Development")


@app.route("/project_hist_report", methods=["GET","POST"])
def project_history_report():
    
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('SELECT "ProjectCode", "ProjectName" FROM "ProjectMaster" ORDER BY "ProjectCode"')
    projects = [{"code": row[0], "name": row[1]} for row in cursor.fetchall()]

    today = datetime.today().strftime('%Y-%m-%d')
    
    return render_template("project_history_report.html",projects=projects, today=today)

@app.route("/task_performed_report", methods=["GET","POST"])
def tasks_performed_report():
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('SELECT "UserID", "EmpName" FROM "UserMaster" ORDER BY "EmpName" DESC')
    emp_details = [{"id": row[0], "name": row[1]} for row in cursor.fetchall()]
    
    print(emp_details)
    
    # cursor.execute('SELECT "UserID", "EmpName" FROM "UserMaster" ORDER BY "EmpName"')
    # emp_details = [{"id": row[0], "name": row[1]} for row in cursor.fetchall()]

    today = datetime.today().strftime('%Y-%m-%d')
    
    
    return render_template("task_performed_report.html", emp_details=emp_details, today=today, user_category=session['user_category'])

@app.route("/get_tasks_performed_report")
def get_tasks_performed_report():
    empName = request.args.get('emp_name')
    date_from = request.args.get("from")
    date_to = request.args.get("to")
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Convert to date format and adjust 'to' date to include the entire day
        date_from_obj = datetime.strptime(date_from, "%Y-%m-%d")
        date_to_obj = datetime.strptime(date_to, "%Y-%m-%d") + timedelta(days=1)
    except Exception as e:
        return jsonify({"error": f"Invalid date format: {e}"}), 400
    
    
    print(empName)
    
    cursor.execute("""
        SELECT ph."ProjectHistoryID", ph."EventDate",pm."ProjectCode", pm."ProjectName",wm."WorkType", ph."Event", ph."Remarks"
        FROM "ProjectHistory" ph
        JOIN "UserMaster" um ON ph."UserID" = um."UserID"
        JOIN "ProjectMaster" pm ON ph."ProjectID" = pm."ProjectID"
        JOIN "WorkTypeMaster" wm ON ph."WorkTypeID" = wm."WorkTypeID"
        WHERE um."EmpName" = %s
        AND ph."EventDate" >= %s
        AND ph."EventDate" < %s
        ORDER BY ph."EventDate" DESC
    """, (empName,date_from_obj, date_to_obj))
    
    data = cursor.fetchall()
    
    print(data)

    records = [
        {
            "SrNo": i + 1,
            "ProjectHistoryID": row[0],
            "EventDate": row[1].strftime('%d %b %Y'),
            "ProjectDetails": row[2] + " : " + row[3],
            "WorkType": row[4],
            "Event": row[5],
            "Remarks": row[6]
        }
        for i, row in enumerate(data)
    ]

    return jsonify(records)

@app.route("/get_project_history_report")
def get_project_history_report():
    project_code = request.args.get("code")
    date_from = request.args.get("from")
    date_to = request.args.get("to")

    try:
        # Convert to date format and adjust 'to' date to include the entire day
        date_from_obj = datetime.strptime(date_from, "%Y-%m-%d")
        date_to_obj = datetime.strptime(date_to, "%Y-%m-%d") + timedelta(days=1)
    except Exception as e:
        return jsonify({"error": f"Invalid date format: {e}"}), 400

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT ph."ProjectHistoryID", ph."EventDate", um."EmpName", ph."Event", ph."Remarks", wm."WorkType"
        FROM "ProjectHistory" ph
        JOIN "UserMaster" um ON ph."UserID" = um."UserID"
        JOIN "ProjectMaster" pm ON ph."ProjectID" = pm."ProjectID"
        JOIN "WorkTypeMaster" wm ON ph."WorkTypeID" = wm."WorkTypeID"
        WHERE pm."ProjectCode" = %s
          AND ph."IsHistory" = true
          AND ph."EventDate" >= %s
          AND ph."EventDate" < %s
        ORDER BY ph."EventDate" DESC
    """, (project_code, date_from_obj, date_to_obj))

    data = cursor.fetchall()

    records = [
        {
            "SrNo": i + 1,
            "ProjectHistoryID": row[0],
            "EventDate": row[1].strftime('%d %b %Y'),
            "EmpName": row[2],
            "Event": row[3],
            "Remarks": row[4],
            "WorkType": row[5],
        }
        for i, row in enumerate(data)
    ]

    return jsonify(records)


@app.route("/pdf_report")
def project_hist_report_pdf():
    project_code = request.args.get("code")
    date_from = request.args.get("from")
    date_to = request.args.get("to")
    project_name = request.args.get("name", "project")
    try:
        # Convert to date format and adjust 'to' date to include the entire day
        date_from_obj = datetime.strptime(date_from, "%Y-%m-%d")
        date_to_obj = datetime.strptime(date_to, "%Y-%m-%d") + timedelta(days=1)
    except Exception as e:
        return jsonify({"error": f"Invalid date format: {e}"}), 400

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT ph."ProjectHistoryID", ph."EventDate", um."EmpName", ph."Event", ph."Remarks", wm."WorkType"
        FROM "ProjectHistory" ph
        JOIN "UserMaster" um ON ph."UserID" = um."UserID"
        JOIN "ProjectMaster" pm ON ph."ProjectID" = pm."ProjectID"
        JOIN "WorkTypeMaster" wm ON ph."WorkTypeID" = wm."WorkTypeID"
        WHERE pm."ProjectCode" = %s
          AND ph."IsHistory" = true
          AND ph."EventDate" >= %s
          AND ph."EventDate" < %s
        ORDER BY ph."EventDate" DESC
    """, (project_code, date_from_obj, date_to_obj))

    data = cursor.fetchall()

    records = [
        {
            "SrNo": i + 1,
            "ProjectHistoryID": row[0],
            "EventDate": row[1].strftime('%d %b %Y'),
            "EmpName": row[2],
            "Event": row[3],
            "Remarks": row[4],
            "WorkType": row[5],
        } for i, row in enumerate(data)]
    
    rendered = render_template("project_history_report_pdf.html",records=records)

    # Update this path to your local wkhtmltopdf
    # config = pdfkit.configuration(wkhtmltopdf=r"C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe")

    pdf = pdfkit.from_string(rendered, False, configuration=config, options={
        'page-size': 'A4',
        'orientation': 'Landscape',
        'margin-top': '10mm',
        'margin-bottom': '10mm',
        'margin-left': '10mm',
        'margin-right': '10mm'
    })

    filename = f"{project_code}_history_report.pdf"

    return send_file(BytesIO(pdf), as_attachment=True, download_name=filename, mimetype='application/pdf')

@app.route("/tasks_performed_pdf_report")
def tasks_performed_pdf_report():
    empName = request.args.get("emp_name")
    date_from = request.args.get("from")
    date_to = request.args.get("to")
    try:
        # Convert to date format and adjust 'to' date to include the entire day
        date_from_obj = datetime.strptime(date_from, "%Y-%m-%d")
        date_to_obj = datetime.strptime(date_to, "%Y-%m-%d") + timedelta(days=1)
    except Exception as e:
        return jsonify({"error": f"Invalid date format: {e}"}), 400

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT ph."ProjectHistoryID", ph."EventDate",pm."ProjectCode", pm."ProjectName",wm."WorkType", ph."Event", ph."Remarks", dm."DesignationName", um."UserCategory"
        FROM "ProjectHistory" ph
        JOIN "UserMaster" um ON ph."UserID" = um."UserID"
        JOIN "ProjectMaster" pm ON ph."ProjectID" = pm."ProjectID"
        JOIN "WorkTypeMaster" wm ON ph."WorkTypeID" = wm."WorkTypeID"
        JOIN "DesignationMaster" dm ON dm."DesignationID" = um."DesignationID"
        WHERE um."EmpName" = %s
        AND ph."EventDate" >= %s
        AND ph."EventDate" < %s
        ORDER BY ph."EventDate" DESC
    """, (empName,date_from_obj, date_to_obj))
    
    report_title = cursor.fetchone()
    
    emp_name = empName+" "+report_title[7]+" "+report_title[8]

    data = cursor.fetchall()

    records = [
        {
            "SrNo": i + 1,
            "ProjectHistoryID": row[0],
            "EventDate": row[1].strftime('%d %b %Y'),
            "ProjectDetails": row[2]+ " : "+ row[3],
            "Event": row[5],
            "Remarks": row[6],
            "WorkType": row[4],
        } for i, row in enumerate(data)]
    
    rendered = render_template("tasks_performed_report_pdf.html",records=records,empName=emp_name)

    # Update this path to your local wkhtmltopdf
    # config = pdfkit.configuration(wkhtmltopdf=r"C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe")

    pdf = pdfkit.from_string(rendered, False, configuration=config, options={
        'page-size': 'A4',
        'orientation': 'Landscape',
        'margin-top': '10mm',
        'margin-bottom': '10mm',
        'margin-left': '10mm',
        'margin-right': '10mm'
    })

    filename = f"{empName}_tasks_report.pdf"

    return send_file(BytesIO(pdf), as_attachment=True, download_name=filename, mimetype='application/pdf')


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5002, debug=True)