import smtplib
from datetime import datetime  # instead of just date
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from flask_mail import Mail, Message

def send_task_assignment_email(mail,to_email, assigner_name, project_code, task_details, designation, deadline, project_name, assigned_to_email):
    # sender_email = "mitimitra@gmail.com"
    # sender_password = "qrlycwlicirmbeuk"

    # Ensure `deadline` is a string in 'YYYY-MM-DD' format first
    
    deadline = datetime.strptime(str(deadline), "%Y-%m-%d").strftime("%d-%m-%Y")


    cc_email = "mitimitra@gmail.com"

    subject = "New Task Assigned - Mitimitra Task System"
    body = f"""
    Dear {to_email},<br />
    A Fresh Task is assigned by: {assigner_name} : {designation} <br />for project, {project_code} : {project_name}<br /><br />
    Task Details: {task_details} <br />
    You are expected to complete this task by : {deadline} and upload details once completed in the software.<br />
    This mail is electronically generated, hence should not be replied.
    """
    
    signature = """
    <br /><br />
    <hr>
    <p style="font-family: Arial, sans-serif; font-size: 14px;">
        Thanks & Regards,<br>
        <strong><a href="https://mitimitra.com" target="_blank">Mitimitra Consultants Pvt. Ltd.</a></strong><br>
        Online - Task Management System<br>
    </p>
    """
    
    full_body = f"{body}{signature}"
    
    print(assigned_to_email)
    
    msg = Message(subject=subject, recipients=[assigned_to_email], cc=cc_email)
    msg.html = full_body
    mail.send(msg)