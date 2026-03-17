import logging
import asyncio
from typing import Final, Union

from aiogram import Bot, Dispatcher, F, Router
from aiogram.filters import Command
from aiogram.types import (Message, LabeledPrice, PreCheckoutQuery, 
                            ContentType, CallbackQuery, InlineKeyboardMarkup, 
                            InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton,
                            KeyboardButtonRequestUser, KeyboardButtonRequestChat, ReplyKeyboardRemove,
                            FSInputFile)
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.methods import SendGift
import os

# --- НАСТРОЙКИ ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PHOTO_PATH = os.path.join(BASE_DIR, "start.png")
BOT_TOKEN: Final = "8021165557:AAHfkfkZUQrpbHlZDOaE0cl-FKClC8BLNXY"
CHANNEL_ID: Final = "@StarGGamerGIFTS"
SUPPORT_URL: Final = "https://t.me/StarGGamer_official"
GIFT_PRICE: Final = 50 

GIFTS_MENU = {
    "🧸 Новогодний мишка": {"id": "5956217000635139069", "sticker": "CAACAgIAAxkBAAEQl5BpmzgZK--9COG2FEg7wfNuqxSwYgACF5wAAnHUyEhM_w9CoUqiwjoE"}, 
    "🎄 Новогодняя елка": {"id": "5922558454332916696", "sticker": "CAACAgIAAxkBAAEQl45pmzgXbHlGoAit3lZVhdx7iHt5nwACepEAAjByyEgjzOEYl2IJMDoE"},
    "🧸 Мишка влюбленных": {"id": "5800655655995968830", "sticker": "CAACAgIAAxkBAAEQl4BpmzWFPseGIp1ovJpEAafR2R3KjwAC74MAAtmryUiG3BZvmLqUDDoE"}, 
    "💝 Сердце влюбленных": {"id": "5801108895304779062", "sticker": "CAACAgIAAxkBAAEQl4xpmzfpOkSnX3q6HD0lkq8F9HylXgAC0I8AAtL6yEiWRP-UqnQTRDoE"},
    "🧸 Девчачий мишка": {"id": "5866352046986232958", "sticker": "CAACAgIAAxkBAAEQs_5prJZKHlJfF65cV0Bfmrn7ELEOHwAC4p4AAr75YUkVQ46Zb1culjoE" },
    "🧸 Мишка Патрика": {"id": "5893356958802511476", "sticker": "CAACAgIAAxkBAAEQxRJpuX6G2AU8j068gUCfsqa8UgABbvcAAkGYAAJoh9FJ5T__TtIq7_w6BA" }
}

class GiftStates(StatesGroup):
    waiting_for_recipient = State()
    waiting_for_confirmation = State()
    waiting_for_custom_comment = State()

router = Router()

# --- УНИВЕРСАЛЬНАЯ ФУНКЦИЯ ОБНОВЛЕНИЯ ИНТЕРФЕЙСА ---

async def ui_update(event: Union[CallbackQuery, Message], text: str, kb: InlineKeyboardMarkup):
    """
    Безопасно обновляет интерфейс: 
    - Если это кнопка на фото -> edit_caption
    - Если это кнопка на тексте -> edit_text
    - Если это новое сообщение -> answer
    """
    if isinstance(event, CallbackQuery):
        try:
            if event.message.photo:
                await event.message.edit_caption(caption=text, reply_markup=kb, parse_mode="HTML")
            else:
                await event.message.edit_text(text=text, reply_markup=kb, parse_mode="HTML")
        except Exception:
            await event.message.answer(text, reply_markup=kb, parse_mode="HTML")
    else:
        await event.answer(text, reply_markup=kb, parse_mode="HTML")

# --- ЛОГИКА ШАГОВ ---

async def show_privacy_warning(event: Union[Message, CallbackQuery], target_id: str, state: FSMContext):
    await state.update_data(target_id=target_id)
    await state.set_state(GiftStates.waiting_for_confirmation)
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Все верно", callback_data="confirm_privacy")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="open_shop")]
    ])
    
    text = (
        "🔒 <b>Важно:</b> У получателя должны быть правильно настроены параметры конфиденциальности для подарков, иначе подарок не придет.\n\n"
        "Настройки → Конфиденциальность → Подарки:\n"
        "- Кто может отображать подарки в профиле → Любой\n"
        "- Убедитесь, что все типы подарков включены в Принимаемые виды подарков\n"
        "- Что пользователь запустил бота\n\n"
        "⚠️ <b>Важно:</b> если вы отправляете другу, то он обязательно должен запустить бота!"
    )
    await ui_update(event, text, kb)

async def ask_for_comment_ui(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    target_id = data.get("target_id", "Неизвестно")
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Без комментария", callback_data="skip_comment")],
        [InlineKeyboardButton(text="❌ Отменить покупку", callback_data="back_start")]
    ])
    
    text = (
        f"🎁 <b>Получатель:</b> <code>{target_id}</code>\n\n"
        "❗️ <b>Обратите внимание:</b>\n"
        "Комментарий не должен содержать нецензурную лексику, оскорбления, запрещённый контент или ссылки на сторонние ресурсы.\n\n"
        "Максимальная длина комментария: <b>128 символов</b>.\n\n"
        "Если комментарий нарушает правила — сервис оставляет за собой право не отправлять подарок.\n"
        "⚠️ Деньги в этом случае не возвращаются.\n\n"
        "Напишите комментарий, который будет приложен при отправке подарка (можно одну фразу или нажмите кнопку ниже если без комментария):"
    )
    # Сначала переключаем состояние, потом правим интерфейс
    await state.set_state(GiftStates.waiting_for_custom_comment)
    await ui_update(callback, text, kb)

# --- ХЕНДЛЕРЫ ---

@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext, bot: Bot):
    await state.clear()
    builder = InlineKeyboardBuilder()
    builder.button(text="🛒 Магазин", callback_data="open_shop")
    builder.button(text="🆘 Поддержка", url=SUPPORT_URL)
    builder.adjust(2)

    if os.path.exists(PHOTO_PATH):
        await message.answer_photo(photo=FSInputFile(PHOTO_PATH), caption="👋 <b>Добро пожаловать!</b>", reply_markup=builder.as_markup(), parse_mode="HTML")
    else:
        await message.answer("👋 <b>Добро пожаловать!</b>", reply_markup=builder.as_markup(), parse_mode="HTML")

@router.callback_query(F.data == "open_shop")
async def shop_callback(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    builder = InlineKeyboardBuilder()
    for name, data in GIFTS_MENU.items():
        builder.button(text=f"{name} | {GIFT_PRICE}⭐️", callback_data=f"sel_{data['id']}")
    builder.button(text="⬅️ Назад", callback_data="back_start")
    builder.adjust(1)
    await ui_update(callback, "🛒 <b>Магазин подарков:</b>\nВыберите подарок:", builder.as_markup())

@router.callback_query(F.data.startswith("sel_"))
async def sel_target(callback: CallbackQuery, state: FSMContext):
    gift_id = callback.data.split("_")[1]
    await state.update_data(gift_id=gift_id)
    
    sticker_id = next((v['sticker'] for k, v in GIFTS_MENU.items() if v['id'] == gift_id), None)
    if sticker_id: await callback.message.answer_sticker(sticker_id)

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎁 Себе", callback_data="to_me")],
        [InlineKeyboardButton(text="👥 Другу", callback_data="to_friend")],
        [InlineKeyboardButton(text="📢 В канал", callback_data="to_channel")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="open_shop")]
    ])
    await ui_update(callback, "<b>Кому отправить подарок?</b>", kb)

@router.callback_query(F.data == "to_me")
async def to_me_handler(callback: CallbackQuery, state: FSMContext):
    await show_privacy_warning(callback, str(callback.from_user.id), state)

@router.callback_query(F.data == "to_friend")
async def to_friend_handler(callback: CallbackQuery, state: FSMContext):
    kb = ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="👤 Выбрать пользователя", request_user=KeyboardButtonRequestUser(request_id=1))],
        [KeyboardButton(text="❌ Отмена")]
    ], resize_keyboard=True)
    await callback.message.answer("Нажмите кнопку ниже, чтобы выбрать друга:", reply_markup=kb)
    await state.set_state(GiftStates.waiting_for_recipient)

@router.callback_query(F.data == "to_channel")
async def to_channel_handler(callback: CallbackQuery, state: FSMContext):
    kb = ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="📢 Выбрать канал", request_chat=KeyboardButtonRequestChat(request_id=2, chat_is_channel=True))],
        [KeyboardButton(text="❌ Отмена")]
    ], resize_keyboard=True)
    await callback.message.answer("Нажмите кнопку ниже, чтобы выбрать канал:", reply_markup=kb)
    await state.set_state(GiftStates.waiting_for_recipient)

@router.message(GiftStates.waiting_for_recipient)
async def process_recipient(message: Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.clear()
        return await cmd_start(message, state, message.bot)
    
    t_id = None
    if message.user_shared: t_id = str(message.user_shared.user_id)
    elif message.chat_shared: t_id = str(message.chat_shared.chat_id)
    elif message.text and message.text.replace('-', '').isdigit(): t_id = message.text
    
    if not t_id:
        return await message.answer("Пожалуйста, используйте кнопку или введите ID.")

    await message.answer("ID принят.", reply_markup=ReplyKeyboardRemove())
    await show_privacy_warning(message, t_id, state)

@router.callback_query(GiftStates.waiting_for_confirmation, F.data == "confirm_privacy")
async def confirm_privacy_handler(callback: CallbackQuery, state: FSMContext):
    await ask_for_comment_ui(callback, state)

@router.callback_query(GiftStates.waiting_for_custom_comment, F.data == "skip_comment")
async def skip_comment_callback(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    await send_payment_invoice(callback.message, data['gift_id'], data['target_id'], "", state)
    await callback.message.delete()

@router.message(GiftStates.waiting_for_custom_comment)
async def comment_message_handler(message: Message, state: FSMContext):
    if not message.text: return
    if len(message.text) > 128:
        return await message.answer("⚠️ Максимум 128 символов!")
    
    data = await state.get_data()
    await send_payment_invoice(message, data['gift_id'], data['target_id'], message.text, state)

async def send_payment_invoice(message: Message, gift_id, target_id, comment, state: FSMContext):
    await message.answer_invoice(
        title="Оплата подарка",
        description=f"Кому: {target_id}\nТекст: {comment or 'Без комментария'}",
        prices=[LabeledPrice(label="XTR", amount=GIFT_PRICE)],
        payload=f"pay:{gift_id}:{target_id}:{comment}",
        currency="XTR",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=f"Оплатить ⭐️{GIFT_PRICE}", pay=True)]])
    )
    await state.clear()

@router.pre_checkout_query()
async def pre_checkout(q: PreCheckoutQuery):
    await q.answer(ok=True)

@router.message(F.content_type == ContentType.SUCCESSFUL_PAYMENT)
async def success_payment(m: Message, bot: Bot):
    p = m.successful_payment.invoice_payload.split(":")
    try:
        target = int(p[2]) if p[2].replace('-', '').isdigit() else p[2]
        await bot(SendGift(gift_id=p[1], user_id=target, text=p[3]))
        await m.answer("✅ Подарок успешно отправлен! не забудьте оставить отзыв в @Delete_Gifts")
    except Exception as e:
        logging.error(f"Ошибка: {e}")
        await m.answer("❌ Ошибка при отправке подарка. Обратитесь в поддержку.")

@router.callback_query(F.data == "back_start")
async def back_to_main_callback(callback: CallbackQuery, state: FSMContext, bot: Bot):
    await state.clear()
    await callback.message.delete() # Удаляем старое, чтобы не путаться
    await cmd_start(callback.message, state, bot)

async def main():
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()
    dp.include_router(router)
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
