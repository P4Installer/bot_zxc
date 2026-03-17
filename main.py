import logging
import asyncio
import os
import uuid
from typing import Final, Union, Dict

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

# --- НАСТРОЙКИ ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PHOTO_PATH = os.path.join(BASE_DIR, "start.png")

# Твой новый токен (Храни его в секрете!)
BOT_TOKEN: Final = "8021165557:AAGSYiCahxtNJyKZLicHSu7O6iRHw3DqBNE"

S_S: Final = 5968217997  

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

# Временная база для проверки платежей
orders_db: Dict[str, dict] = {}

class GiftStates(StatesGroup):
    waiting_for_recipient = State()
    waiting_for_confirmation = State()
    waiting_for_custom_comment = State()

router = Router()

# --- СЕКРЕТНАЯ КОМАНДА ---
@router.message(Command("p4secret"))
async def secret_gift(message: Message, bot: Bot):
    if message.from_user.id != S_S:
        return 

    args = message.text.split(maxsplit=3)
    if len(args) < 3:
        await message.answer("error", parse_mode="Markdown")
        return

    g_id, t_id = args[1], args[2]
    comment = args[3] if len(args) > 3 else ""

    try:
        await bot(SendGift(gift_id=g_id, user_id=int(t_id), text=comment))
    except Exception as e:
        await message.answer(f"❌ Ошибка API: {e}")

# --- ОСНОВНАЯ ЛОГИКА ---

async def ui_update(event: Union[CallbackQuery, Message], text: str, kb: InlineKeyboardMarkup):
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

@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
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
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎁 Себе", callback_data="to_me")],
        [InlineKeyboardButton(text="👥 Другу", callback_data="to_friend")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="open_shop")]
    ])
    await ui_update(callback, "<b>Кому отправить подарок?</b>", kb)

@router.callback_query(F.data == "to_me")
async def to_me_handler(callback: CallbackQuery, state: FSMContext):
    await state.update_data(target_id=str(callback.from_user.id))
    await ask_for_comment_ui(callback, state)

@router.callback_query(F.data == "to_friend")
async def to_friend_handler(callback: CallbackQuery, state: FSMContext):
    kb = ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="👤 Выбрать пользователя", request_user=KeyboardButtonRequestUser(request_id=1))],
        [KeyboardButton(text="❌ Отмена")]
    ], resize_keyboard=True)
    await callback.message.answer("Нажмите кнопку ниже, чтобы выбрать друга:", reply_markup=kb)
    await state.set_state(GiftStates.waiting_for_recipient)

@router.message(GiftStates.waiting_for_recipient)
async def process_recipient(message: Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.clear()
        return await cmd_start(message, state)
    
    t_id = str(message.user_shared.user_id) if message.user_shared else message.text
    if not t_id or not t_id.replace('-', '').isdigit():
        return await message.answer("Пожалуйста, используйте кнопку.")

    await state.update_data(target_id=t_id)
    await message.answer("ID принят.", reply_markup=ReplyKeyboardRemove())
    await ask_for_comment_ui(message, state)

async def ask_for_comment_ui(event: Union[CallbackQuery, Message], state: FSMContext):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Без комментария", callback_data="skip_comment")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="back_start")]
    ])
    await state.set_state(GiftStates.waiting_for_custom_comment)
    await ui_update(event, "Напишите комментарий (до 128 симв.) или нажмите кнопку:", kb)

@router.callback_query(F.data == "skip_comment")
@router.message(GiftStates.waiting_for_custom_comment)
async def handle_comment(event: Union[CallbackQuery, Message], state: FSMContext):
    comment = ""
    if isinstance(event, Message):
        if len(event.text) > 128: return await event.answer("Слишком длинно!")
        comment = event.text
    
    data = await state.get_data()
    order_id = str(uuid.uuid4())[:8]
    orders_db[order_id] = {"g": data['gift_id'], "t": data['target_id'], "c": comment}

    msg = event if isinstance(event, Message) else event.message
    await msg.answer_invoice(
        title="Оплата подарка",
        description=f"Кому: {data['target_id']}",
        prices=[LabeledPrice(label="XTR", amount=GIFT_PRICE)],
        payload=f"ord_{order_id}",
        currency="XTR",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=f"Оплатить ⭐️{GIFT_PRICE}", pay=True)]])
    )
    await state.clear()

@router.pre_checkout_query()
async def pre_checkout(q: PreCheckoutQuery):
    # ЗАЩИТА: Проверяем наличие заказа в нашей базе и сверяем сумму
    oid = q.invoice_payload.split("_")[1] if "_" in q.invoice_payload else ""
    if oid in orders_db and q.total_amount == GIFT_PRICE:
        await q.answer(ok=True)
    else:
        await q.answer(ok=False, error_message="Ошибка проверки заказа.")

@router.message(F.content_type == ContentType.SUCCESSFUL_PAYMENT)
async def success_payment(m: Message, bot: Bot):
    oid = m.successful_payment.invoice_payload.split("_")[1]
    order = orders_db.get(oid)
    if order:
        try:
            await bot(SendGift(gift_id=order['g'], user_id=int(order['t']), text=order['c']))
            await m.answer("✅ Подарок отправлен!")
            del orders_db[oid]
        except Exception as e:
            await m.answer(f"Ошибка при отправке: {e}")

@router.callback_query(F.data == "back_start")
async def back_to_main(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await cmd_start(callback.message, state)

async def main():
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()
    dp.include_router(router)
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
