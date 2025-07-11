import PyPDF2
import re
import os
import shutil
import CommonUtil as cu
import pandas as pd

def split_and_extract_info(reportFolderName):
    working_folder = cu.getFolderPath("O", reportFolderName)
    bulk_pdf_files=[f for f in os.listdir(working_folder) if f.startswith("BulkOrders_") and f.endswith(".pdf")]
    input_pdf_path=working_folder+"\\"+bulk_pdf_files[0]
    input_pdf_path=input_pdf_path.replace('\\','/')
    split_folder=input_pdf_path.split('/')[-1].replace('.pdf','').strip()
    split_folder=working_folder+"/"+split_folder
    if os.path.exists(split_folder):
        shutil.rmtree(split_folder)

    os.makedirs(split_folder)

    #read excel in df
    order_excel=([f for f in os.listdir(working_folder) if f.startswith("OrdersToBeSent_") and f.endswith(".xls")])[0]
    order_excel_path=working_folder+"\\"+order_excel
    order_excel_path=order_excel_path.replace('\\','/')
    dfOrder = pd.read_excel(order_excel_path, skiprows=1)


    pdf_reader = PyPDF2.PdfReader(input_pdf_path)
    total_pages = len(pdf_reader.pages)
    order_ctr=1
    page_ctr=1
    for page_num in range(total_pages):
        page = pdf_reader.pages[page_num]
        text = page.extract_text()
        text= text.replace('\n','')
        
        page_match = re.search(r'Page \d+ of \d+', text)
        # order_match =re.search(r'Order #: \d+', text)
        # print(order_match)
        matched_text=""
        
        if page_match:
            matched_text = page_match.group()
        if page_ctr==1:
            current_page_start=page_num
        if matched_text:
            if matched_text=="Page "+str(page_ctr)+" of "+str(page_ctr):
                output_pdf_path = split_folder+"/Order_"+str(order_ctr)+".pdf"
                page_ctr=0
                pdf_writer = PyPDF2.PdfWriter()
                for i in range(current_page_start, page_num + 1):
                    pdf_writer.add_page(pdf_reader.pages[i])

                with open(output_pdf_path, 'wb') as output_pdf:
                    pdf_writer.write(output_pdf)
                rename_pdf(output_pdf_path, dfOrder, split_folder)
                order_ctr=order_ctr+1
        page_ctr=page_ctr+1
    print("Bulk pdf splitted successfully by orders")


def get_order_number(text,dfOrder):
    order_no=""
    for order_number in dfOrder['Order Number']:
        if pd.notna(order_number) and 'Total Number Of Orders' not in str(order_number):
            if str(order_number) in text:
                order_no=order_number
            # else:
            #     patient = cu.clean_null_data(dfOrder['Patient'])
            #     doc_name=cu.clean_null_data(dfOrder['Type'])
            #     if patient:
            #         patient_firstname=patient.split(',')[1].strip()
            #         patient_lastname=patient.split(',')[0].strip()
            #         if patient_firstname in text and patient_lastname in text and "Auto-Generated" in doc_name:
            #             order_no=order_number
    return order_no
            
def rename_pdf(pdf_path, df, split_folder):
    pdf_reader = PyPDF2.PdfReader(pdf_path)
    total_pages = len(pdf_reader.pages)
    text=""
    for page_num in range(total_pages):
        page = pdf_reader.pages[page_num]
        text = text + page.extract_text()
    order_number= get_order_number(text,df)
    if order_number:
        output_pdf_path = split_folder+"/"+str(order_number)+".pdf"
        shutil.move(pdf_path,output_pdf_path)

    
    

# # Example usage
# input_pdf_path = "C:\\Users\\ayush\\Desktop\\AllAgencyDA\\Reports\\Axxess\\Orders\\2024-02-23\\Axxess-StandardHomeHealth\\11\\BulkOrders_638434212060411100.pdf" #path should come frm main prog reading from config file
# split_and_extract_info(input_pdf_path)

# "C:\Users\ayush\Desktop\AllAgencyDA\Reports\Axxess\Orders\2024-02-23\Axxess-StandardHomeHealth\11\BulkOrders_638434212060411100.pdf"