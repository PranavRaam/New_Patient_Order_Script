import win32com.client
import ReadConfig as rc
from datetime import datetime
import CommonUtil as cu
import os

def send_email(reportfolder):
    try:
        outlook = win32com.client.Dispatch("Outlook.Application")
        configuration = rc.readConfig()
        to=configuration["MailTo"]
        cc=configuration["MailCC"]
        bcc=""
        rpa=configuration["RPA"]
        
        current_working_folder= cu.getFolderPath("O",reportfolder)
        attachment_path=current_working_folder+"/OrderTemplate.xlsx" 
        efaxAttachmentPath=current_working_folder+"/EfaxTemplate.xlsx" 
        mail = outlook.CreateItem(0)
        mail.Subject = "Order Bot Run Report for "+rpa+" ("+reportfolder+") "+" - "+datetime.now().strftime("%Y-%m-%d %H:%M")
        mail.Body = "PFA the Order report."
        mail.To = to
        if cc:
            mail.CC = cc
        if bcc:
            mail.BCC = bcc
        if os.path.exists(attachment_path):
            mail.Attachments.Add(attachment_path)
        if os.path.exists(efaxAttachmentPath):
            mail.Attachments.Add(efaxAttachmentPath)
        mail.Send()

        #delete folders older than archive days
        cu.DeleteOldFolders()

    except Exception as e:
        raise str(e)



send_email("Athena-GAH")