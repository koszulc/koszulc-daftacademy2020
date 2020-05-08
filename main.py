import aiosqlite
import sqlite3
from contextlib import contextmanager
from fastapi import FastAPI, Response, status
from pydantic import BaseModel
import uvicorn

app = FastAPI(debug=True)


@app.on_event("startup")
async def startup():
    app.db_connection = sqlite3.connect('chinook.db')


@app.on_event("shutdown")
async def shutdown():
   app.db_connection.close()




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


# @app.get("/tracks/composers/")
# async def composers(response: Response, composer_name: str):
#     pass

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
