from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models import User
from app.schemas import UserCreate, UserLogin, Token, UserOut, UserUpdate
from passlib.hash import bcrypt
from app.core.security import create_access_token, get_current_user

router = APIRouter()


@router.post("/register", response_model=Token)
def register(req: UserCreate, db: Session = Depends(get_db)):
    if db.query(User).filter(User.username == req.username).first():
        raise HTTPException(status_code=400, detail="用户名已存在")
    user = User(
        username=req.username,
        hashed_password=bcrypt.hash(req.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    token = create_access_token({"sub": str(user.id), "role": user.role})
    return Token(access_token=token)


@router.post("/login", response_model=Token)
def login(req: UserLogin, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == req.username).first()
    if not user or not bcrypt.verify(req.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    token = create_access_token({"sub": str(user.id), "role": user.role})
    return Token(access_token=token)


@router.get("/me", response_model=UserOut)
def get_me(user: User = Depends(get_current_user)):
    return user


@router.patch("/me", response_model=UserOut)
def update_me(req: UserUpdate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if req.username is not None:
        duplicate = db.query(User).filter(User.username == req.username, User.id != user.id).first()
        if duplicate:
            raise HTTPException(status_code=400, detail="用户名已存在")
        user.username = req.username
    if req.password is not None:
        user.hashed_password = bcrypt.hash(req.password)
    db.commit()
    db.refresh(user)
    return user
