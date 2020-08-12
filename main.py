from fastapi.responses import RedirectResponse
from fastapi import FastAPI, Request, Response, status, Cookie, HTTPException, Depends
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from hashlib import sha256
from typing import Dict
import secrets
import sqlite3
# import uvicorn


class Patient(BaseModel):
    name: str
    surname: str

app = FastAPI(debug=True)
security = HTTPBasic()
templates = Jinja2Templates(directory="templates")

app.secret_key = "YgFYfgWQ2LhTQSY9MujYu6dXyRZZPuRuzjZE5qM3dMKe6pf3TE6tDwDe6LcMKDfP"
app.ses = {}

app.counter = 0
app.storage: Dict[str, Patient] = {}
app.user_data = {"trudnY": "PaC13Nt"}



@app.on_event("startup")
async def startup():
    app.db_connection = sqlite3.connect('chinook.db')


@app.on_event("shutdown")
async def shutdown():
    app.db_connection.close()


@app.get("/")
def root():
    return {"message": "Hello World during the coronavirus pandemic!"}
    

@app.get("/tracks")
async def tracks(page: int = 0, per_page: int = 10):
    app.db_connection.row_factory = sqlite3.Row
    data = app.db_connection.execute(
        f"SELECT * FROM tracks LIMIT {per_page} OFFSET {page * per_page}"
        ).fetchall()
    return data


@app.get("/tracks/composers/")
async def composer_tracks(response: Response, composer_name: str):
    app.db_connection.row_factory = lambda cursor, row: row[0]
    data = app.db_connection.execute(
        f"""SELECT name
            FROM tracks
            WHERE composer IS '{composer_name}'
            ORDER BY name"""
        ).fetchall()
    if len(data) == 0:
        response.status_code = status.HTTP_404_NOT_FOUND
        return {"detail": {"error": "Couldn't find songs by this composer."}}
    else:
        return data


class Album(BaseModel):
    title: str
    artist_id: int


@app.post("/albums")
async def add_albums(response: Response, album: Album):
    app.db_connection.row_factory = lambda cursor, row: row[0]
    data = app.db_connection.execute(
        f"SELECT * FROM artists WHERE ArtistId = ?", (album.artist_id,)
        ).fetchall()
    if len(data) == 0:
        response.status_code = status.HTTP_404_NOT_FOUND
        return {"detail":
                {"error": "Can't add album for non-existant artist id."}
                }
    else:
        cursor = app.db_connection.execute(
            f"""INSERT INTO albums (Title, ArtistId)
                VALUES (?, ?)""", (album.title, album.artist_id)
            )
        app.db_connection.commit()
        response.status_code = status.HTTP_201_CREATED
        return {
            "AlbumId": cursor.lastrowid,
            "Title": album.title,
            "ArtistId": album.artist_id,
        }


@app.get("/albums/{album_id}")
async def get_album_by_id(album_id: int):
    app.db_connection.row_factory = sqlite3.Row
    data = app.db_connection.execute(
        f"SELECT * FROM albums WHERE AlbumId = ?", (album_id,)
        ).fetchone()
    return data


class Customer(BaseModel):
    company: str = None
    address: str = None
    city: str = None
    state: str = None
    country: str = None
    postalcode: str = None
    fax: str = None


@app.put("/customers/{customer_id}")
async def update_customer_info(
        response: Response,
        customer_id: int,
        customer: Customer
     ):
    app.db_connection.row_factory = sqlite3.Row
    data = app.db_connection.execute(
            f"SELECT * FROM customers WHERE CustomerId = ?", (customer_id,)
        ).fetchone()
    if data is None:
        response.status_code = status.HTTP_404_NOT_FOUND
        return {"detail": {"error": "Couldn't find customer with this id."}}
    update_customer = customer.dict(exclude_unset=True)
    query = [f"{k} = '{v}'" for k, v in update_customer.items()]
    query = ', '.join(query)
    cursor = app.db_connection.execute(
        f"UPDATE customers SET {query} WHERE customerid = ?", (customer_id,)
    )
    app.db_connection.commit()

    data = app.db_connection.execute(
            f"SELECT * FROM customers WHERE CustomerId = ?", (customer_id,)
        ).fetchone()

    return data


@app.get("/sales")
async def sales_stats(response: Response, category: str):
    if category == "customers":
        app.db_connection.row_factory = sqlite3.Row
        data = app.db_connection.execute(
                f"""SELECT customers.customerid
                    ,customers.email
                    ,customers.phone
                    ,ROUND(SUM(invoices.total), 2) as Sum
                    FROM customers
                    JOIN invoices ON customers.customerid = invoices.customerid
                    GROUP BY invoices.customerid
                    ORDER BY Sum DESC, invoices.customerid"""
            ).fetchall()
        return data
    elif category == "genres":
        app.db_connection.row_factory = sqlite3.Row
        data = app.db_connection.execute(
                f"""SELECT genres.name as Name
                    ,SUM(invoice_items.quantity) as Sum
                    FROM genres
                    JOIN tracks ON tracks.genreid = genres.genreid
                    JOIN invoice_items ON invoice_items.trackid = tracks.trackid
                    GROUP BY genres.name
                    ORDER BY Sum DESC, Name"""
            ).fetchall()
        return data
    else:
        response.status_code = status.HTTP_404_NOT_FOUND
        return {"detail":
                {"error": "Can't present statistics for this category."}
                }

def check_cookie(session_token: str = Cookie(None)):
    if session_token not in app.ses:
        session_token = None
    else:
        return session_token

@app.get("/welcome")
def welcome(request: Request, response: Response, session_token: str = Depends(check_cookie)):
    if session_token is None:
        response.status_code = status.HTTP_401_UNAUTHORIZED
        return "Error 401"
    name = app.ses[session_token]
    return templates.TemplateResponse("item.html", {"request": request, "user": name})


def get_current_username(credentials: HTTPBasicCredentials = Depends(security)):
    check = False
    for key_name, value in app.user_data.items():
        correct_username = secrets.compare_digest(credentials.username, key_name)
        correct_password = secrets.compare_digest(credentials.password, value)
        if correct_password and correct_username:
            check = True
    if not check:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Basic"},
        )

    session_token = sha256(
        bytes(f"{credentials.username}{credentials.password}{app.secret_key}", encoding='utf8')).hexdigest()
    app.ses[session_token] = credentials.username
    return session_token



@app.post("/login")
def logging(response: Response, session_token: str = Depends(get_current_username)):
    response.status_code = status.HTTP_302_FOUND
    response.headers["Location"] = "/welcome"
    response.set_cookie(key="session_token", value=session_token)


@app.post("/logout")
def logginout(response: Response, session_token: str = Depends(check_cookie)):
    if session_token is None:
        response.status_code = status.HTTP_401_UNAUTHORIZED
        return "401"
    response.status_code = status.HTTP_302_FOUND
    response.headers["Location"] = "/"
    del app.ses[session_token]


@app.api_route(path="/method", methods=["GET", "POST", "DELETE", "PUT", "OPTIONS"])
def read_request(request: Request):
    return {"method": request.method}

#
@app.post("/patient")
def new_patient(response: Response, patient: Patient, session_token: str = Depends(check_cookie)):
    if session_token is None:
        response.status_code = status.HTTP_401_UNAUTHORIZED
        return "401"
    resp = {"id_": app.counter, "patient": patient}
    pk = f"id_{app.counter}"
    app.storage["id_" + str(app.counter)] = patient
    response.status_code = status.HTTP_302_FOUND
    response.headers["Location"] = "/patient/{pk}"
    app.counter += 1
    return resp


@app.get("/patient")
def get_patients(response: Response, session_token: str = Depends(check_cookie)):
    if session_token is None:
        response.status_code = status.HTTP_401_UNAUTHORIZED
        return "401"
    elif app.storage:
        return app.storage
    response.status_code = status.HTTP_204_NO_CONTENT

@app.get("/patient/{pk}")
def get_patient(pk: str, response: Response, session_token: str = Depends(check_cookie)):
    if session_token is None:
        response.status_code = status.HTTP_401_UNAUTHORIZED
        return "401"
    elif pk in app.storage:
        return app.storage.get(pk)
    response.status_code = status.HTTP_204_NO_CONTENT

@app.delete("/patient/{pk}")
def del_patient(pk: str, response: Response, session_token: str = Depends(check_cookie)):
    if session_token is None:
        response.status_code = status.HTTP_401_UNAUTHORIZED
        return "401"
    app.storage.pop(pk, None)
    response.status_code = status.HTTP_204_NO_CONTENT

# if __name__ == "__main__":
#     uvicorn.run(app, host="127.0.0.1", port=8000)
#

