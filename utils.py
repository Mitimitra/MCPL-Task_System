import smtplib
from datetime import datetime  # instead of just date
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


def send_task_assignment_email(to_email, assigner_name, project_code, task_details, designation, deadline, project_name, assigned_to_email):
    sender_email = "mitimitra@gmail.com"
    sender_password = "qrlycwlicirmbeuk"

    # Ensure `deadline` is a string in 'YYYY-MM-DD' format first
    deadline = datetime.strptime(str(deadline), "%Y-%m-%d").strftime("%d-%m-%Y")


    cc_email = "makarandg@gmail.com"

    subject = "New Task Assigned - Mitimitra Task System"
    body = f"""
    Dear {assigned_to_email},<br />
    A Fresh Task is assigned by: {assigner_name} : {designation} for project, {project_code} : {project_name}<br /><br />
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

    # Create the email message
    msg = MIMEMultipart()
    msg["From"] = sender_email
    msg["To"] = to_email
    msg["Cc"] = cc_email
    msg["Subject"] = subject
    msg.attach(MIMEText(full_body, "html"))

    recipients = [to_email, cc_email]

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(sender_email, sender_password)
            server.sendmail(sender_email, recipients, msg.as_string())
            print("Email sent successfully.")
    except Exception as e:
        print("Failed to send email:", e)