from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey
from datetime import datetime
from app.database import Base


class AgeVerification(Base):
    __tablename__ = "age_verifications"

    id = Column(Integer, primary_key=True, index=True)
    sale_id = Column(Integer, ForeignKey("sales.id"), nullable=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=True)
    
    # Verification details
    verification_method = Column(String, default="visual")  # visual, id_scan, manual
    id_type = Column(String, nullable=True)  # drivers_license, passport, state_id
    id_number_last4 = Column(String, nullable=True)  # Last 4 digits only for privacy
    
    # Calculated age at verification
    date_of_birth = Column(DateTime, nullable=True)
    age_at_verification = Column(Integer, nullable=True)
    
    # Result
    verified = Column(Boolean, default=True)
    declined_reason = Column(String, nullable=True)
    
    # Audit
    verified_by = Column(String, default="pos_system")
    verified_at = Column(DateTime, default=datetime.utcnow)
