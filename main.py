from fastapi import FastAPI, HTTPException, Depends, Header
from pydantic import BaseModel
import requests
import os
import uuid
from typing import Optional
import time

def current_milli_time():
    return round(time.time() * 1000)

app = FastAPI(title="Order Processing API")

# Pydantic model for request validation
class OrderRequest(BaseModel):
    SupplierID: str
    ProductID: str
    #POID: str
    ReorderQty: int
    UnitCost: float
    recordId: str

# First API endpoint configuration
FIRST_API_URL = "https://true.tabs.sale/fusion/v1/datasheets/dstrCZuqHqu1Ztil9x/records"
FIRST_VIEW_ID = "viwkEdlkjrBK0"

# Second API endpoint configuration
SECOND_API_URL = "https://true.tabs.sale/fusion/v1/datasheets/dstFwmrR9HEFNCfplx/records"
SECOND_VIEW_ID = "viwkEdlkjrBK0"

TH_API_URL     = "https://true.tabs.sale/fusion/v1/datasheets/dstVuLSABiS7rhxyCG/records"
TH_VIEW_ID = "viwkEdlkjrBK0"

def validate_token(authorization: str = Header(...)):
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization header format")
    return authorization

@app.post("/new_order")
async def new_order(
    order: OrderRequest,
    authorization: str = Depends(validate_token)
):
    try:
        # Second API call - Supplier information
        # Assuming similar structure but with different fields
        second_response = requests.post(
            f"{SECOND_API_URL}?viewId={SECOND_VIEW_ID}&fieldKey=name",
            headers={
                "Authorization": authorization,
                "Content-Type": "application/json"
            },
            json={
                "records": [
                    {
                        "fields": {
                            "POID": str(uuid.uuid4()),
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
            f"{FIRST_API_URL}?viewId={FIRST_VIEW_ID}&fieldKey=name",
            headers={
                "Authorization": authorization,
                "Content-Type": "application/json"
            },
            json={
                "records": [
                    {
                        "fields": {
                            "QtyOrdered": order.ReorderQty,
                            "UnitCost": order.UnitCost,
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
            f"{TH_API_URL}?viewId={TH_VIEW_ID}&fieldKey=name",
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
