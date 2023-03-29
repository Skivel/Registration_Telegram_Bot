import logging
import re

import settings

from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.utils import executor

logging.basicConfig(level=logging.INFO)

BOT_TOKEN = settings.BOT_TOKEN
SITE_URL = settings.SITE_URL

bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)


class UserForm(StatesGroup):
    name = State()
    email = State()
    password = State()


@dp.message_handler(commands=['start'])
async def start_command(message: types.Message):
    """
    Логіка при отриманні команди /start
    """
    await message.answer("Введіть своє ім'я:")
    await UserForm.name.set()


@dp.message_handler(state=UserForm.name)
async def process_name(message: types.Message, state: FSMContext):
    """
    Логіка при введенні імені користувачем
    """

    # Перевірка імені користувачя
    if not re.match("^[a-zA-Z]{3,20}$", message.text):
        await message.answer("🛑 Помилка 🛑 Ім'я не вірне!")
        await message.answer("Повторіть спробу:")
        return False

    async with state.proxy() as data:
        data['name'] = message.text

    await message.reply(f"Привіт, {message.text}! Введіть свій E-mail:")
    await UserForm.next()


@dp.message_handler(state=UserForm.email)
async def process_email(message: types.Message, state: FSMContext):
    """
    Логіка при введенні e-mail користувачем
    """

    # Регулярний вираз для перевірки формату електронної пошти
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    # Перевірка чи відповідає введена електронна пошта регулярному виразу
    if not re.match(pattern, message.text):
        return False

    async with state.proxy() as data:
        data['email'] = message.text

    await message.answer("Тепер введіть пароль:")
    await UserForm.next()


@dp.message_handler(state=UserForm.password)
async def process_password(message: types.Message, state: FSMContext):
    """
    Логіка при введенні паролю користувачя
    """

    # Перевірка на мінімальну довжину
    if len(message.text) < 8:
        await message.answer("🛑 Небезпека 🛑 Пароль повинен містити більше 8-ми символів")
        await message.answer("Повторіть спробу")
        return False

    # Перевірка на наявність цифр
    if not re.search(r'\d', message.text):
        await message.answer("🛑 Небезпека 🛑 Пароль повинен містити хоча б 1 цифру")
        await message.answer("Повторіть спробу")
        return False

    # Перевірка на наявність символів верхнього та нижнього регістрів
    if not re.search(r'[A-Z]', message.text) or not re.search(r'[a-z]', message.text):
        await message.answer(
            "🛑 Небезпечний пароль 🛑\nПароль повинен містити хоча б 1 букву верхнього та нижнього реєстру (А-а)")
        await message.answer("Повторіть спробу")
        return False

    # Перевірка на наявність спеціальних символів
    if not re.search(r'[!@#$%^&*()_+]', message.text):
        await message.answer("🛑 Небезпека 🛑 Пароль повинен містити хоча б 1 спец символ (!@#$%^&*()_+)")
        await message.answer("Повторіть спробу")
        return False

    async with state.proxy() as data:
        data['password'] = message.text

    await message.answer(
        f"Вітаю, {data.get('name')}!\nВи успішно зареєструвались ✅\nМожете спробувати увійти у свій профіль за посиланням👇\n{SITE_URL}")
    await state.finish()


if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
