from typing import Dict
from fastapi import FastAPI
from pydantic import BaseModel
# import uvicorn

app = FastAPI(debug=True)
app.counter = 0
app.patients_list = dict()


@app.get("/")
async def root():
    return {"message": "Hello World during the coronavirus pandemic!"}


@app.get("/method")
async def get_method():
    return {"method": "GET"}


@app.post("/method")
async def post_method():
    return {"method": "POST"}


@app.put("/method")
async def put_method():
    return {"method": "PUT"}


@app.delete("/method")
async def delete_method():
    return {"method": "DELETE"}


def counter():
    app.counter += 1
    return str(app.counter)


class AppendPatient(BaseModel):
    name: str
    surname: str


class GetPatient(BaseModel):
    id: int = app.counter
    patient: Dict


@app.post("/patient", response_model=GetPatient)
def append_patient(patient_data: AppendPatient):
    id_ = app.counter
    app.patients_list[id_] = patient_data.dict()
    counter()
    return GetPatient(id=id_, patient=patient_data.dict())


# if __name__ == "__main__":
#     uvicorn.run(app, host="127.0.0.1", port=8000)
