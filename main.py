from fastapi import FastAPI, HTTPException, Depends, Header
from pydantic import BaseModel
import requests
import os
import uuid
from typing import Optional
import time

from pathlib import Path

from borb.pdf import Document
from borb.pdf import Page
from borb.pdf import SingleColumnLayout
from borb.pdf import Paragraph
from borb.pdf import PDF

from datetime import date, datetime, timedelta

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders

def send_email_with_attachment(sender_email, receiver_email, subject, body, attachment_path, smtp_server, smtp_port, login, password):
    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = receiver_email
    msg['Subject'] = subject

    msg.attach(MIMEText(body, 'plain'))

    with open(attachment_path, "rb") as attachment:
        part = MIMEBase("application", "octet-stream")
        part.set_payload(attachment.read())

    encoders.encode_base64(part)
    part.add_header(
        "Content-Disposition",
        f"attachment; filename= {attachment_path}",
    )

    msg.attach(part)

    server = smtplib.SMTP_SSL(smtp_server, smtp_port)
    server.login(login, password)

    server.sendmail(sender_email, receiver_email, msg.as_string())
    server.quit()

def send_email(sender_email, receiver_email, subject, body, smtp_server, smtp_port, login, password):
    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = receiver_email
    msg['Subject'] = subject

    msg.attach(MIMEText(body, 'plain'))

    server = smtplib.SMTP_SSL(smtp_server, smtp_port)
    server.login(login, password)

    server.sendmail(sender_email, receiver_email, msg.as_string())
    server.quit()

def current_milli_time():
    return round(time.time() * 1000)

app = FastAPI(title="Order Processing API")

class OrderRequest(BaseModel):
    SupplierID: str
    ProductID: str
    recordId: str

class AcceptReceiptRequest(BaseModel):
    QtyReceived: int
    ProductID: str
    recordId: str

class SendOrderRequest(BaseModel):
    SupplierID: str
    recordId: str

    smtp_server: str
    smtp_port: int
    mail_login: str
    mail_password: str

class SaleOrder(BaseModel):
    SupplierID: str
    #QtyOrdered: int
    #ProductID: str
    recordId: str

    smtp_server: str
    smtp_port: int
    mail_login: str
    mail_password: str

class CreatePayment(BaseModel):
    recordId: str
    order_date: int

class LogTransaction(BaseModel):
    logId: str
    logType: str
    amount: int

class NotificationSentCheck(BaseModel):
    recordId: str

class CreatePurchase(BaseModel):
    recordId: str

VIEW_ID = "viwkEdlkjrBK0"

GET_CLIENTS_URL = "https://true.tabs.sale/fusion/v1/datasheets/dstDVySpvvwyFZ2ZNp/records"
GET_PURCHASE_ORDERS_URL = "https://true.tabs.sale/fusion/v1/datasheets/dstFwmrR9HEFNCfplx/records"
GET_FINANCIAL_URL = "https://true.tabs.sale/fusion/v1/datasheets/dstCqgi4RraAS4nGoE/records"
GET_PURCHASES_URL = "https://true.tabs.sale/fusion/v1/datasheets/dstwRUpF8TQ6XNv5tW/records"
GET_PAYMENTS_URL = "https://true.tabs.sale/fusion/v1/datasheets/dst9N1LFbQ1MTXKJ6b/records"
GET_SALESLINES_URL = "https://true.tabs.sale/fusion/v1/datasheets/dst60uCNxWjrjbHBcr/records"
GET_RECEIPTS_URL = "https://true.tabs.sale/fusion/v1/datasheets/dstZqgNhRa180nHPL7/records"
GET_SUPPLIER_URL = "https://true.tabs.sale/fusion/v1/datasheets/dst7g08bwWmE60EMk0/records"
GET_ORDERLINE_URL = "https://true.tabs.sale/fusion/v1/datasheets/dstrCZuqHqu1Ztil9x/records"
GET_PRODUCT_URL = "https://true.tabs.sale/fusion/v1/datasheets/dstQ5YNHvvFU7VJCSi/records"
FIRST_API_URL = "https://true.tabs.sale/fusion/v1/datasheets/dstrCZuqHqu1Ztil9x/records"
SECOND_API_URL = "https://true.tabs.sale/fusion/v1/datasheets/dstFwmrR9HEFNCfplx/records"
TH_API_URL     = "https://true.tabs.sale/fusion/v1/datasheets/dstVuLSABiS7rhxyCG/records"

def validate_token(authorization: str = Header(...)):
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization header format")
    return authorization

@app.post("/create_purchase")
async def create_purchase(
    order: CreatePurchase,
    authorization: str = Depends(validate_token)
):
    try:
        get_sup_resp = requests.get(
            f"{GET_ORDERLINE_URL}?viewId={VIEW_ID}&fieldKey=name",
            headers={
                "Authorization": authorization
            }
        )
        get_sup_resp.raise_for_status()
        get_sup_response = get_sup_resp.json()

        QtyOrdered = 0
        UnitPrice = 0
        for i in get_sup_response['data']['records']:
            if i['fields']['POID'][0] == order.recordId:
                QtyOrdered = i['fields']['QtyOrdered']
                UnitPrice = i['fields']['UnitPrice']
                break

        end_price = QtyOrdered * UnitPrice

        second_response = requests.post(
            f"{GET_PURCHASES_URL}?viewId={VIEW_ID}&fieldKey=name",
            headers={
                "Authorization": authorization,
                "Content-Type": "application/json"
            },
            json={
                "records": [
                    {
                        "fields": {
                            "POID": [
                                order.recordId
                            ],
                            "Amount": end_price
                        }
                    }
                ],
                "fieldKey": "name"
            }
        )
        
        second_response.raise_for_status()
        second_result = second_response.json()

        th_response = requests.patch(
            f"{GET_PURCHASE_ORDERS_URL}?viewId={VIEW_ID}&fieldKey=name",
            headers={
                "Authorization": authorization,
                "Content-Type": "application/json"
            },
            json={
                "records": [
                    {
                        "recordId": order.recordId,
                        "fields": {
                            "IsSent": True
                        }
                    }
                ],
                "fieldKey": "name"
            }
        )
        
        th_response.raise_for_status()
        th_result = th_response.json()

        return {
            "status": "success",
            "req_result": get_sup_response,
            "order_result": second_result,
            "th_result": th_result
        }

    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=500, detail=f"API request failed: {str(e)}")

@app.post("/payment_notification")
async def payment_notification(
    order: NotificationSentCheck,
    authorization: str = Depends(validate_token)
):
    try:
        th_response = requests.patch(
            f"{GET_PAYMENTS_URL}?viewId={VIEW_ID}&fieldKey=name",
            headers={
                "Authorization": authorization,
                "Content-Type": "application/json"
            },
            json={
                "records": [
                    {
                        "recordId": order.recordId,
                        "fields": {
                            "IsNotificationSent": True
                        }
                    }
                ],
                "fieldKey": "name"
            }
        )
        
        th_response.raise_for_status()
        th_result = th_response.json()

        return {
            "status": "success",
            "order_result": th_result
        }
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=500, detail=f"API request failed: {str(e)}")

@app.post("/log_transaction")
async def log_transaction(
    order: LogTransaction,
    authorization: str = Depends(validate_token)
):
    try:
        idType = "PaymentID"
        if order.logType == "Expense":
            idType = "PurchaseID"

        second_response = requests.post(
            f"{GET_FINANCIAL_URL}?viewId={VIEW_ID}&fieldKey=name",
            headers={
                "Authorization": authorization,
                "Content-Type": "application/json"
            },
            json={
                "records": [
                    {
                        "fields": {
                            idType: [
                                order.logId
                            ],
                            "Type": [order.logType],
                            "Date": current_milli_time(),
                            "Amount": order.amount
                        }
                    }
                ],
                "fieldKey": "name"
            }
        )
        
        second_response.raise_for_status()
        second_result = second_response.json()

        return {
            "status": "success",
            "order_result": second_result
        }

    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=500, detail=f"API request failed: {str(e)}")

@app.post("/create_payment")
async def create_payment(
    order: CreatePayment,
    authorization: str = Depends(validate_token)
):
    try:
        get_sup_resp = requests.get(
            f"{GET_SALESLINES_URL}?viewId={VIEW_ID}&fieldKey=name",
            headers={
                "Authorization": authorization
            }
        )
        get_sup_resp.raise_for_status()
        get_sup_response = get_sup_resp.json()

        QtyOrdered = 0
        UnitPrice = 0
        for i in get_sup_response['data']['records']:
            if i['fields']['SOID'][0] == order.recordId:
                QtyOrdered = i['fields']['QtyOrdered']
                UnitPrice = i['fields']['UnitPrice']
                break

        end_price = QtyOrdered * UnitPrice

        days30 = 24 * 60 * 60 * 1_000 * 30

        second_response = requests.post(
            f"{GET_PAYMENTS_URL}?viewId={VIEW_ID}&fieldKey=name",
            headers={
                "Authorization": authorization,
                "Content-Type": "application/json"
            },
            json={
                "records": [
                    {
                        "fields": {
                            "SOID": [
                                order.recordId
                            ],
                            "Amount": end_price,
                            "DueDate": order.order_date + days30,
                            "Status": ["Pending"]
                        }
                    }
                ],
                "fieldKey": "name"
            }
        )
        
        second_response.raise_for_status()
        second_result = second_response.json()

        return {
            "status": "success",
            "req_result": get_sup_response,
            "order_result": second_result
        }

    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=500, detail=f"API request failed: {str(e)}")

@app.post("/sale_order")
async def sale_order(
    order: SaleOrder,
    authorization: str = Depends(validate_token)
):
    try:
        get_pr_resp = requests.get(
            f"{GET_SALESLINES_URL}?viewId={VIEW_ID}&fieldKey=name",
            headers={
                "Authorization": authorization
            }
        )
        get_pr_resp.raise_for_status()
        get_pr_response = get_pr_resp.json()

        productId = ""
        QtyOrdered = 0
        for i in get_pr_response['data']['records']:
            if i['fields']['SOID'][0] == order.recordId:
                productId = i['fields']['ProductID'][0]
                QtyOrdered = i['fields']['QtyOrdered']
                break



        get_sup_resp = requests.get(
            f"{GET_CLIENTS_URL}?viewId={VIEW_ID}&fieldKey=name",
            headers={
                "Authorization": authorization
            }
        )
        get_sup_resp.raise_for_status()
        get_sup_response = get_sup_resp.json()

        email = ""
        for i in get_sup_response['data']['records']:
            if i['recordId'] == order.SupplierID:
                email = i['fields']['Email']
                break

        get_stock_resp = requests.get(
            f"{TH_API_URL}?viewId={VIEW_ID}&fieldKey=name",
            headers={
                "Authorization": authorization
            }
        )
        get_stock_resp.raise_for_status()
        get_stock_response = get_stock_resp.json()

        stockId = ""
        currentQty = 0
        for i in get_stock_response['data']['records']:
            if i['fields']['ProductID'][0] == productId:
                stockId = i['recordId']
                currentQty = i['fields']['CurrentQty']
                break

        print(f"ASDSASA\n{productId}")

        if currentQty < QtyOrdered:
            send_email(
                sender_email=order.mail_login,
                receiver_email=email,
                subject="Заказ невозможно осуществить",
                body="Нет товара на складе",
                smtp_server=order.smtp_server,#"smtp.mail.ru",
                smtp_port=order.smtp_port,#465,
                login=order.mail_login,
                password=order.mail_password
            )
            return {
                "status": "failed"
            }

        th_response = requests.patch(
            f"{TH_API_URL}?viewId={VIEW_ID}&fieldKey=name",
            headers={
                "Authorization": authorization,
                "Content-Type": "application/json"
            },
            json={
                "records": [
                    {
                        "recordId": stockId,
                        "fields": {
                            "CurrentQty": currentQty - QtyOrdered
                        }
                    }
                ],
                "fieldKey": "name"
            }
        )
        
        th_response.raise_for_status()
        th_result = th_response.json()

        return {
            "status": "success",
            "order_result": th_result
        }

    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=500, detail=f"API request failed: {str(e)}")

@app.post("/accept_receipt")
async def accept_receipt(
    order: AcceptReceiptRequest,
    authorization: str = Depends(validate_token)
):
    try:
        get_sup_resp = requests.get(
            f"{TH_API_URL}?viewId={VIEW_ID}&fieldKey=name",
            headers={
                "Authorization": authorization
            }
        )
        get_sup_resp.raise_for_status()
        get_sup_response = get_sup_resp.json()

        stockId = ""
        currentQty = 0
        for i in get_sup_response['data']['records']:
            if i['fields']['ProductID'][0] == order.ProductID:
                stockId = i['recordId']
                currentQty = i['fields']['CurrentQty']
                break

        th_response = requests.patch(
            f"{TH_API_URL}?viewId={VIEW_ID}&fieldKey=name",
            headers={
                "Authorization": authorization,
                "Content-Type": "application/json"
            },
            json={
                "records": [
                    {
                        "recordId": stockId,
                        "fields": {
                            "LastUpdated": current_milli_time(),
                            "CurrentQty": currentQty + order.QtyReceived
                        }
                    }
                ],
                "fieldKey": "name"
            }
        )
        
        th_response.raise_for_status()
        th_result = th_response.json()



        re_response = requests.patch(
            f"{GET_RECEIPTS_URL}?viewId={VIEW_ID}&fieldKey=name",
            headers={
                "Authorization": authorization,
                "Content-Type": "application/json"
            },
            json={
                "records": [
                    {
                        "recordId": order.recordId,
                        "fields": {
                            "isUpdated": True
                        }
                    }
                ],
                "fieldKey": "name"
            }
        )

        re_response.raise_for_status()
        re_result = re_response.json()

        return {
            "status": "success",
            "order_result": th_result,
            "receipt_update_result": re_result
        }

    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=500, detail=f"API request failed: {str(e)}")

@app.post("/send_order")
async def send_order(
    order: SendOrderRequest,
    authorization: str = Depends(validate_token)
):
    try:
        get_sup_resp = requests.get(
            f"{GET_SUPPLIER_URL}?viewId={VIEW_ID}&fieldKey=name",
            headers={
                "Authorization": authorization
            }
        )
        get_sup_resp.raise_for_status()
        get_sup_response = get_sup_resp.json()

        email = ""
        for i in get_sup_response['data']['records']:
            if i['recordId'] == order.SupplierID:
                email = i['fields']['Email']
                break

        get_resp = requests.get(
            f"{GET_ORDERLINE_URL}?viewId={VIEW_ID}&fieldKey=name",
            headers={
                "Authorization": authorization
            }
        )
        get_resp.raise_for_status()
        get_response = get_resp.json()

        nQtyOrdered = 0
        nUnitPrice = 0

        for i in get_response['data']['records']:
            if i['fields']['POID'][0] == order.recordId:
                nQtyOrdered = i['fields']['QtyOrdered']
                nUnitPrice = i['fields']['UnitPrice']
                break

        pdf = Document()

        page = Page()
        pdf.add_page(page)

        layout = SingleColumnLayout(page)

        layout.add(Paragraph(f"DateSend: {date.today()}"))
        layout.add(Paragraph(f"QtyOrdered: {nQtyOrdered}"))
        layout.add(Paragraph(f"UnitPrice: {nUnitPrice}"))
            
        with open(Path("output.pdf"), "wb") as pdf_file_handle:
            PDF.dumps(pdf_file_handle, pdf)

        print(email)

        send_email_with_attachment(
            sender_email=order.mail_login,
            receiver_email=email,
            subject="Письмо с вложением",
            body="PDF с заказом.",
            attachment_path="output.pdf",
            smtp_server=order.smtp_server,#"smtp.mail.ru",
            smtp_port=order.smtp_port,#465,
            login=order.mail_login,
            password=order.mail_password
        )

        return {
            "status": "success",
            "order_details": get_response
        }

    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=500, detail=f"API request failed: {str(e)}")

@app.post("/new_order")
async def new_order(
    order: OrderRequest,
    authorization: str = Depends(validate_token)
):
    try:
        get_resp = requests.get(
            f"{GET_PRODUCT_URL}?viewId={VIEW_ID}&fieldKey=name",
            headers={
                "Authorization": authorization
            }
        )
        get_resp.raise_for_status()
        get_response = get_resp.json()

        ReorderQty = 0
        UnitCost = 0

        for i in get_response['data']['records']:
            if i['recordId'] == order.ProductID:
                ReorderQty = i['fields']['ReorderQty']
                UnitCost = i['fields']['UnitCost']
                break

        second_response = requests.post(
            f"{SECOND_API_URL}?viewId={VIEW_ID}&fieldKey=name",
            headers={
                "Authorization": authorization,
                "Content-Type": "application/json"
            },
            json={
                "records": [
                    {
                        "fields": {
                            "SupplierID": [
                                order.SupplierID
                            ],
                            "OrderDate": current_milli_time(),
                            "Status": "Draft"
                        }
                    }
                ],
                "fieldKey": "name"
            }
        )
        
        second_response.raise_for_status()
        second_result = second_response.json()
        print(f"\n\nABCV{second_result}\n\n")
        link = second_result['data']['records'][0]['recordId']

        # First API call - Order details
        first_response = requests.post(
            f"{FIRST_API_URL}?viewId={VIEW_ID}&fieldKey=name",
            headers={
                "Authorization": authorization,
                "Content-Type": "application/json"
            },
            json={
                "records": [
                    {
                        "fields": {
                            "QtyOrdered": ReorderQty,
                            "UnitCost": UnitCost,
                            "POID": [link],
                            "ProductID": [order.ProductID]
                        }
                    }
                ],
                "fieldKey": "name"
            }
        )
        
        first_response.raise_for_status()
        first_result = first_response.json()



        th_response = requests.patch(
            f"{TH_API_URL}?viewId={VIEW_ID}&fieldKey=name",
            headers={
                "Authorization": authorization,
                "Content-Type": "application/json"
            },
            json={
                "records": [
                    {
                        "recordId": order.recordId,
                        "fields": {
                            "POID": [link]
                        }
                    }
                ],
                "fieldKey": "name"
            }
        )
        
        th_response.raise_for_status()
        th_result = th_response.json()
        
        # Return combined results
        return {
            "status": "success",
            "order_details": first_result,
            "supplier_details": second_result,
            "th_details": th_result
        }
        
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=500, detail=f"API request failed: {str(e)}")

#if __name__ == "__main__":
#    #import uvicorn
#    #uvicorn.run(app, host="0.0.0.0", port=8000)
#    #app.run()#
