from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from datetime import datetime, timedelta

from app.database import get_db
from app.models.employee import Employee, ROLE_PERMISSIONS, hash_pin, verify_pin

router = APIRouter(prefix="/employees", tags=["employees"])

# Lock settings
MAX_FAILED_ATTEMPTS = 5
LOCKOUT_DURATION_MINUTES = 30


# Schemas
class EmployeeCreate(BaseModel):
    first_name: str
    last_name: str
    employee_number: Optional[str] = None
    pin: str  # 4-6 digit PIN
    phone: Optional[str] = None
    email: Optional[str] = None
    role: str = "cashier"
    hourly_rate: Optional[float] = None
    alcohol_certified: bool = False
    certification_expiry: Optional[datetime] = None


class EmployeeUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    role: Optional[str] = None
    hourly_rate: Optional[float] = None
    alcohol_certified: Optional[bool] = None
    certification_expiry: Optional[datetime] = None
    is_active: Optional[bool] = None
    permissions: Optional[Dict[str, Any]] = None


class EmployeeResponse(BaseModel):
    id: int
    first_name: str
    last_name: str
    employee_number: str
    phone: Optional[str]
    email: Optional[str]
    role: str
    hourly_rate: Optional[float]
    alcohol_certified: bool
    certification_expiry: Optional[datetime]
    is_active: bool
    last_login: Optional[datetime]
    hire_date: datetime
    created_at: datetime

    class Config:
        from_attributes = True


class LoginRequest(BaseModel):
    employee_number: str
    pin: str


class LoginResponse(BaseModel):
    success: bool
    employee_id: Optional[int] = None
    employee_name: Optional[str] = None
    role: Optional[str] = None
    permissions: Optional[Dict[str, Any]] = None
    message: str


class ChangePinRequest(BaseModel):
    current_pin: str
    new_pin: str


def generate_employee_number(db: Session) -> str:
    """Generate next employee number"""
    count = db.query(Employee).count()
    return f"E{count + 1:03d}"


def get_employee_permissions(employee: Employee) -> Dict[str, Any]:
    """Get effective permissions for an employee"""
    base_perms = ROLE_PERMISSIONS.get(employee.role, ROLE_PERMISSIONS["cashier"]).copy()
    if employee.permissions:
        base_perms.update(employee.permissions)
    return base_perms


# Routes
@router.get("", response_model=List[EmployeeResponse])
def list_employees(
    active_only: bool = True,
    role: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """List all employees"""
    query = db.query(Employee)
    
    if active_only:
        query = query.filter(Employee.is_active == True)
    
    if role:
        query = query.filter(Employee.role == role)
    
    return query.order_by(Employee.last_name, Employee.first_name).all()


@router.get("/roles")
def list_roles():
    """Get available roles and their permissions"""
    return ROLE_PERMISSIONS


@router.get("/{employee_id}", response_model=EmployeeResponse)
def get_employee(employee_id: int, db: Session = Depends(get_db)):
    """Get a specific employee"""
    employee = db.query(Employee).filter(Employee.id == employee_id).first()
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    return employee


@router.post("", response_model=EmployeeResponse)
def create_employee(data: EmployeeCreate, db: Session = Depends(get_db)):
    """Create a new employee"""
    # Validate PIN
    if not data.pin.isdigit() or len(data.pin) < 4 or len(data.pin) > 6:
        raise HTTPException(status_code=400, detail="PIN must be 4-6 digits")
    
    # Validate role
    if data.role not in ROLE_PERMISSIONS:
        raise HTTPException(status_code=400, detail=f"Invalid role. Must be one of: {list(ROLE_PERMISSIONS.keys())}")
    
    # Generate employee number if not provided
    employee_number = data.employee_number or generate_employee_number(db)
    
    # Check for duplicate
    existing = db.query(Employee).filter(Employee.employee_number == employee_number).first()
    if existing:
        raise HTTPException(status_code=400, detail="Employee number already exists")
    
    employee = Employee(
        first_name=data.first_name,
        last_name=data.last_name,
        employee_number=employee_number,
        pin_hash=hash_pin(data.pin),
        phone=data.phone,
        email=data.email,
        role=data.role,
        hourly_rate=data.hourly_rate,
        alcohol_certified=data.alcohol_certified,
        certification_expiry=data.certification_expiry
    )
    db.add(employee)
    db.commit()
    db.refresh(employee)
    return employee


@router.patch("/{employee_id}", response_model=EmployeeResponse)
def update_employee(employee_id: int, data: EmployeeUpdate, db: Session = Depends(get_db)):
    """Update an employee"""
    employee = db.query(Employee).filter(Employee.id == employee_id).first()
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    update_data = data.model_dump(exclude_unset=True)
    
    if "role" in update_data and update_data["role"] not in ROLE_PERMISSIONS:
        raise HTTPException(status_code=400, detail=f"Invalid role")
    
    for key, value in update_data.items():
        setattr(employee, key, value)
    
    db.commit()
    db.refresh(employee)
    return employee


@router.post("/login", response_model=LoginResponse)
def employee_login(data: LoginRequest, db: Session = Depends(get_db)):
    """Employee login with PIN"""
    employee = db.query(Employee).filter(
        Employee.employee_number == data.employee_number
    ).first()
    
    if not employee:
        return LoginResponse(success=False, message="Invalid employee number or PIN")
    
    if not employee.is_active:
        return LoginResponse(success=False, message="Account is deactivated")
    
    # Check lockout
    if employee.locked_until and employee.locked_until > datetime.utcnow():
        remaining = (employee.locked_until - datetime.utcnow()).seconds // 60
        return LoginResponse(success=False, message=f"Account locked. Try again in {remaining} minutes")
    
    # Verify PIN
    if not verify_pin(data.pin, employee.pin_hash):
        employee.failed_login_attempts += 1
        
        if employee.failed_login_attempts >= MAX_FAILED_ATTEMPTS:
            employee.locked_until = datetime.utcnow() + timedelta(minutes=LOCKOUT_DURATION_MINUTES)
            db.commit()
            return LoginResponse(success=False, message=f"Account locked for {LOCKOUT_DURATION_MINUTES} minutes")
        
        db.commit()
        remaining = MAX_FAILED_ATTEMPTS - employee.failed_login_attempts
        return LoginResponse(success=False, message=f"Invalid PIN. {remaining} attempts remaining")
    
    # Successful login
    employee.failed_login_attempts = 0
    employee.locked_until = None
    employee.last_login = datetime.utcnow()
    db.commit()
    
    return LoginResponse(
        success=True,
        employee_id=employee.id,
        employee_name=f"{employee.first_name} {employee.last_name}",
        role=employee.role,
        permissions=get_employee_permissions(employee),
        message="Login successful"
    )


@router.post("/{employee_id}/change-pin")
def change_pin(employee_id: int, data: ChangePinRequest, db: Session = Depends(get_db)):
    """Change employee PIN"""
    employee = db.query(Employee).filter(Employee.id == employee_id).first()
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    # Verify current PIN
    if not verify_pin(data.current_pin, employee.pin_hash):
        raise HTTPException(status_code=401, detail="Current PIN is incorrect")
    
    # Validate new PIN
    if not data.new_pin.isdigit() or len(data.new_pin) < 4 or len(data.new_pin) > 6:
        raise HTTPException(status_code=400, detail="New PIN must be 4-6 digits")
    
    employee.pin_hash = hash_pin(data.new_pin)
    db.commit()
    
    return {"message": "PIN changed successfully"}


@router.post("/{employee_id}/reset-pin")
def reset_pin(employee_id: int, new_pin: str, db: Session = Depends(get_db)):
    """Admin reset of employee PIN"""
    employee = db.query(Employee).filter(Employee.id == employee_id).first()
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    if not new_pin.isdigit() or len(new_pin) < 4 or len(new_pin) > 6:
        raise HTTPException(status_code=400, detail="PIN must be 4-6 digits")
    
    employee.pin_hash = hash_pin(new_pin)
    employee.failed_login_attempts = 0
    employee.locked_until = None
    db.commit()
    
    return {"message": "PIN reset successfully"}


@router.post("/{employee_id}/unlock")
def unlock_account(employee_id: int, db: Session = Depends(get_db)):
    """Unlock a locked employee account"""
    employee = db.query(Employee).filter(Employee.id == employee_id).first()
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    employee.failed_login_attempts = 0
    employee.locked_until = None
    db.commit()
    
    return {"message": "Account unlocked"}


@router.get("/{employee_id}/permissions")
def get_permissions(employee_id: int, db: Session = Depends(get_db)):
    """Get employee's effective permissions"""
    employee = db.query(Employee).filter(Employee.id == employee_id).first()
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    return {
        "employee_id": employee.id,
        "employee_name": f"{employee.first_name} {employee.last_name}",
        "role": employee.role,
        "permissions": get_employee_permissions(employee)
    }


@router.get("/expiring-certifications")
def expiring_certifications(
    days: int = 30,
    db: Session = Depends(get_db)
):
    """Get employees with certifications expiring soon"""
    cutoff = datetime.utcnow() + timedelta(days=days)
    
    employees = db.query(Employee).filter(
        Employee.is_active == True,
        Employee.alcohol_certified == True,
        Employee.certification_expiry != None,
        Employee.certification_expiry <= cutoff
    ).all()
    
    return [
        {
            "id": e.id,
            "name": f"{e.first_name} {e.last_name}",
            "employee_number": e.employee_number,
            "certification_expiry": e.certification_expiry,
            "days_until_expiry": (e.certification_expiry - datetime.utcnow()).days
        }
        for e in employees
    ]
