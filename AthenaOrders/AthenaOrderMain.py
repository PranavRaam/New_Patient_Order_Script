import FetchAthenaConfig as fc
import ReadConfig as rc
from datetime import datetime
import CommonUtil as cu
import PrevPatientCheck as pc
import ExecuteDACreatePatient as ed
import SignedOrderDownload as so
import SignedOrderExtraction as se
import execute_da_apis
import Mark_as_filed_DA as mf

def AthenaMain(credreportStorage,mode=None):
    configuration = rc.readConfig()
    logFolder = configuration["LogPath"]
    logFilepath=logFolder+"log_"+str(datetime.now().year)+"-"+str(datetime.now().month)+"-"+str(datetime.now().day)+".txt"
    configData={}
    try:
        configData=fc.getConfigData()
        cu.logFile(logFilepath,"Bot Started for Patient Creation" )
        cu.logFile(logFilepath,"Fetched Configuration for Axxess Successfully!")
        if configData["credentials"]:
            isUAT = configData["isUAT"]
            for cred in configData["credentials"]:
                credName = cred["credentialName"]
                location=cred["locationCode"]
                credURL = cred["devUrl"] if isUAT else cred["prodUrl"]
                loginUser = cred["devLoginUser"] if isUAT else cred["prodLoginUser"]
                loginPassword = cred["devLoginPassword"] if isUAT else cred["prodLoginPassword"]
                reportFolderName = cred["reportStorage"]
                daURL = cred["daDevUrl"] if isUAT else cred["daProdUrl"]
                daLoginUser = cred["daDevLoginUser"] if isUAT else cred["daProdLoginUser"]
                daLoginPassword = cred["daDevLoginPassword"] if isUAT else cred["daProdLoginPassword"]
                # DA api config
                daAPITokenUrl = cred["daDevPatientCreationAPITokenURL"] if isUAT else cred["daProdPatientCreationAPITokenURL"]
                daAPIPatientUrl = cred["daDevPatientCreationAPIURL"] if isUAT else cred["daProdPatientCreationAPIURL"]
                daAPITokenUserName = cred["daDevPatientCreationAPIUser"] if isUAT else cred["daProdPatientCreationAPIUser"]
                daAPITokenPswd = cred["daDevPatientCreationAPIPassword"] if isUAT else cred["daProdPatientCreationAPIPassword"]
                daAPITokenClinicianId = cred["daDevPatientCreationAPIClinicianID"] if isUAT else cred["daProdPatientCreationAPIClinicianID"]
                daAPITokenCaretakerId = cred["daDevPatientCreationAPICaretakerID"] if isUAT else cred["daProdPatientCreationAPICaretakerID"]
                additionals=cred["additionals"]
                helper_id=additionals[0]['value']
                cu.logFile(logFilepath,"-------------------------------------------------------------------------------")
                cu.logFile(logFilepath,"Working Started for Account "+reportFolderName )
                daToken=[daAPITokenUrl,daAPIPatientUrl,daAPITokenUserName,daAPITokenPswd,daAPITokenClinicianId,daAPITokenCaretakerId,reportFolderName]
                #Login to Athena
                if credreportStorage==reportFolderName:
                    try:
                        print("----------------------------------------")

                        ##-------------------------Doenload Signed Orders--------------------------------------------------------------
                        if mode=="download":
                            # #Download Signed Orders
                            so.download_signed_orders(daURL,daLoginUser, daLoginPassword, reportFolderName, location, credName, helper_id) #--- DA ----
                            access_token = cu.get_access_token(daAPITokenUrl,daAPITokenUserName,daAPITokenPswd)
                            execute_da_apis.execute_da_signed_order_download(access_token, daAPIPatientUrl, reportFolderName,daAPITokenCaretakerId)
                            cu.logFile(logFilepath,"Signed Orders downloaded Successfully!")

                            # # # #Extract Signed Orders
                            # # go.get_order_info(reportFolderName)
                            se.signedOrderExtraction(reportFolderName)
                            cu.logFile(logFilepath,"Signed Orders extracted Successfully!")

                        if mode=="file":
                            ## Mark it as read
                            mf.mark_as_filed(daURL,daLoginUser, daLoginPassword, reportFolderName,helper_id)

                        if not mode:
                            pass


                    except Exception as e:
                        cu.logFile(logFilepath, str(e))
                    break

                cu.logFile(logFilepath,"-------------------------------------------------------------------------------")
        cu.logFile(logFilepath,"Bot Exceution Successful!")
    except Exception as e:
        cu.logFile(logFilepath,"Fetching Configuration for Ahena failed! "+ str(e))

    


            

# AthenaMain('Athena-GAH', 'file')
