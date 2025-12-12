from fastapi import FastAPI, HTTPException, Path, Depends
from pydantic import BaseModel
from typing import List, Dict
from datetime import date
from sqlalchemy import Column, Integer, String, Boolean, Date, create_engine, ForeignKey
from sqlalchemy.orm import declarative_base, sessionmaker, relationship, Session

# ------------------ Database Setup ------------------
DATABASE_URL = "sqlite:///./attendance.db"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ------------------ Models ------------------
class StudentORM(Base):
    __tablename__ = "students"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    class_name = Column(String, nullable=False)
    attendance = relationship("AttendanceORM", back_populates="student")

class AttendanceORM(Base):
    __tablename__ = "attendance"
    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id"))
    date = Column(Date, nullable=False)
    status = Column(String, nullable=False)  # Present / Absent
    is_deleted = Column(Boolean, default=False)
    
    student = relationship("StudentORM", back_populates="attendance")

Base.metadata.create_all(bind=engine)

# ------------------ Pydantic Schemas ------------------
class PostStudent(BaseModel):
    name: str
    class_name: str

class Attendance(BaseModel):
    student_id: int
    date: date
    status: str
    is_deleted: bool = False

class ResponseModel(BaseModel):
    request_method: str
    param: dict
    record: str
    data: str



# ------------------ FastAPI App ------------------
app = FastAPI()

# ------------------ STUDENTS ROUTES ------------------
@app.post("/students", response_model=ResponseModel)
def add_student(student: PostStudent, db: Session = Depends(get_db)):
    try:
        existing = db.query(StudentORM).filter(StudentORM.name == student.name).first()
        if existing:
            raise HTTPException(status_code=400, detail="Student already exists")

        db_student = StudentORM(**student.dict())
        db.add(db_student)
        db.commit()
        db.refresh(db_student)
        return ResponseModel(
            request_method="POST",
            param=student.dict(),
            record="Student",
            data="Successfully Added Student."
        )
    except Exception as e:
        return ResponseModel(
            request_method="POST",
            param=student.dict(),
            record="Student",
            data=f"Error occurred: {str(e)}"
        )

@app.get("/students", response_model=List[PostStudent])
def get_students(db: Session = Depends(get_db)):
    students = db.query(StudentORM).all()
    return [PostStudent( name=s.name, class_name=s.class_name) for s in students]

# ------------------ ATTENDANCE ROUTES ------------------

def attendance_isValid(data:dict):
    is_valid:bool
    ## below line you add check for attendance data
    """
        check if these variable exist in dictionary     
        student_id: int
        date: date
        status: str
    """
    if x=="":
        is_valid= True
    else:
        is_valid= False
    return is_valid
    

@app.post("/attendance", response_model=ResponseModel)
def add_attendance(new_attendance_data: dict, db: Session = Depends(get_db)):
    try:
        if not attendance_isValid(new_attendance_data):
            raise HTTPException(status_code=404, detail="Invalid Input Paramters")
        
        student = db.query(StudentORM).filter(StudentORM.id == new_attendance_data.student_id).first()
        if not student:
            raise HTTPException(status_code=404, detail="Student not found")

        db_attendance = AttendanceORM(**new_attendance_data.dict())
        db.add(db_attendance)
        db.commit()
        db.refresh(db_attendance)

        return ResponseModel(
            request_method="POST",
            param=new_attendance_data.dict(),
            record="Attendance",
            data=f"Attendance added successfully for student_id {new_attendance_data.student_id}"
        )
    except Exception as e:
        return ResponseModel(
            request_method="POST",
            param=new_attendance_data.dict(),
            record="Attendance",
            data=f"Error occurred: {str(e)}"
        )

@app.get("/attendance/all", response_model=List[Attendance])
def get_all_attendance(db: Session = Depends(get_db)):
    records = db.query(AttendanceORM).all()
    return [
        Attendance(
            id=a.id,
            student_id=a.student_id,
            date=a.date,
            status=a.status,
            is_deleted=a.is_deleted
        ) for a in records
    ]

@app.get("/attendance/{day_month}", response_model=List[Attendance])
def get_active_attendance(day_month: str = Path(...), db: Session = Depends(get_db)):
    records = db.query(AttendanceORM).filter(AttendanceORM.is_deleted == False).all()
    filtered = [a for a in records if a.date.strftime("%Y-%m-%d").startswith(day_month)]
    return [
        Attendance(
            id=a.id,
            student_id=a.student_id,
            date=a.date,
            status=a.status,
            is_deleted=a.is_deleted
        ) for a in filtered
    ]

@app.get("/attendance/{day_month}/deleted", response_model=List[Attendance])
def get_deleted_attendance(day_month: str = Path(...), db: Session = Depends(get_db)):
    records = db.query(AttendanceORM).filter(AttendanceORM.is_deleted == True).all()
    filtered = [a for a in records if a.date.strftime("%Y-%m-%d").startswith(day_month)]
    return [
        Attendance(
            id=a.id,
            student_id=a.student_id,
            date=a.date,
            status=a.status,
            is_deleted=a.is_deleted
        ) for a in filtered
    ]

@app.delete("/attendance/{attendance_id}")
def delete_attendance(attendance_id: int, db: Session = Depends(get_db)):
    record = db.query(AttendanceORM).filter(AttendanceORM.id == attendance_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Record not found")
    record.is_deleted = True
    db.commit()
    return {"message": "Attendance marked as deleted", "id": attendance_id}

@app.put("/attendance/restore/{attendance_id}")
def restore_attendance(attendance_id: int, db: Session = Depends(get_db)):
    record = db.query(AttendanceORM).filter(AttendanceORM.id == attendance_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Record not found")
    record.is_deleted = False
    db.commit()
    return {"message": "Attendance restored", "id": attendance_id}
