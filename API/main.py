#!/usr/bin/env python3

import os
import yaml
import uvicorn
from fastapi import FastAPI, Query, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse

import mylogger
import lotteryGenerator

# Load config from yaml file
with open("./config.yaml", 'r') as readConfig:
    try:
        config = yaml.safe_load(readConfig)
    except yaml.YAMLError as err:
        exit(err)

myLogging = mylogger.myLogger(
    config["Logger"]["logFileName"],
    config["Logger"]["maxLogFileSizeMB"],
    config["Logger"]["logLevel"],
    config["Logger"]["maxLogRotate"],
)

myLogging.info("API started")

app = FastAPI(title="AU Lottery API", debug=config.get("FastAPI", config.get("Flask", {})).get("Debug", False))


@app.get("/", response_class=HTMLResponse)
def home():
    return "<h1>API for Lottery number Generator</h1>"


@app.get("/api")
def api_id(
    game: str | None = Query(default=None),
    magic: int | None = Query(default=None),
    num: int | None = Query(default=None),
    system: int | None = Query(default=None),
):
    if game is None:
        myLogging.warning("No game field provided.")
        raise HTTPException(
            status_code=400,
            detail="No game field provided. Please specify an game.",
        )
    if magic is None:
        myLogging.warning("No magic number field provided.")
        raise HTTPException(
            status_code=400,
            detail="No magic number field provided. Please specify an magic.",
        )
    if num is None:
        myLogging.warning("No number of games field provided.")
        raise HTTPException(
            status_code=400,
            detail="No number of games field provided. Please specify an num.",
        )
    if system is None:
        myLogging.warning("No system of games field provided.")
        raise HTTPException(
            status_code=400,
            detail="No system of games field provided. Please specify an system.",
        )

    # Generate numbers
    myPlay = lotteryGenerator.PlayGame(game, magic, num, system)
    result = myPlay.callGames()
    return JSONResponse(content=result)


@app.exception_handler(404)
async def page_not_found(request: Request, exc: HTTPException):
    return HTMLResponse(
        content="<h1>404</h1><p>The resource could not be found.</p>",
        status_code=404,
    )


if __name__ == "__main__":
    if "PORT" in os.environ:
        portNum = os.environ["PORT"]
        print(portNum)
    else:
        portNum = config["Server"]["portNumber"]
    try:
        if 1 <= int(portNum) <= 65535:
            uvicorn.run(app, host="0.0.0.0", port=int(portNum))
        else:
            raise ValueError
    except ValueError:
        print("This is NOT a VALID port number.")
        myLogging.fatal(str(portNum) + " is NOT a VALID port number.")
        exit(1)

