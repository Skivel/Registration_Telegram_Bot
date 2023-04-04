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

    # Отримуємо список зареєстрованих користувачів
    response = requests.get(f"{SITE_URL}api/v1/users")
    data = json.loads(response.text)
    register_users = [item['user_nickname'] for item in data]

    # Отримуємо данні про користувачя
    TELEGRAM_USER_INFO.update({f'{message.from_user.id}': {}})
    TELEGRAM_USER_INFO[f'{message.from_user.id}']['name'] = message.from_user.full_name
    TELEGRAM_USER_INFO[f'{message.from_user.id}']['nickname'] = message.from_user.username
    user_photo = await message.from_user.get_profile_photos(limit=1)

    if TELEGRAM_USER_INFO.get(f'{message.from_user.id}').get('nickname') in register_users:
        await message.answer(
            f"Привіт, {TELEGRAM_USER_INFO.get(f'{message.from_user.id}').get('name')}\nВи вже зареєстровані!"
            f"\nУвійдіть у свій профіль за посиланням👇\n{SITE_URL}")
    else:
        await message.answer(
            f"Привіт, {TELEGRAM_USER_INFO.get(f'{message.from_user.id}').get('name')}! \nВведіть свій E-mail:")

        # Якщо користувач має хоч одне фото
        if user_photo.total_count > 0:
            # Отримуємо file id першої фотографії профілю
            file_id = user_photo.photos[0][-1].file_id

            # Завантажуємо фото профілю
            photo = await bot.get_file(file_id)

            # Зберігаємо у директорії для подальших операцій
            await photo.download(destination_dir=f'media/users/{TELEGRAM_USER_INFO.get(f"{message.from_user.id}").get("nickname")}')
            global USER_PHOTO_PATH
            USER_PHOTO_PATH = f'media/users/{TELEGRAM_USER_INFO.get(f"{message.from_user.id}").get("nickname")}/{photo.file_path}'
        else:
            USER_PHOTO_PATH = ''

        await UserForm.email.set()

    print(TELEGRAM_USER_INFO)


@dp.message_handler(state=UserForm.email)
async def process_email(message: types.Message):
    """
    Логіка при введенні e-mail користувачем
    """

    # Регулярний вираз для перевірки формату електронної пошти
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    # Перевірка чи відповідає введена електронна пошта регулярному виразу
    if not re.match(pattern, message.text):
        await message.answer("Email не коректний, повторіть спробу:")
        return False

    TELEGRAM_USER_INFO[f'{message.from_user.id}']['email'] = message.text

    await message.answer("Тепер введіть пароль:")
    await UserForm.next()


@dp.message_handler(state=UserForm.password)
async def process_password(message: types.Message, state: FSMContext):
    """
    Логіка при введенні паролю користувачя
    """

    # Перевірка на мінімальну довжину
    if len(message.text) < 8 or len(message.text) > 30:
        await message.answer("🛑 Небезпека 🛑 Пароль повинен містити від 8-ми до 30-ти символів")
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

    TELEGRAM_USER_INFO[f'{message.from_user.id}']['password'] = message.text

    await message.answer(
        f"Вітаю, {TELEGRAM_USER_INFO.get(f'{message.from_user.id}').get('name')}!\nВи успішно зареєструвались ✅ \nМожете спробувати увійти у свій "
        f"профіль за посиланням👇 \n{SITE_URL}\nLogin: {TELEGRAM_USER_INFO.get(f'{message.from_user.id}').get('nickname')}\nPassword: "
        f"{TELEGRAM_USER_INFO.get(f'{message.from_user.id}').get('password')}")

    data = json.dumps(TELEGRAM_USER_INFO.get(f'{message.from_user.id}'))

    if USER_PHOTO_PATH == '':
        response = requests.post(CREATE_USER_URL, data=json.loads(data))
    else:
        files = {'image': open(USER_PHOTO_PATH, 'rb')}
        response = requests.post(CREATE_USER_URL, data=json.loads(data), files=files)
        print(response.status_code)

    await state.finish()
    TELEGRAM_USER_INFO.pop(f'{message.from_user.id}')
    print(TELEGRAM_USER_INFO)
    return response.status_code


if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
