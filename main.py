import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

from fastapi import FastAPI, Depends, HTTPException, Request, Form, UploadFile, File
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse, StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import or_
from database import engine, get_db
import models
import json
from datetime import datetime

models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="메모장")
templates = Jinja2Templates(directory="templates")


def get_sidebar_data(db: Session):
    all_memos = db.query(models.Memo).filter(models.Memo.is_deleted == False).all()
    all_tags, all_categories = set(), set()
    for m in all_memos:
        if m.tags:
            for t in m.tags.split(","):
                t = t.strip()
                if t: all_tags.add(t)
        if m.category and m.category.strip():
            all_categories.add(m.category.strip())
    trash_count = db.query(models.Memo).filter(models.Memo.is_deleted == True).count()
    return sorted(all_tags), sorted(all_categories), trash_count


def get_memo_list(db: Session, sort: str = "updated"):
    query = db.query(models.Memo).filter(models.Memo.is_deleted == False)
    if sort == "title":
        return query.order_by(models.Memo.is_pinned.desc(), models.Memo.title.asc()).all()
    elif sort == "created":
        return query.order_by(models.Memo.is_pinned.desc(), models.Memo.created_at.desc()).all()
    return query.order_by(models.Memo.is_pinned.desc(), models.Memo.is_favorite.desc(), models.Memo.updated_at.desc()).all()


@app.get("/", response_class=HTMLResponse)
def index(request: Request, search: str = "", tag: str = "", category: str = "",
          favorite: str = "", sort: str = "updated", db: Session = Depends(get_db)):
    query = db.query(models.Memo).filter(models.Memo.is_deleted == False)
    if search:
        query = query.filter(or_(
            models.Memo.title.contains(search),
            models.Memo.content.contains(search),
            models.Memo.tags.contains(search)
        ))
    if tag: query = query.filter(models.Memo.tags.contains(tag))
    if category: query = query.filter(models.Memo.category == category)
    if favorite == "1": query = query.filter(models.Memo.is_favorite == True)
    if sort == "title":
        memos = query.order_by(models.Memo.is_pinned.desc(), models.Memo.title.asc()).all()
    elif sort == "created":
        memos = query.order_by(models.Memo.is_pinned.desc(), models.Memo.created_at.desc()).all()
    else:
        memos = query.order_by(models.Memo.is_pinned.desc(), models.Memo.is_favorite.desc(), models.Memo.updated_at.desc()).all()

    all_tags, all_categories, trash_count = get_sidebar_data(db)
    return templates.TemplateResponse("index.html", {
        "request": request, "memos": memos, "search": search,
        "selected_tag": tag, "selected_category": category,
        "favorite_filter": favorite, "sort": sort,
        "all_tags": all_tags, "all_categories": all_categories, "trash_count": trash_count
    })


@app.get("/trash", response_class=HTMLResponse)
def trash_view(request: Request, db: Session = Depends(get_db)):
    memos = db.query(models.Memo).filter(models.Memo.is_deleted == True).order_by(models.Memo.deleted_at.desc()).all()
    all_tags, all_categories, _ = get_sidebar_data(db)
    return templates.TemplateResponse("index.html", {
        "request": request, "memos": memos, "trash_mode": True,
        "trash_count": len(memos), "all_tags": all_tags, "all_categories": all_categories
    })


@app.get("/memo/new", response_class=HTMLResponse)
def new_memo(request: Request, db: Session = Depends(get_db)):
    all_tags, all_categories, trash_count = get_sidebar_data(db)
    memos = get_memo_list(db)
    return templates.TemplateResponse("index.html", {
        "request": request, "mode": "new", "memos": memos,
        "all_tags": all_tags, "all_categories": all_categories, "trash_count": trash_count
    })


@app.post("/memo")
def create_memo(title: str = Form(...), content: str = Form(...),
                tags: str = Form(default=""), category: str = Form(default=""),
                color: str = Form(default=""), db: Session = Depends(get_db)):
    memo = models.Memo(title=title, content=content, tags=tags, category=category, color=color)
    db.add(memo)
    db.commit()
    db.refresh(memo)
    return RedirectResponse(url=f"/memo/{memo.id}", status_code=303)


@app.get("/memo/{memo_id}", response_class=HTMLResponse)
def get_memo(memo_id: int, request: Request, db: Session = Depends(get_db)):
    memo = db.query(models.Memo).filter(models.Memo.id == memo_id).first()
    if not memo:
        raise HTTPException(status_code=404, detail="메모를 찾을 수 없습니다")
    all_tags, all_categories, trash_count = get_sidebar_data(db)
    if memo.is_deleted:
        trash_memos = db.query(models.Memo).filter(models.Memo.is_deleted == True).order_by(models.Memo.deleted_at.desc()).all()
        return templates.TemplateResponse("index.html", {
            "request": request, "memo": memo, "memos": trash_memos,
            "mode": "trash_view", "trash_mode": True,
            "trash_count": len(trash_memos), "all_tags": all_tags, "all_categories": all_categories
        })
    memos = get_memo_list(db)
    return templates.TemplateResponse("index.html", {
        "request": request, "memo": memo, "memos": memos, "mode": "edit",
        "all_tags": all_tags, "all_categories": all_categories, "trash_count": trash_count
    })


@app.post("/memo/{memo_id}/update")
def update_memo(memo_id: int, title: str = Form(...), content: str = Form(...),
                tags: str = Form(default=""), category: str = Form(default=""),
                color: str = Form(default=""), db: Session = Depends(get_db)):
    memo = db.query(models.Memo).filter(models.Memo.id == memo_id).first()
    if not memo: raise HTTPException(status_code=404)
    memo.title = title
    memo.content = content
    memo.tags = tags
    memo.category = category
    memo.color = color
    memo.updated_at = datetime.now()
    db.commit()
    return RedirectResponse(url=f"/memo/{memo_id}", status_code=303)


@app.post("/memo/{memo_id}/autosave")
async def autosave(memo_id: int, request: Request, db: Session = Depends(get_db)):
    form = await request.form()
    memo = db.query(models.Memo).filter(models.Memo.id == memo_id).first()
    if not memo: return JSONResponse({"status": "error"}, status_code=404)
    memo.title = form.get("title", memo.title)
    memo.content = form.get("content", memo.content)
    memo.tags = form.get("tags", memo.tags)
    memo.category = form.get("category", memo.category)
    memo.color = form.get("color", memo.color)
    memo.updated_at = datetime.now()
    db.commit()
    return JSONResponse({"status": "saved", "time": memo.updated_at.strftime('%H:%M:%S')})


@app.post("/memo/{memo_id}/favorite")
def toggle_favorite(memo_id: int, db: Session = Depends(get_db)):
    memo = db.query(models.Memo).filter(models.Memo.id == memo_id).first()
    if not memo: raise HTTPException(status_code=404)
    memo.is_favorite = not memo.is_favorite
    db.commit()
    return JSONResponse({"is_favorite": memo.is_favorite})


@app.post("/memo/{memo_id}/pin")
def toggle_pin(memo_id: int, db: Session = Depends(get_db)):
    memo = db.query(models.Memo).filter(models.Memo.id == memo_id).first()
    if not memo: raise HTTPException(status_code=404)
    memo.is_pinned = not memo.is_pinned
    db.commit()
    return JSONResponse({"is_pinned": memo.is_pinned})


@app.post("/memo/{memo_id}/delete")
def delete_memo(memo_id: int, db: Session = Depends(get_db)):
    memo = db.query(models.Memo).filter(models.Memo.id == memo_id).first()
    if not memo: raise HTTPException(status_code=404)
    memo.is_deleted = True
    memo.deleted_at = datetime.now()
    db.commit()
    return RedirectResponse(url="/", status_code=303)


@app.post("/memo/{memo_id}/restore")
def restore_memo(memo_id: int, db: Session = Depends(get_db)):
    memo = db.query(models.Memo).filter(models.Memo.id == memo_id).first()
    if not memo: raise HTTPException(status_code=404)
    memo.is_deleted = False
    memo.deleted_at = None
    db.commit()
    return RedirectResponse(url="/trash", status_code=303)


@app.post("/memo/{memo_id}/permanent-delete")
def permanent_delete(memo_id: int, db: Session = Depends(get_db)):
    memo = db.query(models.Memo).filter(models.Memo.id == memo_id).first()
    if not memo: raise HTTPException(status_code=404)
    db.delete(memo)
    db.commit()
    return RedirectResponse(url="/trash", status_code=303)


@app.get("/memo/{memo_id}/export/txt")
def export_txt(memo_id: int, db: Session = Depends(get_db)):
    memo = db.query(models.Memo).filter(models.Memo.id == memo_id).first()
    if not memo: raise HTTPException(status_code=404)
    text = f"{memo.title}\n{'='*40}\n\n{memo.content}\n\n작성: {memo.created_at.strftime('%Y-%m-%d %H:%M')}\n수정: {memo.updated_at.strftime('%Y-%m-%d %H:%M')}"
    return StreamingResponse(
        io.BytesIO(text.encode('utf-8-sig')),
        media_type="text/plain; charset=utf-8",
        headers={"Content-Disposition": f"attachment; filename=memo_{memo_id}.txt"}
    )


@app.get("/backup")
def backup_all(db: Session = Depends(get_db)):
    memos = db.query(models.Memo).filter(models.Memo.is_deleted == False).all()
    data = [{"title": m.title, "content": m.content, "tags": m.tags,
             "category": m.category, "color": m.color,
             "is_favorite": m.is_favorite, "is_pinned": m.is_pinned,
             "created_at": m.created_at.isoformat(), "updated_at": m.updated_at.isoformat()} for m in memos]
    return StreamingResponse(
        io.BytesIO(json.dumps(data, ensure_ascii=False, indent=2).encode('utf-8-sig')),
        media_type="application/json; charset=utf-8",
        headers={"Content-Disposition": "attachment; filename=memo_backup.json"}
    )


@app.post("/restore-backup")
async def restore_backup(file: UploadFile = File(...), db: Session = Depends(get_db)):
    content = await file.read()
    try:
        data = json.loads(content.decode('utf-8-sig'))
        for item in data:
            memo = models.Memo(
                title=item.get("title", ""), content=item.get("content", ""),
                tags=item.get("tags", ""), category=item.get("category", ""),
                color=item.get("color", ""), is_favorite=item.get("is_favorite", False),
                is_pinned=item.get("is_pinned", False),
            )
            db.add(memo)
        db.commit()
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    return RedirectResponse(url="/", status_code=303)
