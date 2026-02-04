from flask import Flask, render_template, request, redirect, session, jsonify, send_file
from datetime import datetime, timedelta, date
from dateutil.relativedelta import relativedelta
from flask_mail import Mail, Message
import pdfkit
from io import BytesIO
import psycopg2
import psycopg2.extras
import platform
import os
import shutil
from utils import send_task_assignment_email
import json
import uuid


app = Flask(__name__)
app.secret_key = 'your_secret_key'

if platform.system() == "Windows":
    print("Windows")
    config = pdfkit.configuration(wkhtmltopdf=r".\wkhtmltopdf\bin\wkhtmltopdf.exe")
else:
    print("Not Windows")
    config = pdfkit.configuration(wkhtmltopdf="/usr/bin/wkhtmltopdf")
    # wkhtmltopdf_path = os.path.join(os.path.dirname(__file__), 'bin', 'wkhtmltopdf')
    # if not os.path.exists(wkhtmltopdf_path):
    #     raise FileNotFoundError(f"wkhtmltopdf not found at {wkhtmltopdf_path}")
    # config = pdfkit.configuration(wkhtmltopdf=wkhtmltopdf_path)



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
        cursor = conn.cursor()
        
        cursor.execute(""" SELECT "UserID" FROM "UserMaster" WHERE "EmpName" = %s """,(session['emp_name'],))
        user = cursor.fetchone()
        
        cursor.execute(''' SELECT "DesignationCode", "DesignationID", "DesignationName" FROM "DesignationMaster" ''')
        designations = [{ "desig_id" : row[1], "desig_code" : row[0], "desig_name" : row[2] }for row in cursor.fetchall()]
        
        cursor.execute(""" SELECT "ProjectID","ProjectCode", "ProjectName", "ArchAssigned", "EngrAssigned" FROM "ProjectMaster" ORDER BY "ProjectCode" ASC """)
        projects = [{"id" : row[0], "proj_details" : row[1] + " : " + row[2], "archAssigned" : row[3], "engrAssigned" : row[4]}for row in cursor.fetchall()]
        
        cursor.execute(""" SELECT "UserID", "EmpName" FROM "UserMaster" WHERE "IsActive" = TRUE ORDER BY "EmpName" ASC """)
        users = [{"id" : row[0], "name" : row[1]}for row in cursor.fetchall()]
        
        cursor.execute(''' SELECT "BranchID", "BranchName", "BranchCode" FROM "BranchMaster" WHERE "OrganisationID" = %s ''',(session['organisation_id'],))
        branches = [{"branch_id" : row[0], "branch_code" : row[2], "branch_name" : row[1]}for row in cursor.fetchall()]
        
        user_id = user[0]
        
        print(user_id)
        
        # cursor.execute(""" SELECT ta."TasksAssignedID" , ta."TaskDescription", um."EmpName", pm."ProjectCode", pm."ProjectName", ta."Remarks", ta."TargetDate", ta."Status" 
        #                FROM "TasksAssigned" ta
        #                JOIN "UserMaster" um ON ta."UserID_AssignedBy" = um."UserID"
        #                JOIN "ProjectMaster" pm ON ta."ProjectID" = pm."ProjectID"
        #                WHERE ta."UserID_AssignedTo" = %s ORDER BY ta."TasksAssignedID" ASC """,(assigned_to_id,))
        
        # # Column Names: "TasksAssignedID", "ProjectID", "UserID_AssignedBy", "UserID_AssignedTo", "TasksAssignedGUID", "DateOfEntry", "TargetDate", "TaskDescription", "Remarks", "Status"
        
        # tasks_assigned = [{"SrNo" : row[0], "task_description" : row[1] , "assigned_by" : row[2], "project_details" : row[3]+" : "+row[4], "remarks": row[5], "deadline": row[6], "status" : row[7]}for row in cursor.fetchall()]
        
        cursor.execute(""" SELECT ph."ProjectHistoryID" , ph."Event", um."EmpName", pm."ProjectCode", pm."ProjectName", ph."Remarks", ph."TargetDate", ph."DateOfEntry", ph."TaskStatus"
                       FROM "ProjectHistory" ph
                       JOIN "UserMaster" um ON ph."AssignedBy" = um."UserID"
                       JOIN "ProjectMaster" pm ON ph."ProjectID" = pm."ProjectID"
                       WHERE ph."ChangeStatus?" = true AND ph."UserID" = %s ORDER BY ph."ProjectHistoryID" ASC """,(user_id,))
        
        assigned_tasks = [{"SrNo" : row[0], "task_description" : row[1] , "assigned_to" : row[2], "project_details" : row[3]+" : "+row[4], "remarks": row[5],"target_date":row[6], "date_of_entry" : row[7], "status": row[8]}for row in cursor.fetchall()]
        
        print("Tasks Assigned to: ",assigned_tasks)
        
        cursor.execute(""" SELECT ph."ProjectHistoryID" , ph."Event", um."EmpName", pm."ProjectCode", pm."ProjectName", ph."Remarks", ph."TaskStatus", ph."TargetDate", ph."DateOfEntry"
                       FROM "ProjectHistory" ph
                       JOIN "UserMaster" um ON ph."UserID" = um."UserID"
                       JOIN "ProjectMaster" pm ON ph."ProjectID" = pm."ProjectID"
                       WHERE ph."ChangeStatus?" = true AND ph."AssignedBy" = %s ORDER BY ph."ProjectHistoryID" ASC """,(user_id,))
        
        tasks_under_review = [{"SrNo" : row[0], "task_description" : row[1] , "assigned_to" : row[2], "project_details" : row[3]+" : "+row[4], "remarks": row[5], "status": row[6],"target_date":row[7], "date_of_entry" : row[8]}for row in cursor.fetchall()]
        print("Tasks Under Review",tasks_under_review)
        
        cursor.execute("""
                       SELECT "EmpName", "DateOfJoining", "DateOfBirth", "UserEmail" FROM "UserMaster"
                       WHERE "IsActive" = true ORDER BY "DateOfJoining" ASC;
                       """)
        
        today = date.today()
        
        employee_list = [{"SrNo" : i+1,"name": row[0], "doj": row[1].strftime("%d %b %Y"), "dob": row[2].strftime("%d %b %Y"), "age": f"{relativedelta(today, row[2]).years} Yrs {relativedelta(today, row[2]).months} Months and {relativedelta(today, row[2]).days} Days", "email": row[3]} for i,row in enumerate(cursor.fetchall())]
        
        
        
        return render_template("dashboard.html",assigned_tasks=assigned_tasks,tasks_under_review=tasks_under_review,designations=designations,branches=branches,projects=projects, users=users, employee_list=employee_list)
    else:
        return render_template("login.html", message="Your session has been timed out. Please Log in again.")
    

@app.route("/get_project_history_by_code")
def get_project_history_by_code():
    # project_code = request.args.get("code")
    print("Project History Code Called..//")
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT ph."ProjectHistoryID", ph."EventDate", um."EmpName", ph."Event", ph."Remarks", wm."WorkType", ph."IsHistory", ph."TimeSpent", pm."ProjectCode"
    FROM "ProjectHistory" ph
    JOIN "UserMaster" um ON ph."UserID" = um."UserID"
    JOIN "ProjectMaster" pm ON ph."ProjectID" = pm."ProjectID"
    JOIN "WorkTypeMaster" wm ON ph."WorkTypeID" = wm."WorkTypeID"
    WHERE um."EmpName" = %s
    ORDER BY ph."EventDate" DESC
    """, (session['emp_name'],))
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
            "IsHistory": row[6],
            "TimeSpent" : row[7],
            "ProjectCode" : row[8]
        }
        for i, row in enumerate(data)
    ]
    
    return jsonify(records)

# @app.route('/update_task_status')
# def update_task_status():


@app.route("/update_project_assignment", methods=["POST"])
def update_project_assignment():
    data = request.get_json()
    project_id = data.get("project_id")
    arch_assigned = data.get("arch_assigned") or None
    engr_assigned = data.get("engr_assigned") or None

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE "ProjectMaster"
        SET "ArchAssigned" = %s, "EngrAssigned" = %s
        WHERE "ProjectID" = %s
    """, (arch_assigned, engr_assigned, project_id))

    conn.commit()
    cursor.close()
    conn.close()

    return jsonify({"success": True})



@app.route("/get_project_history_by_id/<int:history_id>")
def get_project_history_by_id(history_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT ph."ProjectHistoryID", ph."EventDate", ph."Event", ph."Remarks", ph."WorkTypeID", ph."IsHistory", pm."ProjectCode", um."UserID", ph."TimeSpent"
        FROM "ProjectHistory" ph
        JOIN "ProjectMaster" pm
        ON pm."ProjectID" = ph."ProjectID"
        JOIN "UserMaster" um
        ON um."UserID" = ph."AssignedBy"
        WHERE "ProjectHistoryID" = %s
    ''', (history_id,))
    row = cursor.fetchone()
    if row:
        print(row[5])
        return jsonify({
            "ProjectHistoryID": row[0],
            "EventDate": row[1].strftime("%Y-%m-%d"),
            "Event": row[2],
            "Remarks": row[3],
            "WorkTypeID": row[4],
            "IsHistory": row[5],
            "ProjectCode": row[6],
            "AssignerName" : row[7],
            "TimeSpent" : row[8]# Send this too
        })
    return jsonify({})


    
# Also used for task performed
@app.route("/project_hist", methods=["GET", "POST"])
def project_history():
    conn = get_db_connection()
    cursor = conn.cursor()
    errormessage = ''
    
    # Fetch dropdown data
    cursor.execute('SELECT "ProjectCode", "ProjectName" FROM "ProjectMaster" ORDER BY "ProjectCode"')
    projects = [{"code": row[0], "name": row[1]} for row in cursor.fetchall()]
    
    cursor.execute('SELECT "WorkTypeID", "WorkType" FROM "WorkTypeMaster" ORDER BY "WorkType"')
    work_type = [{"id": row[0], "work_type": row[1]} for row in cursor.fetchall()]
    
    cursor.execute('SELECT "UserID", "EmpName" FROM "UserMaster" ORDER BY "EmpName" ASC;')
    empNames = [{"id": row[0], "name": row[1]} for row in cursor.fetchall()]

    today = datetime.today().strftime('%Y-%m-%d')

    if request.method == "POST":
        # Retrieve form data
        project_code = request.form.get('project_code', '').strip()
        emp_name = session.get('emp_name')
        workType = request.form.get('work_type', '').strip()
        rework = request.form.get('IsRework')
        entry_date = request.form.get('entry_date', '').strip()
        event_date = request.form.get('event_date', '').strip()
        event_desc = request.form.get('event_desc', '').strip()
        tasks_assigned_by = request.form.get('task_assigned_by', '').strip()
        remarks = request.form.get('remarks', '').strip()
        isHistory = request.form.get("isHistory")
        history_id = request.form.get("project_history_id", '').strip()
        time_spent_raw = request.form.get('time_spent', '').strip()
        
        print("Project History Updation / Insertion API: ",isHistory)

        # Validate time_spent and convert to float or None
        try:
            time_spent = float(time_spent_raw) if time_spent_raw else None
        except ValueError:
            time_spent = None

        # Validate dropdown selections
        workTypenull = (workType == 'Select Work Type' or workType == '')
        projectCodenull = (project_code == 'Select Project Code' or project_code == '')
        timeSpentNull = (time_spent == 0.0 or time_spent == None)
        projectCodeNull = (project_code == 'Select Project Code' or project_code == '')
        eventDescNull = (event_desc == '')
        assignerNull = (tasks_assigned_by == 'Select Assigner Name' or tasks_assigned_by == '')
        isHistoryNull = (isHistory == '' or isHistory == None)
        isReworkNull = (rework == '' or rework == None)
        

        missing_fields = []

        if workTypenull:
            missing_fields.append("work_type")
        if projectCodenull:
            missing_fields.append("project_code")
        if timeSpentNull:
            missing_fields.append("time_spent")
        if eventDescNull:
            missing_fields.append("event_desc")
        if assignerNull:
            missing_fields.append("task_assigned_by")
        if isHistoryNull or isReworkNull:
            pass  # radios not bordered

        if missing_fields:
            if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                return jsonify({
                    "status": "error",
                    "message": "Please Fill All Details with *",
                    "missing_fields": missing_fields
                }), 400


        # Get ProjectID and UserID from database
        cursor.execute('SELECT "ProjectID" FROM "ProjectMaster" WHERE "ProjectCode" = %s', (project_code,))
        project_row = cursor.fetchone()
        project_id = project_row[0] if project_row else None

        cursor.execute('SELECT "UserID" FROM "UserMaster" WHERE "EmpName" = %s', (emp_name,))
        user_row = cursor.fetchone()
        user_id = user_row[0] if user_row else None

        if project_id and user_id:
            if history_id:
                print("Project History Id: ",history_id)
                # Update existing record
                cursor.execute('''
                    UPDATE "ProjectHistory"
                    SET "EventDate" = %s,
                        "Event" = %s,
                        "Remarks" = %s,
                        "IsHistory" = %s,
                        "WorkTypeID" = %s,
                        "TimeSpent" = %s,
                        "AssignedBy" = %s,
                        "IsRework" = %s
                    WHERE "ProjectHistoryID" = %s
                ''', (event_date, event_desc, remarks, isHistory, workType, time_spent, tasks_assigned_by, rework, history_id))
                conn.commit()
                message = "Record Updated Successfully"
            else:
                # Insert new record
                cursor.execute('''
                    INSERT INTO "ProjectHistory" (
                        "ProjectID", "UserID", "ProjectHistoryGUID", 
                        "DateOfEntry", "EventDate", "Event", "Remarks", 
                        "IsHistory", "WorkTypeID", "AssignedBy", "ChangeStatus?", "TimeSpent", "IsRework"
                    )
                    VALUES (%s, %s, gen_random_uuid(), %s, %s, %s, %s, %s, %s, %s, False, %s, %s)
                ''', (project_id, user_id, entry_date, event_date, event_desc, remarks, isHistory, workType, tasks_assigned_by, time_spent,rework))
                conn.commit()
                message = "Record Saved Successfully"

            return jsonify({
                "status": "success",
                "message": message
            })


        else:
            err_msg = "Invalid Project or User"
            return render_template('project_history.html', projects=projects, work_type=work_type, today=today, errormessage=err_msg, empNames=empNames)

    # GET request rendering
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

        task_desc = task_desc + '| ('+session['username']+' Updated On '+str(date.today())+ ') : '+data['task_desc']
        if data['remarks'] or data['remarks'] != "":
            remarks = remarks + '| ('+session['username']+' Updated On '+str(date.today())+ ') : '+data['remarks']
        # remarks = remarks + '(Edited) : '+data['remarks']
        
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


@app.route("/change_password",methods=["GET","POST"])
def change_password():
    if request.method == "POST":
        data = request.get_json()
        new_pass = data['newPassword']
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute(""" UPDATE "UserMaster" SET "UserPWD" = %s WHERE "EmpName" = %s """,(new_pass,session['emp_name']))
        conn.commit()
        
        return jsonify({
            "message": 'Passwords Changed Successfully'
        }) , 200


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

@app.route("/mark_employee_inactive", methods=["POST"])
def mark_employee_inactive():
    data = request.json
    print("Inactive Data: ",data)
    
    employees = data.get('employees',[])
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    for name in employees:
        cursor.execute(""" UPDATE "UserMaster" SET "IsActive" = false WHERE "EmpName" = %s """,[name,])
        
    conn.commit()
    
    return jsonify({"message": "Setting Inactive Success", "statusCode" : 200})

@app.route("/tasks_assigned", methods=["GET","POST"])
def tasks_assigned():
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute(' SELECT "ProjectID", "ProjectCode", "ProjectName" FROM "ProjectMaster" ORDER BY "ProjectCode" ASC ')
    projects = [{"id": row[0], "code": row[1], "name": row[2]}for row in cursor.fetchall()] # Get Project Details
    
    cursor.execute(' SELECT "UserID", "EmpName" FROM "UserMaster" WHERE "IsActive" = TRUE ORDER BY "EmpName" ASC ')
    empNames = [{"id" : row[0], "name" : row[1]}for row in cursor.fetchall()] # Get User Details
    
    cursor.execute(' SELECT "WorkTypeID", "WorkType" FROM "WorkTypeMaster" ORDER BY "WorkType" ASC ')
    work_type = [{"id" : row[0], "type" : row[1]}for row in cursor.fetchall()]
    
    today = datetime.today().strftime('%Y-%m-%d')
    
    if request.method == "POST":
        data = request.form
        
        print(data)
        
        workType = data.get('work_type')
        project_code = data.get('project_code')
        assign_to = data.get('assign_to')
        projectName = data.get('project_name')
        task_desc = data.get('task_desc')
        
        
        workTypenull = (workType == 'Select Work Type' or workType == '')
        projectCodenull = (project_code == 'Select Project Code' or project_code == '')
        eventDescNull = (task_desc == '')
        projectNameNull = (projectName == '')
        assignToNull = (assign_to == '' or assign_to == 'Select Assigning to Employee')
        
        
        if workTypenull or projectCodenull or assignToNull or projectNameNull or eventDescNull or assignToNull:
            errormessage = "Please Fill All Details with *"
            return jsonify({"status":"error","message": errormessage}),400
            # return render_template('tasks_assigned.html', projects=projects, work_type=work_type, today=today, errormessage=errormessage, empNames=empNames)
        
        cursor.execute(' SELECT "ProjectID" FROM "ProjectMaster" WHERE "ProjectCode" = %s ',(data["project_code"],))
        project_id = cursor.fetchone()
        
        cursor.execute(' SELECT "UserID" FROM "UserMaster" WHERE "EmpName"= %s ',(data["assigned_by"],))
        user_assigned_by = cursor.fetchone()
        
        # cursor.execute(' SELECT "UserEmail","EmpName" FROM "UserMaster" WHERE "UserID" = %s ',(data['assign_to'],))
        # assign_to_email = cursor.fetchone()
        
        task_desc = "Task Assigned: "+ data['task_desc'] + ". | "+"\n"+"Deadline: "+data['target_date']+". | "+"\n"+"Current Status: Pending"
        
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
	                "ProjectID", "AssignedBy", "UserID", "DateOfEntry","Event", "Remarks","ChangeStatus?", "EventDate", "WorkTypeID","TaskStatus","TargetDate")
	                VALUES (%s, %s, %s, %s, %s, %s,True,%s,%s,'Pending',%s);
            ''', (project_id[0], user_assigned_by[0], data['assign_to'], data['entry_date'], task_desc, data['remarks'],data['entry_date'],data["work_type"],data['target_date']))
            conn.commit()
            
            # cursor.execute(""" SELECT "EmpName","UserEmail" FROM "UserMaster" WHERE "UserID" = %s """,[data['assign_to'],])
            
            # assign_to_email = cursor.fetchone()
            
            # app.config['MAIL_SERVER'] = 'smtp.zoho.in' # Or smtp.zoho.eu if based in Europe
            # app.config['MAIL_PORT'] = 465 # Use 465 with SSL or 587 with TLS
            # app.config['MAIL_USE_SSL'] = True
            # app.config['MAIL_USE_TLS'] = False # Set to True if using port 587
            # app.config['MAIL_USERNAME'] = 'mcpl-task-system@zohomail.in'
            # app.config['MAIL_PASSWORD'] = 'ui0W88e7LAeR' # App Password
            # app.config['MAIL_DEFAULT_SENDER'] = 'mcpl-task-system@zohomail.in'
            
            # send_task_assignment_email(Mail(app),assign_to_email[0],data['assigned_by'],data["project_code"], data["task_desc"],session['designation'],data['target_date'],data['project_name'],assign_to_email[1])
            
            return jsonify({
                "status": "success",
                "message": "Task Assigned Successfully"
            })

            # return render_template("tasks_assigned.html",projects=projects, today=today, empNames=empNames, message="Task Assigned Successfully",work_type=work_type)
            
            

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
    
    cursor.execute('SELECT "UserID", "EmpName" FROM "UserMaster" ORDER BY "EmpName" ASC')
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
        SELECT ph."ProjectHistoryID", ph."EventDate",pm."ProjectCode", pm."ProjectName",wm."WorkType", ph."Event", ph."Remarks",ph."TimeSpent"
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
            "Remarks": row[6],
            "TimeSpent": row[7]
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
        SELECT ph."ProjectHistoryID", ph."EventDate", um."EmpName", ph."Event", ph."Remarks", wm."WorkType", ph."IsRework"
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
            "IsRework" : row[6]
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
    
    cursor.execute(""" SELECT "ProjectName" FROM "ProjectMaster" WHERE "ProjectCode" = %s """,(project_code,))
    project_name = cursor.fetchone()
    
    proj_name = project_name[0]
    
    project_details = project_code + " : " + proj_name

    cursor.execute("""
        SELECT ph."ProjectHistoryID", ph."EventDate", um."EmpName", ph."Event", ph."Remarks", wm."WorkType", pm."ProjectCode", pm."ProjectName", ph."TimeSpent", ph."IsRework"
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
            "TimeSpent": row[8],
            "IsRework": row[9]
        } for i, row in enumerate(data)]
    
    cursor.execute("""
                    SELECT DISTINCT um."EmpName", CAST(SUM(ph."TimeSpent") AS NUMERIC(10,2)) FROM "ProjectHistory" ph
                    JOIN "UserMaster" um ON ph."UserID" = um."UserID"
                    JOIN "ProjectMaster" pm ON ph."ProjectID" = pm."ProjectID"
                    WHERE pm."ProjectCode" = %s AND ph."EventDate" >= %s
                    AND ph."EventDate" < %s GROUP BY um."EmpName" ORDER BY CAST(SUM(ph."TimeSpent") AS NUMERIC(10,2)) DESC;
                    """,[project_code,date_from_obj,date_to_obj])
    
    project_abstract_details = [{"SrNo" : i, "name": row[0], "time_spent": row[1]}for i,row in enumerate(cursor.fetchall(), start=1)]
    
    total_time_spent = 0
    for proj in project_abstract_details:
        total_time_spent += float(proj["time_spent"])
    
    rendered = render_template("project_history_report_pdf.html",records=records,project_details=project_details,project_abstract_details=project_abstract_details,total_time_spent=total_time_spent)

    # Update this path to your local wkhtmltopdf
    # config = pdfkit.configuration(wkhtmltopdf=r"C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe")

    pdf = pdfkit.from_string(rendered, False, configuration=config, options={
        'page-size': 'A4',
        'orientation': 'Landscape',
        'margin-top': '10mm',
        'margin-bottom': '10mm',
        'margin-left': '10mm',
        'margin-right': '10mm',
        'footer-center': 'Page [page] of [toPage]',
        'footer-right' : '© Mitimitra Consultants Pvt. Ltd., Pune',
        'footer-font-size': '9',
        'footer-spacing': '3',
        'footer-line': '',  # draws a line above footer
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
        SELECT ph."ProjectHistoryID", ph."EventDate",pm."ProjectCode", pm."ProjectName",wm."WorkType", ph."Event", ph."Remarks", dm."DesignationName", um."UserCategory", ph."TimeSpent"
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

    data = cursor.fetchall()

    report_title = data[0]

    emp_name = f"{empName} {report_title[7]} {report_title[8]}"

    records = [
        {
            "SrNo": i + 1,
            "ProjectHistoryID": row[0],
            "EventDate": row[1].strftime('%d %b %Y'),
            "ProjectDetails": row[2]+ " : "+ row[3],
            "Event": row[5],
            "Remarks": row[6],
            "WorkType": row[4],
            "TimeSpent" : row[9]
        } for i, row in enumerate(data)]
    
    date_from_title = date_from_obj.strftime("%d-%m-%Y")
    date_to_title = date_to_obj.strftime("%d-%m-%Y")
    
    cursor.execute("""
                    SELECT DISTINCT pm."ProjectCode", pm."ProjectName", CAST(SUM(ph."TimeSpent") AS NUMERIC(10,2)) FROM "ProjectHistory" ph
                    JOIN "UserMaster" um ON ph."UserID" = um."UserID"
                    JOIN "ProjectMaster" pm ON ph."ProjectID" = pm."ProjectID"
                    WHERE um."EmpName" = %s AND ph."EventDate" >= %s
                    AND ph."EventDate" < %s GROUP BY pm."ProjectCode", pm."ProjectName" ORDER BY CAST(SUM(ph."TimeSpent") AS NUMERIC(10,2)) DESC;
                   """,[empName, date_from_obj, date_to_obj])
    
    emp_abstract = [{"srno" : i, "project_code": row[0], "project_name": row[1], "time_spent": row[2]}for i,row in enumerate(cursor.fetchall(),start=1)]
    
    total_time_spent = 0
    for emp in emp_abstract:
        if emp["time_spent"] == None:
            emp["time_spent"] = 1.0
        else:
            total_time_spent += float(emp["time_spent"])
    
    rendered = render_template("tasks_performed_report_pdf.html",records=records,empName=emp_name,date_from=date_from_title,date_to=date_to_title,emp_abstract=emp_abstract,total_time_spent=total_time_spent)

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

@app.route("/add_project", methods=["GET","POST"])
def add_project():
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    if request.method == "POST":
        data = request.get_json()
        project_code = data.get("project_code")
        project_name = data.get("project_name")
        client_name = data.get("clientName")
        client_addr = data.get("clientAddr")
        client_contact = data.get("clientContactInfo")
        remarks = data.get("remarks")
        
        print(data)
        
        cursor.execute(''' INSERT INTO "ProjectMaster" 
                       ("ProjectCode","ProjectName","ClientName","ClientAddress","ClientContactInfo","Remarks","OrganisationID") 
                       VALUES (%s,%s,%s,%s,%s,%s,%s) '''
                       ,(project_code,project_name,client_name,client_addr,client_contact,remarks,session["organisation_id"]))
        conn.commit()
        
        return jsonify({
            "message" : "Project Saved Successfully"
        }), 200

@app.route("/add_employee", methods=["GET","POST"])
def add_employee():
    conn=get_db_connection()
    cursor = conn.cursor()
    if request.method == "POST":
        data = request.get_json()
        emp_name = data.get("name")
        emp_email = data.get("email")
        emp_desig = data.get("designation_id")
        emp_branch = data.get("branch_id")
        emp_username = data.get("username")
        emp_pwd = emp_username+'@7'
        org_id = 2
        user_category = "User"
        emp_dob = data.get("empDOB")
        emp_doj = data.get("empDOJ")
        
        cursor.execute(''' INSERT INTO "UserMaster" 
        ("UserName","UserPWD","EmpName","UserEmail","UserCategory","OrganisationID","BranchID","DesignationID","DateOfBirth","DateOfJoining") 
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) ''',(emp_username,emp_pwd,emp_name,emp_email,user_category,org_id,emp_branch,emp_desig,emp_dob,emp_doj))
        conn.commit()
        
        print(data)

        return jsonify({
            "message" : 'User Added Successfully'
        }), 200


@app.route('/director_meetings', methods=["GET", "POST"])
def director_meetings():
    today = datetime.today().strftime('%Y-%m-%d')
    conn = get_db_connection()
    cursor = conn.cursor()

    # -------------------
    # EDIT existing meeting
    # -------------------
    if request.method == "POST":
        edit_mode = request.form.get("edit_mode", "false").lower() == "true"
        meeting_code = request.form.get("meeting_code")

        meeting_date = request.form.get("meeting_date")
        mom_points = request.form.get("mom_points")
        remarks = request.form.get("remarks")
        crucial_points = request.form.get("crucial_points")

        directors_selected_data = json.loads(request.form.get("directors_selected") or "[]")
        staff_selected_data = json.loads(request.form.get("staff_selected") or "[]")

        if not meeting_date or not mom_points or not directors_selected_data or not staff_selected_data:
            return jsonify({"status": "error", "message": "Missing required fields."}), 400

        try:
            meeting_dt = datetime.strptime(meeting_date, '%Y-%m-%d')
        except ValueError:
            return jsonify({"status": "error", "message": "Invalid meeting date format."}), 400

        weekend_dt = meeting_dt + timedelta(days=(5 - meeting_dt.weekday()) % 7)

        cursor.execute("""SELECT "UserID", "EmpName" FROM "UserMaster" """)
        all_users = dict(cursor.fetchall())

        directors_selected = [
            {"id": entry["id"], "name": all_users.get(entry["id"], entry.get("name", "Unknown"))}
            for entry in directors_selected_data
        ]
        staff_selected = [
            {"id": entry["id"], "name": all_users.get(entry["id"], entry.get("name", "Unknown"))}
            for entry in staff_selected_data
        ]

        meeting_title = f"Meeting on {meeting_date}"

        if edit_mode:
            # UPDATE existing meeting
            update_query = """
                UPDATE "DirectorMeetingMaster"
                SET "MeetingDate" = %s,
                    "WeekendDate" = %s,
                    "ParticipantDirectors" = %s,
                    "ParticipantStaff" = %s,
                    "MOMPoints" = %s,
                    "CrucialDecisions" = %s,
                    "Remarks" = %s,
                    "MeetingTitle" = %s
                WHERE "MeetingCode" = %s
            """
            cursor.execute(update_query, (
                meeting_date,
                weekend_dt.date(),
                json.dumps(directors_selected),
                json.dumps(staff_selected),
                mom_points,
                crucial_points,
                remarks,
                meeting_title,
                meeting_code
            ))

            conn.commit()
            conn.close()

            return jsonify({
                "status": "success",
                "message": "Meeting updated successfully",
                "toast": {"header": "Updated", "body": "Meeting updated successfully"},
                "updated_title": meeting_title
            })

        else:
            # INSERT new meeting
            meeting_code = str(uuid.uuid4())
            insert_query = """
                INSERT INTO "DirectorMeetingMaster" (
                    "MeetingDate", "WeekendDate", "ParticipantDirectors",
                    "ParticipantStaff", "MOMPoints", "CrucialDecisions",
                    "Remarks", "MeetingTitle", "MeetingCode"
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            cursor.execute(insert_query, (
                meeting_date,
                weekend_dt.date(),
                json.dumps(directors_selected),
                json.dumps(staff_selected),
                mom_points,
                crucial_points,
                remarks,
                meeting_title,
                meeting_code
            ))
            conn.commit()
            conn.close()

            return jsonify({
                "status": "success",
                "message": "MOM Details Saved Successfully",
                "toast": {"header": "Server Message", "body": "MOM Details Saved Successfully"}
            })

    # -------------------
    # GET: Fetch single meeting data for view/edit
    # -------------------
    if request.method == "GET" and request.args.get("meeting_code"):
        meeting_code = request.args.get("meeting_code")
        cursor.execute("""
            SELECT "MeetingDate", "MeetingTitle", "ParticipantDirectors",
                   "ParticipantStaff", "MOMPoints", "CrucialDecisions",
                   "Remarks", "MeetingCode"
            FROM "DirectorMeetingMaster"
            WHERE "MeetingCode" = %s
        """, (meeting_code,))
        row = cursor.fetchone()
        conn.close()

        if not row:
            return jsonify({"status": "error", "message": "Meeting not found"}), 404

        meeting_data = {
            "MeetingDate": row[0].strftime('%Y-%m-%d'),
            "MeetingTitle": row[1],
            "ParticipantDirectors": json.loads(row[2]),
            "ParticipantStaff": json.loads(row[3]),
            "MOMPoints": row[4],
            "CrucialDecisions": row[5],
            "Remarks": row[6],
            "MeetingCode": row[7]
        }

        return jsonify({"status": "success", "data": meeting_data}), 200

    # -------------------
    # GET: Default page load with users and meeting list
    # -------------------

    # Fetch Directors
    cursor.execute("""
        SELECT um."UserID", um."EmpName"
        FROM "UserMaster" um
        JOIN "BranchMaster" bm ON bm."BranchID" = um."BranchID"
        WHERE bm."BranchCode" = 'DIR'
    """)
    directors = [{"id": row[0], "name": row[1]} for row in cursor.fetchall()]

    # Fetch Staff
    cursor.execute("""
        SELECT um."UserID", um."EmpName"
        FROM "UserMaster" um
        JOIN "BranchMaster" bm ON bm."BranchID" = um."BranchID"
        WHERE bm."BranchCode" != 'DIR'
        ORDER BY um."DOrder" ASC
    """)
    staff_members = [{"id": row[0], "name": row[1]} for row in cursor.fetchall()]

    # Fetch Existing Meetings
    cursor.execute("""
        SELECT "MeetingDate", "MeetingTitle", "MeetingCode"
        FROM "DirectorMeetingMaster"
        ORDER BY "MeetingDate" DESC
    """)
    meetings = cursor.fetchall()

    meeting_data = [
        {
            "sr": idx + 1,
            "title": row[1],
            "code": row[2]
        }
        for idx, row in enumerate(meetings)
    ]

    conn.close()

    return render_template(
        'meetings.html',
        today=today,
        directors=directors,
        staff_members=staff_members,
        meeting_data=meeting_data
    )

@app.route('/view_and_edit_meetings', methods=["GET", "POST"])
def view_and_edit_meetings():
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        if request.method == "GET":
            meeting_code = request.args.get('meeting_code')
            if meeting_code:
                cursor.execute("""
                    SELECT "MeetingId", "MeetingTitle", "MeetingCode", "MeetingDate", "WeekendDate",
                           "ParticipantDirectors", "ParticipantStaff", "MOMPoints", "CrucialDecisions", "Remarks",
                           "IsEdited"
                    FROM "DirectorMeetingMaster"
                    WHERE "MeetingCode" = %s
                """, (meeting_code,))
                row = cursor.fetchone()
                if not row:
                    return jsonify({"status": "error", "message": "Meeting not found"}), 404

                meeting = {
                    "MeetingID": row[0],
                    "MeetingTitle": row[1],
                    "MeetingCode": row[2],
                    "MeetingDate": row[3].strftime("%Y-%m-%d"),
                    "WeekendDate": row[4].strftime("%Y-%m-%d"),
                    "DirectorsPresent": row[5],
                    "StaffPresent": row[6],
                    "MOMPoints": row[7],
                    "CrucialDecisions": row[8],
                    "Remarks": row[9],
                    "IsEdited": row[10]
                }
                return jsonify({"status": "success", "data": meeting})

            # else: fetch all meetings
            cursor.execute("""
                SELECT "MeetingID", "MeetingTitle", "MeetingCode", "MeetingDate", "WeekendDate",
                       "ParticipantDirectors", "ParticipantStaff", "MOMPoints", "CrucialDecisions", "Remarks",
                       "IsEdited"
                FROM "DirectorMeetingMaster"
                ORDER BY "MeetingDate" DESC
            """)
            rows = cursor.fetchall()
            meetingData = [{
                "MeetingID": r[0],
                "MeetingTitle": r[1],
                "MeetingCode": r[2],
                "MeetingDate": r[3].strftime("%Y-%m-%d"),
                "WeekendDate": r[4].strftime("%Y-%m-%d"),
                "DirectorsPresent": r[5],
                "StaffPresent": r[6],
                "MOMPoints": r[7],
                "CrucialDecisions": r[8],
                "Remarks": r[9],
                "IsEdited": r[10]
            } for r in rows]
            return jsonify({"status": "success", "data": meetingData})

        elif request.method == "POST":
            data = request.get_json()
            meeting_code = data.get('meeting_code')
            mom_points = data.get('MOMPoints')
            crucial = data.get('CrucialDecisions')
            remarks = data.get('Remarks')

            if not meeting_code:
                return jsonify({"status": "error", "message": "Missing meeting_code"}), 400

            cursor.execute("""
                UPDATE "DirectorMeetingMaster"
                SET "MOMPoints" = %s, "CrucialDecisions" = %s, "Remarks" = %s, "IsEdited" = %s
                WHERE "MeetingCode" = %s AND "IsEdited" = false
            """, (mom_points, crucial, remarks, True, meeting_code))
            if cursor.rowcount == 0:
                return jsonify({"status": "error", "message": "This meeting is already edited. Cannot edit more than once."}), 400
            conn.commit()
            return jsonify({"status": "success", "message": "Meeting updated successfully"})

    except Exception as e:
        import traceback
        print("🔥 ERROR in /view_and_edit_meetings:", traceback.format_exc())
        return jsonify({"status": "error", "message": str(e)}), 500

    finally:
        cursor.close()
        conn.close()


# @app.route('/demo_email')
# def send_demo_mail():
#     app.config['MAIL_SERVER'] = 'smtp.zoho.in' # Or smtp.zoho.eu if based in Europe
#     app.config['MAIL_PORT'] = 465 # Use 465 with SSL or 587 with TLS
#     app.config['MAIL_USE_SSL'] = True
#     app.config['MAIL_USE_TLS'] = False # Set to True if using port 587
#     app.config['MAIL_USERNAME'] = 'maheshmw@zohomail.in'
#     app.config['MAIL_PASSWORD'] = 'bt3kKiHGGFft' # bt3kKiHGGFft
#     app.config['MAIL_DEFAULT_SENDER'] = 'maheshmw@zohomail.in'
#     mail = Mail(app)
#     msg = Message("Hello from Flask!", recipients=["nimishgodbole409@gmail.com"])
#     msg.body = "This is a test email sent from Flask using Zoho Mail SMTP."
#     mail.send(msg)
#     return "Email sent!"


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5002, debug=True)