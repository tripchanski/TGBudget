import requests, logging

from pydantic import BaseModel # type: ignore
from fastapi import FastAPI, Depends, HTTPException # type: ignore
from sqlalchemy import create_engine, Column, Integer, String, Float, Date # type: ignore
from sqlalchemy.orm import sessionmaker, declarative_base, Session # type: ignore
from datetime import datetime

# ================== LOGGING ==================

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s',
                    handlers=[logging.StreamHandler()])

logger = logging.getLogger(__name__)

# ================== DATABASE ==================

DATABASE_URL = 'sqlite:///./expenses.db'
engine = create_engine(DATABASE_URL, connect_args={'check_same_thread': False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

class Expense(Base):
    __tablename__ = 'expenses'
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    amount_uah = Column(Float)
    amount_usd = Column(Float)
    date = Column(Date)

Base.metadata.create_all(bind=engine)
# ================== MODELS ==================

class ExpenseCreate(BaseModel):
    title: str
    date: str
    amount: float

class ExpenseGet(BaseModel):
    start_date: str
    end_date: str

class ExpenseEdit(BaseModel):
    title: str
    amount: float
    id: int

# ================== FASTAPI ==================

app = FastAPI()

# ================== FUNCTIONS ==================

def get_usd_exchange_rate():
    response = requests.get('https://bank.gov.ua/NBUStatService/v1/statdirectory/exchange?valcode=USD&json')
    if response.status_code == 200:
        return response.json()[0]['rate']
    raise HTTPException(status_code=500, detail='Unable to fetch exchange rate')

# ================== GET ==================

@app.get('/expenses/')
def get_expenses_by_date(expense: ExpenseGet, db: Session = Depends(get_db)):
    try:
        start_date = datetime.strptime(expense.start_date, '%d.%m.%Y')
        end_date = datetime.strptime(expense.end_date, '%d.%m.%Y')
    except ValueError:
        raise HTTPException(status_code=400, detail='Invalid date format. Use DD.MM.YYYY.')

    expenses = db.query(Expense).filter(Expense.date >= start_date, Expense.date <= end_date).all()
    if not expenses:
        raise HTTPException(status_code=404, detail='No expenses found for the given period.')

    return {'context': expenses}

@app.get('/all_expenses/')
def get_all_expenses(db: Session = Depends(get_db)):
    expenses = db.query(Expense).all()
    if not expenses:
        raise HTTPException(status_code=404, detail='No expenses found for the given period.')
    return {'context': expenses}

@app.get('/expenses/{expense_id}')
def get_expense(expense_id: int, db: Session = Depends(get_db)):
    expense = db.query(Expense).filter(Expense.id == expense_id).first()
    if not expense:
        raise HTTPException(status_code=404, detail='Expense not found')
    return {'context': expense}

# ================== POST ==================

@app.post('/expenses/')
def add_expense(expense: ExpenseCreate, db: Session = Depends(get_db)):
    logger.info(f'Adding expense: {expense.title}, {expense.amount}')
    exchange_rate = get_usd_exchange_rate()
    logger.info(f'Exchange rate: {exchange_rate}')
    date = datetime.strptime(expense.date, '%d.%m.%Y')
    new_expense = Expense(
        title=expense.title,
        amount_uah=expense.amount,
        amount_usd=round(expense.amount / exchange_rate, 2),
        date=date
    )
    logger.info(f'New expense: {new_expense}')
    db.add(new_expense)
    db.commit()
    db.refresh(new_expense)
    return new_expense

# ================== DELETE ==================

@app.delete('/expenses/{expense_id}')
def delete_expense(expense_id: int, db: Session = Depends(get_db)):
    expense = db.query(Expense).filter(Expense.id == expense_id).first()
    if not expense:
        raise HTTPException(status_code=404, detail='Expense not found')
    db.delete(expense)
    db.commit()
    return expense

# ================== PUT ==================

@app.put('/expenses/{expense_id}')
def update_expense(expense_id: int, new_data: ExpenseEdit, db: Session = Depends(get_db)):
    expense = db.query(Expense).filter(Expense.id == expense_id).first()
    if not expense:
        raise HTTPException(status_code=404, detail='Expense not found')
    exchange_rate = get_usd_exchange_rate()
    expense.title = new_data.title
    expense.amount_uah = new_data.amount
    expense.amount_usd = round(new_data.amount / exchange_rate, 2)
    db.commit()
    db.refresh(expense)
    return expense
