#!/usr/bin/python

# Written by your truly, Tyler Jones ;)

import subprocess
import sys
import re
import time
from email.message import EmailMessage
import textwrap

# funtion that extracts job ID from Slurm output passed through MailProg to then be used in 'scontrol show job ID'
def get_scontrol_info():
    
    # bool to return that will be used in main()
    info_fail = False
    fail_reason = ""

    # set fail fallback for Slurm argument
    slurm_out = None

    # get all the arguments passed to the script
    args = sys.argv[0:]

    # dynamically check the passed arguments for the one containing desired information instead of statically choosing sys.argv[2]
    for i, arg in enumerate(args):
        if 'job_id' in arg.lower().strip() or 'slurm' in arg.lower().strip():
            slurm_out = args[i]

    # check if the script failed to find the Slurm arg
    if slurm_out is None:
        info_fail = True
        fail_reason = "Failed to find argument containing Slurm Job ID."

    # set fail fallback for job ID
    id = None

    # use regex to grab job ID
    match = re.search(r'Job_id=(\S+)', slurm_out)
    if match:
        id = match.group(1).strip()

    # check if the script failed to find the job ID
    if id is None:
        info_fail = True
        fail_reason = "Failed to find Job ID in chosen argument."

    # give Slurm some time to recognize the job ID in scontrol
    time.sleep(1)

    # set fail fallback for scontrol output
    scontrol_output = None

    # run 'scontrol show job ID' command
    job_info = subprocess.run(
        ['/usr/bin/scontrol', 'show', 'job', id],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )

    # store and return scontrol output for info parsing
    scontrol_output = job_info.stdout

    # check if the script failed to find the scontrol output
    if not scontrol_output.strip():
        info_fail = True
        fail_reason = "Failed to capture scontrol output using Job ID."

    return scontrol_output, info_fail, fail_reason

# a function that (more or less) extracts information based on input string (e.g., JobId); doesn't work for everything but it gets close enough that I only need to do a little bit more cleanup
def extract_info(job_text, string):

    # find match based on input string
    match = re.search(fr'{string}=(\S+)', job_text)

    # if no match is found, return 'Unknown' place holder
    if match is None:
        return 'Unknown'
    else:
        return match.group(1)

# function to craft and send the HTML email with an input subject, body, and recipiant email
def send_html_email(subject, html_body, to_email):

    # instantiate email message and set fields based on input variables
    msg = EmailMessage()
    msg['From'] = "Hamilton Slurm Scheduler <slurm@hamilton.cluster.earlham.edu>"
    msg['To'] = to_email
    msg['Subject'] = subject

    # a plain text fallback incase the users email provider doesn't support HTML (Zimbra and Outlook support HTML)
    msg.set_content("This is an HTML email. Please view it in an HTML-compatible email client.")

    # creat HTML version of the email
    msg.add_alternative(html_body, subtype='html')

    # run sendmail command with curated email info
    with subprocess.Popen(['/usr/sbin/sendmail', '-t'], stdin=subprocess.PIPE) as proc:
        proc.communicate(msg.as_bytes())

def send_fail_email(subject, body, to_email):
    
    # instantiate email message and set fields based on input variables
    msg = EmailMessage()
    msg['From'] = "Hamilton Slurm Scheduler <slurm@hamilton.cluster.earlham.edu>"
    msg['To'] = to_email
    msg['Subject'] = subject

    # set failure reason as body of the email
    msg.set_content(body)

    # run sendmail command with curated email info
    with subprocess.Popen(['/usr/sbin/sendmail', '-t'], stdin=subprocess.PIPE) as proc:
        proc.communicate(msg.as_bytes())

def main():
    
    # default failure fallbacks
    admin_email = "tdjones22@earlham.edu"
    user_email = None
    fail_reason = ""
    
    # dynamically search for user email in list of args passed to script
    for arg in sys.argv:
        if "@earlham.edu" in arg:
          user_email = arg.strip()
          break
    else:
        # set fail reason and subject for email
        fail_reason = "Email not passed to script."
        fail_subject = "Hamilton Slurm Mail Failure"

        # send failure email and exit now
        send_fail_email(fail_subject, fail_reason, admin_email)
        exit(1)

    # get scontrol info
    job_info, fail_bool, fail_reason = get_scontrol_info()

    # check if get_scontrol_info() reported any errors, send error email, and exit script now
    if fail_bool == True:
        fail_subject = "Hamilton Slurm Mail Failure"

        # send failure email and exit now
        send_fail_email(fail_subject, fail_reason, user_email)
        exit(1)

    # job summary info
    job_name = extract_info(job_info, 'JobName')
    job_id = extract_info(job_info, 'JobId')
    job_state = extract_info(job_info, 'JobState')
    partition = extract_info(job_info, 'Partition')
    reason = extract_info(job_info, 'Reason')
    fail_state = reason
    if reason.strip() == "None":
        fail_state = 'N/A'
    else:
        fail_state = reason

    # user info
    user_id = extract_info(job_info, 'UserId').split('(')[0].strip()

    # little bit of fun easter eggs for whoever I choose to subject my wrath upon
    sneak = ''
    sneak_dict = {
      'tdjones22': '<li><strong>Surprise:</strong> The Goatiest Goat who ever Goated</li>',
      'blmendo22': '<li><strong>Surprise:</strong> Waddup blmendo22 play me a lil tune on yo piano keyboard</li>',
      'ctknight22': "<li><strong>Surprise:</strong> Charlie took Monkey D server from us...we can't let that slide</li>",
      'pelibby16': '<li><strong>Surprise:</strong> Tried smuggling a laser pointer onto a plane?! Shame on you</li>',
      'charliep': '<li><strong>Surprise:</strong> Charles Franklin Peck III</li>'
    }
    if user_id.strip() in sneak_dict.keys():
      sneak = sneak_dict[user_id]

    # timing info
    run_time = extract_info(job_info, 'RunTime')
    start_info = extract_info(job_info, 'StartTime')
    start_date = start_info.split('T')[0]
    start_time = start_info.split('T')[1]
    end_info = extract_info(job_info, 'EndTime')
    end_date = end_info.split('T')[0]
    end_time = end_info.split('T')[1]
    submit_info = extract_info(job_info, 'SubmitTime')
    submit_date = submit_info.split('T')[0]
    submit_time = submit_info.split('T')[1]

    # resource info
    nodes = extract_info(job_info, 'NodeList')
    nodelist_matches = re.findall(r'NodeList=(\S+)', job_info)
    if len(nodelist_matches) > 2:
        nodes = nodelist_matches[2]
    else:
        nodes = "Unknown"
    cores = extract_info(job_info, 'NumCPUs')
    tasks = extract_info(job_info, 'NumTasks')
    cpu_per_task = extract_info(job_info, 'CPUs/Task')

    # directory info
    command = extract_info(job_info, 'Command')
    work_dir = extract_info(job_info, 'WorkDir')
    std_out = extract_info(job_info, 'StdOut')

    # grammatical consideration based on job state for the subject
    subject = ''
    if job_state.strip() == 'FAILED':
        subject = f"Job: {job_name} (#{job_id}) has FAILED"
    elif job_state.strip() == 'COMPLETED':
        subject = f"Job: {job_name} (#{job_id}) has COMPLETED"
    else:
        subject = f"Job: {job_name} (#{job_id}) is RUNNING"

    # create HTML with included variables that will be passed to send_html_email as the body
    html_output = textwrap.dedent(f"""
    <html>
      <head>
        <style>
          body {{
            font-family: sans-serif;
            color: #222;
            margin: 0;
            padding: 0;
            background-color: #faf5f5;
            position: relative;
          }}

          .content {{
            position: relative;
            padding: 2rem;
          }}
        </style>
      </head>
      <body>
        <div class="content">
            <h2 style="color: #004080;">Hamilton Slurm Job Report – {job_state}</h2>

            <h3>📌 Job Summary</h3>
            <ul style="line-height: 150%">
              <li><strong>Job Name:</strong> {job_name}</li>
              <li><strong>Job ID:</strong> {job_id}</li>
              <li><strong>Job State:</strong> {job_state}</li>
              <li><strong>Partition:</strong> {partition}</li>
              <li><strong>Failure Reason:</strong> {fail_state}</li>
            </ul>

            <h3>👤 User Info</h3>
            <ul style="line-height: 150%">
              <li><strong>User ID:</strong> {user_id}</li>
              <li><strong>Email:</strong> {user_email}</li>
              {sneak}
            </ul>

            <h3>🕒 Timing</h3>
            <ul style="line-height: 150%">
              <li><strong>Submitted:</strong> {submit_date} at {submit_time}</li>
              <li><strong>Started:</strong> {start_date} at {start_time}</li>
              <li><strong>Ended:</strong> {end_date} at {end_time}</li>
              <li><strong>Run Time:</strong> {run_time}</li>
            </ul>

            <h3>🖥️ Resources</h3>
            <ul style="line-height: 150%">
              <li><strong>Nodes Used:</strong> {nodes}</li>
              <li><strong>Cores:</strong> {cores}</li>
              <li><strong>Tasks:</strong> {tasks}</li>
              <li><strong>CPUs/Task:</strong> {cpu_per_task}</li>
            </ul>

            <h3>📁 File Paths</h3>
            <ul style="line-height: 150%">
              <li><strong>Command:</strong> {command}</li>
              <li><strong>Working Dir:</strong> {work_dir}</li>
              <li><strong>Output Dir:</strong> {std_out}</li>
            </ul>

            <hr>
            <p style="color: #383838;">Automated Message Generated via /usr/bin/slurm-mail-v2 on Hamilton.</p>
        </div>
      </body>
    </html>
    """)

    # call the function to send the email
    send_html_email(subject, html_output, user_email)

main()
