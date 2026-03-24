from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional
from pydantic import BaseModel

from ...core.database import get_db
from ...core.security import get_current_user, require_roles
from ...models.integration import Integration
from ...models.user import User

router = APIRouter()

AVAILABLE_INTEGRATIONS = [
    {"type": "azure_ad_b2c",   "name": "Azure AD B2C",        "description": "Single Sign-On via Microsoft Azure AD B2C"},
    {"type": "sharepoint",     "name": "SharePoint",           "description": "Document management via Microsoft SharePoint"},
    {"type": "outlook",        "name": "Outlook / Exchange",   "description": "Email notifications and calendar sync"},
    {"type": "teams",          "name": "Microsoft Teams",      "description": "Deal room notifications via Teams"},
    {"type": "salesforce",     "name": "Salesforce CRM",       "description": "Investor CRM sync"},
    {"type": "hubspot",        "name": "HubSpot",              "description": "Marketing and investor pipeline"},
    {"type": "docusign",       "name": "DocuSign",             "description": "E-signatures for deal documents"},
    {"type": "bloomberg",      "name": "Bloomberg",            "description": "Market data and financial indices"},
    {"type": "stripe",         "name": "Stripe",               "description": "Payment processing for fees"},
    {"type": "aws_s3",         "name": "AWS S3",               "description": "Document storage on Amazon S3"},
    {"type": "azure_blob",     "name": "Azure Blob Storage",   "description": "Document storage on Azure Blob"},
]


class IntegrationCreate(BaseModel):
    integration_type: str
    name: str
    config: Optional[dict] = {}


class IntegrationUpdate(BaseModel):
    is_enabled: Optional[bool] = None
    config: Optional[dict] = None
    status: Optional[str] = None


@router.get("/available")
def list_available(current_user: User = Depends(get_current_user)):
    return AVAILABLE_INTEGRATIONS


@router.get("/")
def list_integrations(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin")),
):
    return db.query(Integration).all()


@router.post("/", status_code=201)
def create_integration(
    req: IntegrationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin")),
):
    existing = db.query(Integration).filter(Integration.integration_type == req.integration_type).first()
    if existing:
        raise HTTPException(status_code=400, detail="Integration already configured")
    integration = Integration(**req.model_dump())
    db.add(integration)
    db.commit()
    db.refresh(integration)
    return integration


@router.get("/{integration_id}")
def get_integration(
    integration_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin")),
):
    integration = db.query(Integration).filter(Integration.id == integration_id).first()
    if not integration:
        raise HTTPException(status_code=404, detail="Integration not found")
    return integration


@router.put("/{integration_id}")
def update_integration(
    integration_id: int,
    req: IntegrationUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin")),
):
    integration = db.query(Integration).filter(Integration.id == integration_id).first()
    if not integration:
        raise HTTPException(status_code=404, detail="Integration not found")
    for field, value in req.model_dump(exclude_unset=True).items():
        setattr(integration, field, value)
    db.commit()
    db.refresh(integration)
    return integration


@router.post("/{integration_id}/test")
def test_integration(
    integration_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin")),
):
    integration = db.query(Integration).filter(Integration.id == integration_id).first()
    if not integration:
        raise HTTPException(status_code=404, detail="Integration not found")
    # Placeholder: in production call the actual integration test
    return {"status": "ok", "message": f"Integration '{integration.name}' test endpoint reached. Configure secrets in environment variables."}


@router.delete("/{integration_id}", status_code=204)
def delete_integration(
    integration_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin")),
):
    integration = db.query(Integration).filter(Integration.id == integration_id).first()
    if not integration:
        raise HTTPException(status_code=404, detail="Integration not found")
    db.delete(integration)
    db.commit()
