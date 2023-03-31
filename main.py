import logging
import re
import requests
import json

import settings

from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.utils import executor

logging.basicConfig(level=logging.INFO)

BOT_TOKEN = settings.BOT_TOKEN
CREATE_USER_URL = settings.SITE_URL + 'user/create'
SITE_URL = settings.SITE_URL
TELEGRAM_USER_INFO = {}
USER_PHOTO_PATH = ''

bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)


class UserForm(StatesGroup):
    email = State()
    password = State()


@dp.message_handler(commands=['start'])
async def start_command(message: types.Message):
    """
    Логіка при отриманні команди /start
    """

    # Отримуємо данні про користувачя
    TELEGRAM_USER_INFO.update({'name': message.from_user.full_name})
    TELEGRAM_USER_INFO.update({'nickname': message.from_user.username})
    user_photo = await message.from_user.get_profile_photos(limit=1)

    await message.answer(f"Привіт, {TELEGRAM_USER_INFO.get('name')}! \nВведіть свій E-mail:")

    # Якщо користувач має хоч одне фото
    if user_photo.total_count > 0:
        # Отримуємо file id перщої фотографії профілю
        file_id = user_photo.photos[0][-1].file_id

        # Завантажуємо фото профілю
        photo = await bot.get_file(file_id)

        # Зберігаємо у директорії для подальших операцій
        await photo.download(destination_dir=f'media/users/{TELEGRAM_USER_INFO.get("nickname")}')
        global USER_PHOTO_PATH
        USER_PHOTO_PATH = f'media/users/{TELEGRAM_USER_INFO.get("nickname")}/{photo.file_path}'
    else:
        USER_PHOTO_PATH = ''

    await UserForm.email.set()


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

    TELEGRAM_USER_INFO.update({'email': message.text})

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

    TELEGRAM_USER_INFO.update({'password': message.text})

    await message.answer(
        f"Вітаю, {TELEGRAM_USER_INFO.get('name')}!\nВи успішно зареєструвались ✅ \nМожете спробувати увійти у свій "
        f"профіль за посиланням👇 \n{SITE_URL}\nLogin: {TELEGRAM_USER_INFO.get('nickname')}\nPassword: "
        f"{TELEGRAM_USER_INFO.get('password')}")
    if USER_PHOTO_PATH == '':
        response = requests.post(CREATE_USER_URL, data=json.dumps(TELEGRAM_USER_INFO),
                                 headers={'Content-Type': 'application/json'})
    else:
        headers = {'Content-Type': 'application/json'}
        data = json.dumps(TELEGRAM_USER_INFO)
        print(f'TEST {data}')
        files = {'image': open(USER_PHOTO_PATH, 'rb')}
        response = requests.post(CREATE_USER_URL, data=json.loads(data), files=files)
        print(response.status_code)
        print(response.json)

    await state.finish()
    return response.status_code


if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
