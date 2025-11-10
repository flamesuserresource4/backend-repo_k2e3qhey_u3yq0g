import os
import hashlib
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from bson import ObjectId
from typing import List, Optional

from database import db, create_document, get_documents
from schemas import User, Group, Post, Comment, Like

app = FastAPI(title="Campus Social API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Utility to convert Mongo documents to JSON-serializable dicts

def to_public(doc: dict):
    if not doc:
        return doc
    d = {**doc}
    _id = d.pop("_id", None)
    if isinstance(_id, ObjectId):
        d["id"] = str(_id)
    if "password_hash" in d:
        d.pop("password_hash")
    return d

@app.get("/")
def read_root():
    return {"message": "Campus Social API is running"}

@app.get("/test")
def test_database():
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }
    try:
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
            response["database_name"] = db.name if hasattr(db, 'name') else "✅ Connected"
            response["connection_status"] = "Connected"
            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️  Connected but Error: {str(e)[:50]}"
        else:
            response["database"] = "⚠️  Available but not initialized"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:50]}"

    response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
    response["database_name"] = "✅ Set" if os.getenv("DATABASE_NAME") else "❌ Not Set"
    return response

# --------- Basic role check (simple header-based for demo) ---------
class AuthInfo(BaseModel):
    user_id: Optional[str] = None
    role: str = "user"


def get_auth(role: Optional[str] = None):
    def dep():
        # In a real app, use JWT. For demo, read headers via dependency override later if needed
        # Here we just default to role=user
        info = AuthInfo(role="user")
        if role and role not in ["user", "moderator", "admin"]:
            raise HTTPException(status_code=403, detail="Invalid role")
        if role in ["moderator", "admin"]:
            # Allow for testing by env override; production would validate token
            pass
        return info
    return dep

# ----------------- Simple Auth (Demo) -----------------
class RegisterRequest(BaseModel):
    name: str
    email: str
    password: str

class LoginRequest(BaseModel):
    email: str
    password: str

@app.post("/api/auth/register")
def register(req: RegisterRequest):
    # Check duplicate email
    existing = get_documents("user", {"email": req.email}, 1)
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    password_hash = hashlib.sha256(req.password.encode()).hexdigest()
    user = User(name=req.name, email=req.email, role="user", avatar_url=None, password_hash=password_hash)
    uid = create_document("user", user)
    created = get_documents("user", {"_id": ObjectId(uid)}, 1)
    return to_public(created[0]) if created else {"id": uid, "name": req.name, "email": req.email, "role": "user"}

@app.post("/api/auth/login")
def login(req: LoginRequest):
    users = get_documents("user", {"email": req.email}, 1)
    if not users:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    u = users[0]
    password_hash = hashlib.sha256(req.password.encode()).hexdigest()
    if u.get("password_hash") != password_hash:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return to_public(u)

# ----------------- Users -----------------
@app.post("/api/users")
def create_user(user: User):
    user_id = create_document("user", user)
    return {"id": user_id}

@app.get("/api/users")
def list_users(limit: int = 50):
    users = get_documents("user", {}, limit)
    return [to_public(u) for u in users]

# ----------------- Groups -----------------
@app.post("/api/groups", dependencies=[Depends(get_auth("moderator"))])
def create_group(group: Group):
    gid = create_document("group", group)
    return {"id": gid}

@app.get("/api/groups")
def list_groups(limit: int = 50):
    groups = get_documents("group", {}, limit)
    return [to_public(g) for g in groups]

# ----------------- Posts -----------------
@app.post("/api/groups/{group_id}/posts")
def create_post(group_id: str, post: Post):
    if group_id != post.group_id:
        raise HTTPException(status_code=400, detail="Group ID mismatch")
    pid = create_document("post", post)
    return {"id": pid}

@app.get("/api/groups/{group_id}/posts")
def list_posts(group_id: str, limit: int = 50):
    posts = get_documents("post", {"group_id": group_id}, limit)
    return [to_public(p) for p in posts]

# ----------------- Comments -----------------
@app.post("/api/posts/{post_id}/comments")
def create_comment(post_id: str, comment: Comment):
    if post_id != comment.post_id:
        raise HTTPException(status_code=400, detail="Post ID mismatch")
    cid = create_document("comment", comment)
    return {"id": cid}

@app.get("/api/posts/{post_id}/comments")
def list_comments(post_id: str, limit: int = 50):
    comments = get_documents("comment", {"post_id": post_id}, limit)
    return [to_public(c) for c in comments]

# ----------------- Likes -----------------
@app.post("/api/posts/{post_id}/likes")
def like_post(post_id: str, like: Like):
    if post_id != like.post_id:
        raise HTTPException(status_code=400, detail="Post ID mismatch")
    lid = create_document("like", like)
    return {"id": lid}

@app.get("/api/posts/{post_id}/likes")
def list_likes(post_id: str, limit: int = 100):
    likes = get_documents("like", {"post_id": post_id}, limit)
    return [to_public(l) for l in likes]

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
