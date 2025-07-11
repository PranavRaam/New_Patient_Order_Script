import  AthenaOrderMain as mainfuncion
import FetchAthenaConfig as fc
import ReadConfig as rc
from datetime import datetime
import CommonUtil as cu


def upload_Efax_to_DA():
    configuration = rc.readConfig()
    logFolder = configuration["LogPath"]
    logFilepath=logFolder+"log_"+str(datetime.now().year)+"-"+str(datetime.now().month)+"-"+str(datetime.now().day)+".txt"
    configData={}
    try:
        configData=fc.getConfigData()
        cu.logFile(logFilepath,"Bot Started for Efax Upload" )
        cu.logFile(logFilepath,"Fetched Configuration for Athena Successfully!")
        if configData["credentials"]:
            for cred in configData["credentials"]:
                try:
                    credName = cred["credentialName"]
                    reportFolderName = cred["reportStorage"]
                    UploadFromTemplate= cred["uploadFromTemplate"]
                    if UploadFromTemplate:
                        mainfuncion.AthenaMain(reportFolderName)
                except Exception as ex:
                    cu.logFile(logFilepath,"Error: "+ credName +"- "+str(ex))
    except Exception as ex:
        cu.logFile(logFilepath,"Error: "+str(ex))
        

