import aiohttp, logging, openpyxl # type: ignore

from aiogram import types, F, Router  # type: ignore
from aiogram.filters import Command # type: ignore
from aiogram.fsm.context import FSMContext # type: ignore
from aiogram.fsm.state import State, StatesGroup # type: ignore
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, Message # type: ignore
from datetime import datetime
from io import BytesIO


API_URL = "http://api:8000"
router = Router()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ExpensesGet(StatesGroup):
    waiting_for_title = State()
    waiting_for_date = State()
    waiting_for_amount = State()
    waiting_for_start_date = State()
    waiting_for_end_date = State()

class ExpensesDelete(StatesGroup):
    waiting_for_id = State()

class ExpensesEdit(StatesGroup):
    waiting_for_id = State()
    waiting_for_title = State()
    waiting_for_amount = State()


menu = ReplyKeyboardMarkup( keyboard = [
    [
        KeyboardButton(text = '📝 Додати статтю витрат 📝'),
        KeyboardButton(text = '🗃 Отримати звіт витрат 🗃'),
    ],
    [
        KeyboardButton(text = '🟥 Видалити статтю у списку витрат 🟥'),
        KeyboardButton(text = '🖊 Відредагувати статтю у списку витрат 🖊'),
    ]
    ] ,resize_keyboard=True
)

infos = {}


@router.message(Command('start'))
async def start(message: types.Message):
    await message.answer('Привіт! Обери дію.', reply_markup = menu)

# ================== Add Expenses ==================

@router.message(F.text == '📝 Додати статтю витрат 📝')
async def add_Expenses(message: Message, state: FSMContext):
    infos[message.from_user.id] = {}
    await state.set_state(ExpensesGet.waiting_for_title)
    await message.answer('✏️ Введи назву статті витрат:')

@router.message(ExpensesGet.waiting_for_title)
async def waiting_for_title(message: Message, state: FSMContext):
    info = infos[message.from_user.id]
    info['title'] = str(message.text)
    await state.set_state(ExpensesGet.waiting_for_date)
    await message.answer('🗓 Введи дату витрат у форматі DD.MM.YYYY:')

@router.message(ExpensesGet.waiting_for_date)
async def waiting_for_date(message: Message, state: FSMContext):
    info = infos[message.from_user.id]
    try:
        parsed_date = datetime.strptime(message.text, '%d.%m.%Y').date()
        info['date'] = parsed_date
        info['date'] = str(message.text)
        await state.set_state(ExpensesGet.waiting_for_amount)
        await message.answer('💳 Введи суму витрат у грн:')
    except ValueError:
        await message.answer('''
                             ⚠️ Невірно вказана дата.\n\n🗓 Введи дату витрат у форматі DD.MM.YYYY:
                             ''')
        await state.set_state(ExpensesGet.waiting_for_date)

@router.message(ExpensesGet.waiting_for_amount)
async def waiting_for_amount(message: Message, state: FSMContext):
    info = infos[message.from_user.id]
    try:
        info['amount'] = float(message.text)
        async with aiohttp.ClientSession() as session:
            async with session.post(f'{API_URL}/expenses/', json=info) as response:
                if response.status == 200:
                    await message.answer(f'''
                        ✅ Стаття витрат додана:\n\n ✏️ {info['title']},\n 🗓 {info['date']},\n 💳 {info['amount']} грн.
                        ''', reply_markup = menu)
                else:
                    await message.answer('⚠️ Сталася помилка під час додавання статті витрат.\nСпробуйте ще раз.', reply_markup = menu)
        del info
        await state.clear()
    except ValueError:
        await message.answer('''
                             ⚠️ Невірно вказана сума.\n\n💳 Введи суму витрат у грн:
                             ''')
        await state.set_state(ExpensesGet.waiting_for_amount)

# ================== Get Expenses ==================

@router.message(F.text == '🗃 Отримати звіт витрат 🗃')
async def get_Expenses(message: Message, state: FSMContext):
    infos[message.from_user.id] = {}
    await state.set_state(ExpensesGet.waiting_for_start_date)
    await message.answer('🗓 Введи дату початку в форматі DD.MM.YYYY:')

@router.message(ExpensesGet.waiting_for_start_date)
async def waiting_for_start_date(message: Message, state: FSMContext):
    info = infos[message.from_user.id]
    try:
        parsed_date = datetime.strptime(message.text, '%d.%m.%Y').date()
        info['start_date'] = parsed_date
        info['start_date'] = str(message.text)
        await message.answer('🗓 Введи дату кінця в форматі DD.MM.YYYY:')
        await state.set_state(ExpensesGet.waiting_for_end_date)
    except ValueError:
        await message.answer('''
                             ⚠️ Невірно вказана дата.\n\n🗓 Введи дату початку в форматі DD.MM.YYYY:
                             ''')
        await state.set_state(ExpensesGet.waiting_for_start_date)

@router.message(ExpensesGet.waiting_for_end_date)
async def waiting_for_end_date(message: Message, state: FSMContext):
    info = infos[message.from_user.id]
    try:
        parsed_date = datetime.strptime(message.text, '%d.%m.%Y').date()
        info['end_date'] = parsed_date
        info['end_date'] = str(message.text)
        await message.answer('⏳ Зачекайте, формується звіт...')
        async with aiohttp.ClientSession() as session:
            async with session.get(f'{API_URL}/expenses/', json=info) as response:
                if response.status == 200:
                    expenses = await response.json()
                    wb = openpyxl.Workbook()
                    ws = wb.active
                    ws.append(['ID','Назва', 'Дата', 'Сума (грн)', 'Сума (USD)']) # type: ignore

                    total_expenses = 0
                    for expense in expenses['context']:
                        ws.append([expense['id'], expense['title'], expense['date'], expense['amount_uah'], expense['amount_usd']]) # type: ignore
                        total_expenses += expense['amount_uah']

                    file_stream = BytesIO()
                    wb.save(file_stream)
                    file_stream.seek(0)

                    await message.answer_document(types.BufferedInputFile(file_stream.getvalue(), filename='expenses_report.xlsx'))
                    await message.answer(f'✅ Звіт сформовано та відправлено! \n\n🪙 Загальна сума {total_expenses}', reply_markup = menu)

                elif response.status == 404:
                    await message.answer('🪧 За вказаний період витрат не знайдено.')
                else:
                    await message.answer('⚠️ Сталася помилка під час отримання звіту.\nСпробуйте ще раз.', reply_markup = menu)
        del info
        await state.clear()
    except ValueError:
        await message.answer('''
                             ⚠️ Невірно вказана дата.\n\n🗓 Введи дату кінця в форматі DD.MM.YYYY:
                             ''')
        await state.set_state(ExpensesGet.waiting_for_end_date)

# ================== Delete Expense ==================

@router.message(F.text == '🟥 Видалити статтю у списку витрат 🟥')
async def delete_Expenses(message: Message, state: FSMContext):
    async with aiohttp.ClientSession() as session:
        async with session.get(f'{API_URL}/all_expenses/') as response:
            if response.status == 200:
                expenses = await response.json()

                wb = openpyxl.Workbook()
                ws = wb.active
                ws.append(['ID','Назва', 'Дата', 'Сума (грн)', 'Сума (USD)']) # type: ignore

                for expense in expenses['context']:
                    ws.append([expense['id'], expense['title'], expense['date'], expense['amount_uah'], expense['amount_usd']]) # type: ignore

                file_stream = BytesIO()
                wb.save(file_stream)
                file_stream.seek(0)

                await message.answer_document(types.BufferedInputFile(file_stream.getvalue(), filename='expenses_report.xlsx'))
            elif response.status == 404:
                await message.answer('🪧 За вказаний період витрат не знайдено.')
            else:
                await message.answer('⚠️ Сталася помилка під час отримання звіту.\nСпробуйте ще раз.', reply_markup = menu)
                await state.clear()
    await message.answer('🏷 Введи ID статті витрат для видалення:')
    await state.set_state(ExpensesDelete.waiting_for_id)

@router.message(ExpensesDelete.waiting_for_id)
async def waiting_for_id(message: Message, state: FSMContext):
    async with aiohttp.ClientSession() as session:
        async with session.delete(f'{API_URL}/expenses/{message.text}') as response:
            if response.status == 200:
                await message.answer('✅ Статтю витрат видалено!', reply_markup = menu)
            else:
                await message.answer('⚠️ Сталася помилка під час видалення статті витрат.\nСпробуйте ще раз.' , reply_markup = menu)
    await state.clear()

# ================== Edit Expense ==================

@router.message(F.text == '🖊 Відредагувати статтю у списку витрат 🖊')
async def edit_Expenses(message: Message, state: FSMContext):
    infos[message.from_user.id] = {}
    async with aiohttp.ClientSession() as session:
        async with session.get(f'{API_URL}/all_expenses/') as response:
            if response.status == 200:
                expenses = await response.json()
                wb = openpyxl.Workbook()
                ws = wb.active
                ws.append(['ID','Назва', 'Дата', 'Сума (грн)', 'Сума (USD)']) # type: ignore

                for expense in expenses['context']:
                    ws.append([expense['id'], expense['title'], expense['date'], expense['amount_uah'], expense['amount_usd']]) # type: ignore

                file_stream = BytesIO()
                wb.save(file_stream)
                file_stream.seek(0)

                await message.answer_document(types.BufferedInputFile(file_stream.getvalue(), filename="expenses_report.xlsx"))
            elif response.status == 404:
                await message.answer('🪧 За вказаний період витрат не знайдено.')
            else:
                await message.answer('⚠️ Сталася помилка під час отримання звіту.\nСпробуйте ще раз.', reply_markup = menu)
                await state.clear()
    await message.answer('🏷 Введи ID статті витрат для редагування:')
    await state.set_state(ExpensesEdit.waiting_for_id)

@router.message(ExpensesEdit.waiting_for_id)
async def waiting_for_edit_id(message: Message, state: FSMContext):
    info = infos[message.from_user.id]
    try:
        info['id'] = int(message.text)
        async with aiohttp.ClientSession() as session:
            async with session.get(f'{API_URL}/expenses/{message.text}', json=info) as response:
                if response.status == 200:
                    expenses = await response.json()
                    expense = expenses['context']
                    await message.answer(f'''
                        📋 Вибрана стаття витрат:\n\n ✏️ {expense['title']},\n 🗓 {expense['date']},\n 💳 {expense['amount_uah']} грн.,\n 💵 {expense['amount_usd']} $.
                        ''')
                    await message.answer('✏️ Введи нову назву статті витрат:')
                    await state.set_state(ExpensesEdit.waiting_for_title)
                else:
                    await message.answer('⚠️ Сталася помилка під час отримання статті витрат.\nСпробуйте ще раз.', reply_markup = menu)
                    del info
                    await state.clear()
    except ValueError:
        await message.answer('''
                             ⚠️ Невірно вказане ID.\n\n🏷 Введи ID статті витрат для редагування:
                             ''')
        await state.set_state(ExpensesEdit.waiting_for_id)

@router.message(ExpensesEdit.waiting_for_title)
async def waiting_for_edit_title(message: Message, state: FSMContext):
    info = infos[message.from_user.id]
    info['title'] = str(message.text)
    await message.answer('Введи нову суму витрат у гривнях:')
    await state.set_state(ExpensesEdit.waiting_for_amount)

@router.message(ExpensesEdit.waiting_for_amount)
async def waiting_for_edit_amount(message: Message, state: FSMContext):
    info = infos[message.from_user.id]
    info['amount'] = float(message.text)
    async with aiohttp.ClientSession() as session:
        async with session.put(f'{API_URL}/expenses/{info["id"]}', json=info) as response:
            if response.status == 200:
                await message.answer('✅ Статтю витрат відредаговано!', reply_markup = menu)
            else:
                await message.answer('⚠️ Сталася помилка під час редагування статті витрат.\nСпробуйте ще раз.', reply_markup = menu)
    await state.clear()
    del info
