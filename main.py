from fastapi import FastAPI, Depends, HTTPException, Request, Form
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import or_
from database import engine, get_db
import models
import schemas

models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="메모장")
templates = Jinja2Templates(directory="templates")


@app.get("/", response_class=HTMLResponse)
def index(request: Request, search: str = "", tag: str = "", favorite: str = "", db: Session = Depends(get_db)):
    query = db.query(models.Memo)
    if search:
        query = query.filter(
            or_(
                models.Memo.title.contains(search),
                models.Memo.content.contains(search),
                models.Memo.tags.contains(search)
            )
        )
    if tag:
        query = query.filter(models.Memo.tags.contains(tag))
    if favorite == "1":
        query = query.filter(models.Memo.is_favorite == True)
    memos = query.order_by(models.Memo.is_favorite.desc(), models.Memo.updated_at.desc()).all()

    # 전체 태그 목록
    all_memos = db.query(models.Memo).all()
    all_tags = set()
    for m in all_memos:
        if m.tags:
            for t in m.tags.split(","):
                t = t.strip()
                if t:
                    all_tags.add(t)

    return templates.TemplateResponse("index.html", {
        "request": request,
        "memos": memos,
        "search": search,
        "selected_tag": tag,
        "favorite_filter": favorite,
        "all_tags": sorted(all_tags)
    })


@app.get("/memo/new", response_class=HTMLResponse)
def new_memo(request: Request, db: Session = Depends(get_db)):
    all_memos = db.query(models.Memo).all()
    all_tags = set()
    for m in all_memos:
        if m.tags:
            for t in m.tags.split(","):
                t = t.strip()
                if t:
                    all_tags.add(t)
    return templates.TemplateResponse("index.html", {
        "request": request,
        "mode": "new",
        "memos": db.query(models.Memo).order_by(models.Memo.is_favorite.desc(), models.Memo.updated_at.desc()).all(),
        "all_tags": sorted(all_tags)
    })


@app.post("/memo")
def create_memo(
    title: str = Form(...),
    content: str = Form(...),
    tags: str = Form(default=""),
    db: Session = Depends(get_db)
):
    memo = models.Memo(title=title, content=content, tags=tags)
    db.add(memo)
    db.commit()
    return RedirectResponse(url="/", status_code=303)


@app.get("/memo/{memo_id}", response_class=HTMLResponse)
def get_memo(memo_id: int, request: Request, db: Session = Depends(get_db)):
    memo = db.query(models.Memo).filter(models.Memo.id == memo_id).first()
    if not memo:
        raise HTTPException(status_code=404, detail="메모를 찾을 수 없습니다")
    all_memos = db.query(models.Memo).all()
    all_tags = set()
    for m in all_memos:
        if m.tags:
            for t in m.tags.split(","):
                t = t.strip()
                if t:
                    all_tags.add(t)
    memos = db.query(models.Memo).order_by(models.Memo.is_favorite.desc(), models.Memo.updated_at.desc()).all()
    return templates.TemplateResponse("index.html", {
        "request": request,
        "memo": memo,
        "memos": memos,
        "mode": "edit",
        "all_tags": sorted(all_tags)
    })


@app.post("/memo/{memo_id}/update")
def update_memo(
    memo_id: int,
    title: str = Form(...),
    content: str = Form(...),
    tags: str = Form(default=""),
    db: Session = Depends(get_db)
):
    memo = db.query(models.Memo).filter(models.Memo.id == memo_id).first()
    if not memo:
        raise HTTPException(status_code=404, detail="메모를 찾을 수 없습니다")
    memo.title = title
    memo.content = content
    memo.tags = tags
    from datetime import datetime
    memo.updated_at = datetime.now()
    db.commit()
    return RedirectResponse(url=f"/memo/{memo_id}", status_code=303)


@app.post("/memo/{memo_id}/favorite")
def toggle_favorite(memo_id: int, db: Session = Depends(get_db)):
    memo = db.query(models.Memo).filter(models.Memo.id == memo_id).first()
    if not memo:
        raise HTTPException(status_code=404, detail="메모를 찾을 수 없습니다")
    memo.is_favorite = not memo.is_favorite
    db.commit()
    return JSONResponse({"is_favorite": memo.is_favorite})


@app.post("/memo/{memo_id}/delete")
def delete_memo(memo_id: int, db: Session = Depends(get_db)):
    memo = db.query(models.Memo).filter(models.Memo.id == memo_id).first()
    if not memo:
        raise HTTPException(status_code=404, detail="메모를 찾을 수 없습니다")
    db.delete(memo)
    db.commit()
    return RedirectResponse(url="/", status_code=303)
