"""
Database Schemas for Dental Clinic Suite

Each Pydantic model maps to a MongoDB collection using the lowercase
of the class name as the collection name.

Examples:
- Patient -> "patient"
- Doctor -> "doctor"

These schemas will be exposed via the /schema endpoint and are used by
the database viewer for validation and basic CRUD.
"""

from typing import Optional, List, Literal, Dict, Any
from pydantic import BaseModel, Field
from datetime import date, datetime

# ---------------------------------------------------------------------
# Core People
# ---------------------------------------------------------------------

class Receptionist(BaseModel):
    name: str = Field(..., description="Full name")
    email: str = Field(..., description="Work email")
    phone: Optional[str] = Field(None, description="Contact phone")
    shift: Literal["morning", "evening", "night"] = Field("morning")
    is_active: bool = Field(True)

class Doctor(BaseModel):
    name: str = Field(..., description="Full name")
    email: str = Field(..., description="Work email")
    phone: Optional[str] = Field(None)
    specialization: Optional[str] = Field(None, description="e.g., Orthodontist, Endodontist")
    license_no: Optional[str] = Field(None)
    is_active: bool = Field(True)

class Patient(BaseModel):
    first_name: str
    last_name: str
    date_of_birth: Optional[date] = Field(None)
    gender: Optional[Literal["male", "female", "other"]] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    allergies: List[str] = Field(default_factory=list)
    medical_history: Optional[str] = None
    insurance_provider: Optional[str] = None
    insurance_member_id: Optional[str] = None
    balance: float = Field(0, ge=0, description="Current balance")
    notes: Optional[str] = None

# ---------------------------------------------------------------------
# Clinical & Scheduling
# ---------------------------------------------------------------------

class Procedure(BaseModel):
    code: str = Field(..., description="Internal or insurance code")
    name: str
    description: Optional[str] = None
    default_duration_min: int = Field(30, ge=5, le=480)
    base_fee: float = Field(..., ge=0)

class Appointment(BaseModel):
    patient_id: str = Field(..., description="Reference to patient _id")
    doctor_id: str = Field(..., description="Reference to doctor _id")
    start_time: datetime = Field(..., description="Appointment start time (UTC)")
    duration_min: int = Field(30, ge=5, le=480)
    procedure_codes: List[str] = Field(default_factory=list)
    status: Literal["scheduled", "checked_in", "in_progress", "completed", "cancelled", "no_show"] = "scheduled"
    room: Optional[str] = None
    notes: Optional[str] = None

# ---------------------------------------------------------------------
# Billing & Reports
# ---------------------------------------------------------------------

class PaymentItem(BaseModel):
    description: str
    amount: float = Field(..., ge=0)
    procedure_code: Optional[str] = None
    appointment_id: Optional[str] = None

class Payment(BaseModel):
    patient_id: str = Field(..., description="Reference to patient _id")
    amount: float = Field(..., ge=0)
    method: Literal["cash", "card", "transfer", "insurance"]
    status: Literal["pending", "paid", "refunded", "failed"] = "paid"
    reference: Optional[str] = None
    date_time: datetime = Field(default_factory=datetime.utcnow)
    items: List[PaymentItem] = Field(default_factory=list)
    notes: Optional[str] = None

class Report(BaseModel):
    type: Literal["daily", "financial", "inventory", "custom"]
    period_start: Optional[date] = None
    period_end: Optional[date] = None
    generated_by: Optional[str] = Field(None, description="User id")
    data: Dict[str, Any] = Field(default_factory=dict)

# ---------------------------------------------------------------------
# Inventory (Consumables)
# ---------------------------------------------------------------------

class Consumable(BaseModel):
    name: str
    unit: Literal["pcs", "ml", "g", "box", "pack", "bottle", "tube"] = "pcs"
    stock_qty: float = Field(0, ge=0)
    reorder_level: float = Field(0, ge=0)
    cost_per_unit: float = Field(0, ge=0)
    vendor: Optional[str] = None
    sku: Optional[str] = None
