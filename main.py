from fastapi import FastAPI, Depends, HTTPException, Request, Form
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from sqlalchemy import or_
from database import engine, get_db
import models
import schemas

models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="메모장")
templates = Jinja2Templates(directory="templates")


@app.get("/", response_class=HTMLResponse)
def index(request: Request, search: str = "", db: Session = Depends(get_db)):
    if search:
        memos = db.query(models.Memo).filter(
            or_(
                models.Memo.title.contains(search),
                models.Memo.content.contains(search)
            )
        ).order_by(models.Memo.updated_at.desc()).all()
    else:
        memos = db.query(models.Memo).order_by(models.Memo.updated_at.desc()).all()
    return templates.TemplateResponse("index.html", {
        "request": request,
        "memos": memos,
        "search": search
    })


@app.get("/memo/new", response_class=HTMLResponse)
def new_memo(request: Request):
    return templates.TemplateResponse("index.html", {
        "request": request,
        "mode": "new",
        "memos": []
    })


@app.post("/memo")
def create_memo(
    title: str = Form(...),
    content: str = Form(...),
    db: Session = Depends(get_db)
):
    memo = models.Memo(title=title, content=content)
    db.add(memo)
    db.commit()
    return RedirectResponse(url="/", status_code=303)


@app.get("/memo/{memo_id}", response_class=HTMLResponse)
def get_memo(memo_id: int, request: Request, db: Session = Depends(get_db)):
    memo = db.query(models.Memo).filter(models.Memo.id == memo_id).first()
    if not memo:
        raise HTTPException(status_code=404, detail="메모를 찾을 수 없습니다")
    memos = db.query(models.Memo).order_by(models.Memo.updated_at.desc()).all()
    return templates.TemplateResponse("index.html", {
        "request": request,
        "memo": memo,
        "memos": memos,
        "mode": "edit"
    })


@app.post("/memo/{memo_id}/update")
def update_memo(
    memo_id: int,
    title: str = Form(...),
    content: str = Form(...),
    db: Session = Depends(get_db)
):
    memo = db.query(models.Memo).filter(models.Memo.id == memo_id).first()
    if not memo:
        raise HTTPException(status_code=404, detail="메모를 찾을 수 없습니다")
    memo.title = title
    memo.content = content
    from datetime import datetime
    memo.updated_at = datetime.now()
    db.commit()
    return RedirectResponse(url=f"/memo/{memo_id}", status_code=303)


@app.post("/memo/{memo_id}/delete")
def delete_memo(memo_id: int, db: Session = Depends(get_db)):
    memo = db.query(models.Memo).filter(models.Memo.id == memo_id).first()
    if not memo:
        raise HTTPException(status_code=404, detail="메모를 찾을 수 없습니다")
    db.delete(memo)
    db.commit()
    return RedirectResponse(url="/", status_code=303)
