from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional, List
from pydantic import BaseModel
from datetime import datetime

from ...core.database import get_db
from ...core.security import get_current_user, require_roles
from ...models.ic import ICSession, ICVote, ICSessionStatus, ICDecision
from ...models.user import User

router = APIRouter()


class ICSessionCreate(BaseModel):
    title: str
    session_date: datetime
    project_id: Optional[int] = None
    agenda: Optional[str] = None
    quorum_required: int = 3
    attendees: Optional[List[int]] = []
    documents: Optional[List[str]] = []


class ICSessionUpdate(BaseModel):
    title: Optional[str] = None
    session_date: Optional[datetime] = None
    status: Optional[ICSessionStatus] = None
    agenda: Optional[str] = None
    minutes: Optional[str] = None
    decision: Optional[ICDecision] = None
    decision_notes: Optional[str] = None
    conditions: Optional[str] = None
    quorum_met: Optional[bool] = None
    attendees: Optional[List[int]] = None


class VoteCreate(BaseModel):
    vote: ICDecision
    rationale: Optional[str] = None
    conditions: Optional[str] = None


@router.get("/")
def list_sessions(
    skip: int = 0,
    limit: int = Query(50, le=200),
    status: Optional[ICSessionStatus] = None,
    project_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = db.query(ICSession)
    if status:
        q = q.filter(ICSession.status == status)
    if project_id:
        q = q.filter(ICSession.project_id == project_id)
    total = q.count()
    items = q.order_by(ICSession.session_date.desc()).offset(skip).limit(limit).all()
    return {"total": total, "items": items}


@router.post("/", status_code=201)
def create_session(
    req: ICSessionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "analyst", "ic_member")),
):
    session = ICSession(
        **req.model_dump(),
        chaired_by_id=current_user.id,
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


@router.get("/{session_id}")
def get_session(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    session = db.query(ICSession).filter(ICSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="IC Session not found")
    return session


@router.put("/{session_id}")
def update_session(
    session_id: int,
    req: ICSessionUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "analyst", "ic_member")),
):
    session = db.query(ICSession).filter(ICSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="IC Session not found")
    for field, value in req.model_dump(exclude_unset=True).items():
        setattr(session, field, value)
    db.commit()
    db.refresh(session)
    return session


@router.delete("/{session_id}", status_code=204)
def delete_session(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin")),
):
    session = db.query(ICSession).filter(ICSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="IC Session not found")
    db.delete(session)
    db.commit()


@router.post("/{session_id}/vote", status_code=201)
def cast_vote(
    session_id: int,
    req: VoteCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "ic_member")),
):
    session = db.query(ICSession).filter(ICSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="IC Session not found")
    if session.status == ICSessionStatus.completed:
        raise HTTPException(status_code=400, detail="Session already completed")

    existing_vote = db.query(ICVote).filter(
        ICVote.session_id == session_id,
        ICVote.voter_id == current_user.id
    ).first()
    if existing_vote:
        existing_vote.vote = req.vote
        existing_vote.rationale = req.rationale
        existing_vote.conditions = req.conditions
        db.commit()
        db.refresh(existing_vote)
        return existing_vote

    vote = ICVote(
        session_id=session_id,
        voter_id=current_user.id,
        **req.model_dump(),
    )
    db.add(vote)
    db.commit()
    db.refresh(vote)
    return vote


@router.get("/{session_id}/votes")
def get_votes(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    session = db.query(ICSession).filter(ICSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="IC Session not found")
    votes = db.query(ICVote).filter(ICVote.session_id == session_id).all()
    summary = {
        "approved": sum(1 for v in votes if v.vote == ICDecision.approved),
        "rejected": sum(1 for v in votes if v.vote == ICDecision.rejected),
        "deferred": sum(1 for v in votes if v.vote == ICDecision.deferred),
        "conditional": sum(1 for v in votes if v.vote == ICDecision.conditional),
        "total_votes": len(votes),
        "quorum_required": session.quorum_required,
        "quorum_met": len(votes) >= session.quorum_required,
    }
    return {"votes": votes, "summary": summary}


@router.post("/{session_id}/finalize")
def finalize_session(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "analyst")),
):
    session = db.query(ICSession).filter(ICSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="IC Session not found")
    votes = db.query(ICVote).filter(ICVote.session_id == session_id).all()
    session.quorum_met = len(votes) >= session.quorum_required
    session.status = ICSessionStatus.completed

    if votes:
        vote_counts = {}
        for v in votes:
            vote_counts[v.vote] = vote_counts.get(v.vote, 0) + 1
        majority_decision = max(vote_counts, key=vote_counts.get)
        session.decision = majority_decision

    db.commit()
    db.refresh(session)
    return session
