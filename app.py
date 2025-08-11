from flask import Flask, render_template, request, redirect, session, jsonify, send_file
from datetime import datetime, timedelta
import pdfkit
from io import BytesIO
import psycopg2
import psycopg2.extras
import platform
import os
import shutil
from utils import send_task_assignment_email


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
        database="MCPL-TMS",
        host="ep-icy-bread-a16ytb6h-pooler.ap-southeast-1.aws.neon.tech",
        port="5432",
        user="neondb_owner",
        password="npg_E91uRZnoHOFw"
    )

@app.route("/")
def dashboard():
    if "emp_name" in session:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        
        cursor.execute(""" SELECT "UserID" FROM "UserMaster" WHERE "EmpName" = %s """,(session['emp_name'],))
        user = cursor.fetchone()
        
        user_id = user[0]
        
        print(user_id)
        
        # cursor.execute(""" SELECT ta."TasksAssignedID" , ta."TaskDescription", um."EmpName", pm."ProjectCode", pm."ProjectName", ta."Remarks", ta."TargetDate", ta."Status" 
        #                FROM "TasksAssigned" ta
        #                JOIN "UserMaster" um ON ta."UserID_AssignedBy" = um."UserID"
        #                JOIN "ProjectMaster" pm ON ta."ProjectID" = pm."ProjectID"
        #                WHERE ta."UserID_AssignedTo" = %s ORDER BY ta."TasksAssignedID" ASC """,(assigned_to_id,))
        
        # # Column Names: "TasksAssignedID", "ProjectID", "UserID_AssignedBy", "UserID_AssignedTo", "TasksAssignedGUID", "DateOfEntry", "TargetDate", "TaskDescription", "Remarks", "Status"
        
        # tasks_assigned = [{"SrNo" : row[0], "task_description" : row[1] , "assigned_by" : row[2], "project_details" : row[3]+" : "+row[4], "remarks": row[5], "deadline": row[6], "status" : row[7]}for row in cursor.fetchall()]
        
        cursor.execute(""" SELECT ph."ProjectHistoryID" , ph."Event", um."EmpName", pm."ProjectCode", pm."ProjectName", ph."Remarks"
                       FROM "ProjectHistory" ph
                       JOIN "UserMaster" um ON ph."UserID" = um."UserID"
                       JOIN "ProjectMaster" pm ON ph."ProjectID" = pm."ProjectID"
                       WHERE ph."ChangeStatus?" = true AND ph."UserID" = %s ORDER BY ph."ProjectHistoryID" ASC """,(user_id,))
        
        assigned_tasks = [{"SrNo" : row["ProjectHistoryID"], "task_description" : row["Event"] , "assigned_to" : row["EmpName"], "project_details" : row["ProjectCode"]+" : "+row["ProjectName"], "remarks": row["Remarks"]}for row in cursor.fetchall()]
        
        
        print(assigned_tasks)
        
        cursor.execute(""" SELECT ph."ProjectHistoryID" , ph."Event", um."EmpName", pm."ProjectCode", pm."ProjectName", ph."Remarks", ph."TaskStatus"
                       FROM "ProjectHistory" ph
                       JOIN "UserMaster" um ON ph."UserID" = um."UserID"
                       JOIN "ProjectMaster" pm ON ph."ProjectID" = pm."ProjectID"
                       WHERE ph."ChangeStatus?" = true AND ph."AssignedBy" = %s ORDER BY ph."ProjectHistoryID" ASC """,(user_id,))
        
        tasks_under_review = [{"SrNo" : row["ProjectHistoryID"], "task_description" : row["Event"] , "assigned_to" : row["EmpName"], "project_details" : row["ProjectCode"]+" : "+row["ProjectName"], "remarks": row["Remarks"], "status": row["TaskStatus"]}for row in cursor.fetchall()]
        
        return render_template("dashboard.html",complied_review_tasks=assigned_tasks,tasks_under_review=tasks_under_review)
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

# @app.route('/update_task_status')
# def update_task_status():
    


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
    
    cursor.execute('SELECT "UserID", "EmpName" FROM "UserMaster" ORDER BY "EmpName" ASC;')
    empNames = [{"id": row[0], "name" : row[1]}for row in cursor.fetchall()]

    today = datetime.today().strftime('%Y-%m-%d')

    if request.method == "POST":
        workTypenull = False
        projectCodenull = False
        project_code = request.form['project_code']
        emp_name = session['emp_name']
        workType = request.form['work_type']
        entry_date = request.form['entry_date']
        event_date = request.form['event_date']
        event_desc = request.form['event_desc']
        tasks_assigned_by = request.form['task_assigned_by']
        remarks = request.form['remarks']
        isHistory = request.form.get("isHistory","false").lower() == "true"
        history_id = request.form.get("project_history_id")


        cursor.execute('SELECT "ProjectID" FROM "ProjectMaster" WHERE "ProjectCode" = %s', (project_code,))
        project_row = cursor.fetchone()
        project_id = project_row[0] if project_row else None

        cursor.execute('SELECT "UserID" FROM "UserMaster" WHERE "EmpName" = %s', (emp_name,))
        user_row = cursor.fetchone()
        user_id = user_row[0] if user_row else None
        
        if workType == 'Select Work Type' or '':
            workTypenull = True
        
        if project_code == 'Select Project Code' or '':
            projectCodenull = True
            
        if workTypenull == True and projectCodenull == True:
            return render_template('project_history.html',projects=projects,work_type=work_type, today=today,errormessage="Please fill all Project Code and Work Type", empNames=empNames)
        
        if workTypenull == True:
            return render_template('project_history.html',projects=projects,work_type=work_type, today=today,errormessage="Please fill Work Type", empNames=empNames)
        
        if projectCodenull == True:
            return render_template('project_history.html',projects=projects,work_type=work_type, today=today,errormessage="Please fill Project Code", empNames=empNames)
        
        

        if project_id and user_id:
            if history_id:
                cursor.execute('''
                    UPDATE "ProjectHistory"
                    SET "EventDate" = %s,
                        "Event" = %s,
                        "Remarks" = %s,
                        "IsHistory" = %s,
                        "WorkTypeID" = %s
                    WHERE "ProjectHistoryID" = %s AND "ChangeStatus?" = false
                ''', (event_date, event_desc, remarks, isHistory, workType, history_id))
                conn.commit()
                message = "Record Updated Successfully"
            else:
                cursor.execute('''
                    INSERT INTO "ProjectHistory" (
                    "ProjectID", "UserID", "ProjectHistoryGUID", 
                    "DateOfEntry", "EventDate", "Event", "Remarks", 
                    "IsHistory", "WorkTypeID", "AssignedBy","ChangeStatus?"
                )
                VALUES (%s, %s, gen_random_uuid(), %s, %s, %s, %s, %s, %s,%s,False)
            ''', (project_id, user_id, entry_date, event_date, event_desc, remarks, isHistory, workType,tasks_assigned_by))
                conn.commit()
                message = "Record Saved Successfully"

        return render_template("project_history.html", 
                               message=message, 
                               projects=projects, 
                               today=today,work_type=work_type,empNames=empNames)

    return render_template("project_history.html", projects=projects, today=today, work_type=work_type, empNames=empNames)

@app.route("/update_task_under_review",methods=["GET","POST"])
def update_task_under_review():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    if request.method == "POST":
        data = request.get_json()
        print(data)
        
        taskDesc = data['task_desc']
        remarks = data['remarks']
        status = data['task_status']
        taskId = data['task_id']
        
        cursor.execute(''' SELECT "Event" FROM "ProjectHistory" WHERE "ProjectHistoryID" = %s ''',(taskId,))
        old_task_data = cursor.fetchone()
        taskDesc_old = old_task_data[0]
        
        updated_task_desc = taskDesc_old+', (Edited): '+taskDesc
        
        if status == 'Cleared':
            cursor.execute(''' UPDATE "ProjectHistory" SET 
                       "Event" = %s, "Remarks" = %s, "TaskStatus" = %s, "ChangeStatus?" = False WHERE "ProjectHistoryID" = %s''',(updated_task_desc, remarks, status,taskId))
            conn.commit()
            
            return jsonify({
                "message": 'Task Updated Successfully',
                "status": '200'
            }), 200
        
        else:
            cursor.execute(''' UPDATE "ProjectHistory" SET 
                       "Event" = %s, "Remarks" = %s, "TaskStatus" = %s WHERE "ProjectHistoryID" = %s''',(updated_task_desc, remarks, status,taskId))
            conn.commit()
            
            return jsonify({
                "message": 'Task Updated Successfully',
                "status": '200'
            }), 200
        
    

@app.route('/update_assigned_tasks',methods=["GET","POST"])
def update_assigned_tasks():
    if request.method == "POST":
        
        if request.is_json:
            data = request.get_json()
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        print(data['task_id'])
        
        # cursor.execute(''' SELECT "ProjectID" FROM "ProjectHistory" WHERE "ProjectHistoryID" = %s ''',(data['task_id'],))
        
        # project = cursor.fetchone()
        
        # project_id = project[0]
        
        # cursor.execute(''' SELECT "UserID" FROM "UserMaster" WHERE "EmpName" = %s ''',(session['emp_name'],))
        
        # user = cursor.fetchone()
        # user_id = user[0]
        
        cursor.execute(''' SELECT "Event", "Remarks" FROM "ProjectHistory" WHERE "ProjectHistoryID" = %s ''',(data['task_id'],))
        task = cursor.fetchone()
        
        task_desc = task[0]
        remarks = task[1]

        task_desc = task_desc + '(Edited) : '+data['task_desc']
        remarks = remarks + '(Edited) : '+data['remarks']
        
        # cursor.execute('''
        #             INSERT INTO "ProjectHistory" (
        #             "ProjectID", "UserID", "ProjectHistoryGUID", 
        #             "DateOfEntry", "EventDate", "Event", "Remarks", 
        #             "IsHistory", "WorkTypeID"
        #         )
        #         VALUES (%s, %s, gen_random_uuid(), %s, %s, %s, %s, %s, %s)
        #     ''', (project_id, user_id, entry_date, event_date, event_desc, remarks, isHistory, workType))
        
        # cursor.execute('''
        #     INSERT INTO "ProjectHistory"(
        #     "ProjectID","UserID","DateOfEntry","EventDate","Event","Remarks","IsHistory","WorkTypeID","TasksAssignedID","ChangeStatus?"
        #     ) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        # ''',(project_id, user_id, datetime.today(), datetime.today(), task_desc, remarks, False, 1, data['task_id'], True))
        # conn.commit()
        
        cursor.execute(''' UPDATE "ProjectHistory" SET 
                       "Event" = %s, "Remarks" = %s WHERE "ProjectHistoryID" = %s''',(task_desc, remarks, data['task_id']))
        conn.commit()
    
        return jsonify({
            "message": 'Task Updated Successfully',
            "status": '200'
        }), 200



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

@app.route("/tasks_assigned", methods=["GET","POST"])
def tasks_assigned():
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute(' SELECT "ProjectID", "ProjectCode", "ProjectName" FROM "ProjectMaster" ORDER BY "ProjectCode" ASC ')
    projects = [{"id": row[0], "code": row[1], "name": row[2]}for row in cursor.fetchall()] # Get Project Details
    
    cursor.execute(' SELECT "UserID", "EmpName" FROM "UserMaster" ORDER BY "EmpName" ASC ')
    empNames = [{"id" : row[0], "name" : row[1]}for row in cursor.fetchall()] # Get User Details
    
    cursor.execute(' SELECT "WorkTypeID", "WorkType" FROM "WorkTypeMaster" ORDER BY "WorkType" ASC ')
    work_type = [{"id" : row[0], "type" : row[1]}for row in cursor.fetchall()]
    
    today = datetime.today().strftime('%Y-%m-%d')
    
    if request.method == "POST":
        data = request.form
        
        print(data)
        
        cursor.execute(' SELECT "ProjectID" FROM "ProjectMaster" WHERE "ProjectCode" = %s ',(data["project_code"],))
        project_id = cursor.fetchone()
        
        cursor.execute(' SELECT "UserID" FROM "UserMaster" WHERE "EmpName"= %s ',(data["assigned_by"],))
        user_assigned_by = cursor.fetchone()
        
        cursor.execute(' SELECT "UserEmail","EmpName" FROM "UserMaster" WHERE "UserID" = %s ',(data['assign_to'],))
        assign_to_email = cursor.fetchone()
        
        task_desc = "Task Assigned: "+ data['task_desc'] + ". Deadline: "+data['target_date']+". Current Status: Pending"
        
        print(project_id)
        
        if data and project_id and user_assigned_by:
            # cursor.execute('''
            #         INSERT INTO public."TasksAssigned"(
	        #         "ProjectID", "UserID_AssignedBy", "UserID_AssignedTo", "DateOfEntry", "TargetDate", "TaskDescription", "Remarks", "Status")
	        #         VALUES (%s, %s, %s, %s, %s, %s, %s, %s);
            # ''', (project_id[0], user_assigned_by[0], data['assign_to'], data['entry_date'], data['target_date'], data['task_desc'], data['remarks'], 'Pending'))
            # conn.commit()
            cursor.execute('''
                    INSERT INTO "ProjectHistory"(
	                "ProjectID", "AssignedBy", "UserID", "DateOfEntry","Event", "Remarks","ChangeStatus?", "EventDate", "WorkTypeID","TaskStatus")
	                VALUES (%s, %s, %s, %s, %s, %s,True,%s,%s,'Pending');
            ''', (project_id[0], user_assigned_by[0], data['assign_to'], data['entry_date'], task_desc, data['remarks'],data['entry_date'],data["work_type"]))
            conn.commit()
            send_task_assignment_email(assign_to_email[0],data['assigned_by'],data["project_code"], data["task_desc"],session['designation'],data['target_date'],data['project_name'],assign_to_email[1])
            
            return render_template("tasks_assigned.html",projects=projects, today=today, empNames=empNames, message="Task Assigned Successfully",work_type=work_type)
            
            

    return render_template("tasks_assigned.html",projects=projects,empNames=empNames,today=today,work_type=work_type)


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