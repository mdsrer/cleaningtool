import os
import pandas as pd
from flask import Flask, request, send_file
import re
import dns.resolver
import smtplib
from flask import render_template


app = Flask(__name__)

def read_file(file):
    _, file_extension = os.path.splitext(file.filename)
    if file_extension == '.xlsx':
        return pd.read_excel(file)
    elif file_extension == '.csv':
        return pd.read_csv(file, encoding='latin1')  # Specify encoding as 'latin1'
    elif file_extension == '.txt':
        return pd.read_csv(file, delimiter='\t', encoding='latin1')  # Specify encoding as 'latin1'
    else:
        return None



def save_file(df, filename):
    _, file_extension = os.path.splitext(filename)
    if file_extension == '.xlsx':
        df.to_excel(filename, index=False)
    elif file_extension == '.csv':
        df.to_csv(filename, index=False)
    elif file_extension == '.txt':
        df.to_csv(filename, index=False, sep='\t')

def is_valid_email(email):
    # Regular expression pattern for email validation
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email)

def is_valid_domain(domain):
    try:
        socket.gethostbyname(domain)
        return True
    except socket.error:
        return False

def verify_domain(domain):
    try:
        answers = dns.resolver.resolve(domain, 'MX')
        # If there are MX records for the domain, it's considered valid
        return True
    except dns.resolver.NoAnswer:
        # If there are no MX records for the domain, it's considered invalid
        return False
    except dns.resolver.NXDOMAIN:
        # If the domain doesn't exist, it's considered invalid
        return False
    except Exception as e:
        # Handle other exceptions, e.g., network errors
        # print(f"Error occurred: {e}")
        return False

def is_role_email(email):
    # Logic to detect role-based email addresses
    # Example: admin@example.com, support@example.com
    role_emails = ['admin', 'support']  # Add more role email patterns if needed
    username = email.split('@')[0]
    return username.lower() in role_emails

def is_disposable_email(email):
    # Logic to detect disposable email addresses
    # Example: mailinator.com, tempmail.com
    disposable_domains = ['mailinator.com', 'tempmail.com']  # Add more disposable email domains if needed
    domain = email.split('@')[1]
    return domain.lower() in disposable_domains

def is_mailbox_exist(email):
    # Address used for SMTP MAIL FROM command
    fromAddress = 'your_email@example.com'  # Change this to your email address

    # Syntax check
    if not is_valid_email(email):
        # print('Invalid email syntax')
        return False

    # Get domain for DNS lookup
    domain = email.split('@')[1]
    # print('Domain:', domain)

    # MX record lookup
    try:
        records = dns.resolver.query(domain, 'MX')
        mxRecord = str(records[0].exchange)
    except Exception as e:
        # print(f"Error while querying MX record for {domain}: {e}")
        return False

    # SMTP lib setup (use debug level for full output)
    server = smtplib.SMTP()
    server.set_debuglevel(0)

    # SMTP Conversation
    try:
        server.connect(mxRecord)
        server.helo(server.local_hostname)
        server.mail(fromAddress)
        code, message = server.rcpt(str(email))
        server.quit()

        # Assume SMTP response 250 is success
        if code == 250:
            # print('Mailbox exists')
            return True
        else:
            # print('Mailbox does not exist')
            return False
    except Exception as e:
        # print(f"Error while checking mailbox existence for {email}: {e}")
        return False

# def remove_invalid_emails(df):
#     valid_emails = []
#     for email in df['email']:
#         if is_valid_email(email) and verify_domain(email.split('@')[1]) and not is_role_email(email) \
#                 and not is_disposable_email(email) and is_mailbox_exist(email):
#             valid_emails.append(email)
#     return pd.DataFrame({'email': valid_emails})

# def remove_invalid_emails(df):
#     valid_emails = []
#     for email in df['email']:
#         if email is not None and is_valid_email(email) and verify_domain(email.split('@')[1]) and not is_role_email(email) \
#                 and not is_disposable_email(email) and is_mailbox_exist(email):
#             valid_emails.append(email)
#     return pd.DataFrame({'email': valid_emails})


# def remove_invalid_emails(df):
#     valid_emails = []
#     for email in df['email']:
#         if email=="":
#             continue
#         elif isinstance(email, str) and is_valid_email(email) and verify_domain(email.split('@')[1]) and not is_role_email(email) \
#                 and not is_disposable_email(email) and is_mailbox_exist(email):
#             valid_emails.append(email)
#     return pd.DataFrame({'email': valid_emails})

def remove_invalid_emails(df):
    valid_rows = []
    for index, row in df.iterrows():
        print(f"Email: {row[email_column]} checking...")
        if pd.notnull(row[email_column]) and is_valid_email(row[email_column]) and \
           verify_domain(row[email_column].split('@')[1]) and \
           not is_role_email(row[email_column]) and \
           not is_disposable_email(row[email_column]) and \
           is_mailbox_exist(row[email_column]):
            print("Status: Valid")
            valid_rows.append(row)
        else:
            print("Status: NOT Valid!")
            print(email_column)
    return pd.DataFrame(valid_rows)




def is_email(s):
    # Regular expression to match typical email patterns
    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    return re.match(email_pattern, str(s)) is not None

def detect_email_column(df, threshold=0.8):
    for column in df.columns:
        email_count = sum(df[column].apply(is_email))
        if email_count / len(df[column]) >= threshold:
            return column
    return None

@app.route('/')
def index():
    return render_template('index_d.html')

@app.route('/upload', methods=['POST'])
def upload():
    file1 = request.files['file1']

    if file1.filename == '':
        return render_template('index_d.html', alert_message="Please select at least 1 file to upload.")

    df1 = read_file(file1)
    
    # Find the column containing emails
    global email_column
    # email_column = None
    # for column in df1.columns:
    #     if any(df1[column].str.contains('@')):
    #         email_column = column
    #         break

    email_column = detect_email_column(df1)
    
    if email_column is None:
        return render_template('index_d.html', alert_message="No column found containing emails.")

    df1 = df1.drop_duplicates(subset=email_column)
    df1_cleaned = remove_invalid_emails(df1)

    output_filename = 'output' + os.path.splitext(file1.filename)[1]
    save_file(df1_cleaned, output_filename)

    # Return the modified file for download
    return send_file(output_filename, as_attachment=True)


if __name__ == '__main__':
    app.run()
