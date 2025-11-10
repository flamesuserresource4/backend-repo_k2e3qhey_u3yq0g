"""
Database Schemas for Campus Social App

Each Pydantic model represents a MongoDB collection. The collection name is the
lowercased class name. Example: class User -> "user" collection.
"""

from pydantic import BaseModel, Field
from typing import Optional, Literal

# Core user with simple role-based access
class User(BaseModel):
    name: str = Field(..., description="Full name")
    email: str = Field(..., description="Email address")
    avatar_url: Optional[str] = Field(None, description="Profile image URL")
    role: Literal["user", "moderator", "admin"] = Field("user", description="Role for permissions")

class Group(BaseModel):
    name: str = Field(..., description="Group name")
    description: Optional[str] = Field(None, description="What this group is about")
    created_by: str = Field(..., description="User ID of creator")

class Post(BaseModel):
    group_id: str = Field(..., description="Target group ID")
    author_id: str = Field(..., description="User ID of author")
    content: str = Field(..., description="Post text content")

class Comment(BaseModel):
    post_id: str = Field(..., description="Post ID being commented on")
    author_id: str = Field(..., description="User ID of commenter")
    content: str = Field(..., description="Comment text")

class Like(BaseModel):
    post_id: str = Field(..., description="Post that was liked")
    user_id: str = Field(..., description="User who liked the post")
