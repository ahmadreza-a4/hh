import os
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.types import (
    Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, ContentType
)
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.router import Router
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram import F

# توکن و آی‌دی مدیر
API_TOKEN = os.getenv("BOT_TOKEN")
if not API_TOKEN:
    raise ValueError("BOT_TOKEN not set in environment variables.")
ADMIN_ID = 694246194

# تنظیمات لاگ
logging.basicConfig(level=logging.INFO)

# ساخت ربات
bot = Bot(token=API_TOKEN, parse_mode=ParseMode.HTML)
dp = Dispatcher(storage=MemoryStorage())
router = Router()
dp.include_router(router)

# قیمت‌ها
PRICES = {
    "vmess": lambda gb: gb * 3000,
    "vless": lambda gb: gb * 3000 + 20000
}

# لوکیشن‌ها
LOCATIONS = {
    "france": "🇫🇷 فرانسه",
    "sweden": "🇸🇪 سوئد",
    "austria": "🇦🇹 اتریش",
    "netherlands": "🇳🇱 هلند"
}

user_orders = {}

# منوی اصلی
def main_menu():
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✨ خرید اشتراک", callback_data="buy")],
        [InlineKeyboardButton(text="ℹ️ مشخصات اشتراک", callback_data="info")]
    ])
    return kb

@router.message(Command("start"))
async def start_cmd(message: Message):
    await message.answer(
        "به ربات فروش کانفیگ‌های پرسرعت ویتوری خوش آمدید\n\n⚡ پشتیبانی ۲۴ ساعته\n📱 مناسب برای انواع دستگاه‌ها",
        reply_markup=main_menu()
    )

@router.callback_query(F.data == "info")
async def handle_info(callback: CallbackQuery):
    await bot.send_message(ADMIN_ID, f"درخواست مشخصات از کاربر: {callback.from_user.id}")
    await callback.message.answer("درخواست شما ثبت شد، منتظر پاسخ مدیر باشید.", reply_markup=back_button())
    await callback.answer()

@router.callback_query(F.data == "buy")
async def handle_buy(callback: CallbackQuery):
    user_orders[callback.from_user.id] = {}
    builder = InlineKeyboardBuilder()
    for key, loc in LOCATIONS.items():
        builder.button(text=loc, callback_data=f"loc:{key}")
    builder.adjust(2)
    builder.row(InlineKeyboardButton(text="🔙 بازگشت", callback_data="main"))
    await callback.message.answer("کشور مورد نظر را انتخاب کنید:", reply_markup=builder.as_markup())
    await callback.answer()

@router.callback_query(F.data.startswith("loc:"))
async def choose_service(callback: CallbackQuery):
    loc = callback.data.split(":")[1]
    user_orders[callback.from_user.id]['location'] = loc
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="vmess", callback_data="srv:vmess"),
            InlineKeyboardButton(text="vless", callback_data="srv:vless")
        ],
        [InlineKeyboardButton(text="🔙 بازگشت", callback_data="buy")]
    ])
    await callback.message.answer("نوع سرویس را انتخاب کنید:", reply_markup=kb)
    await callback.answer()

@router.callback_query(F.data.startswith("srv:"))
async def choose_duration(callback: CallbackQuery):
    srv = callback.data.split(":")[1]
    user_orders[callback.from_user.id]['service'] = srv
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="1 ماهه", callback_data="dur:1"),
            InlineKeyboardButton(text="3 ماهه", callback_data="dur:3")
        ],
        [InlineKeyboardButton(text="🔙 بازگشت", callback_data="buy")]
    ])
    await callback.message.answer("مدت زمان را انتخاب کنید:", reply_markup=kb)
    await callback.answer()

@router.callback_query(F.data.startswith("dur:"))
async def choose_volume(callback: CallbackQuery):
    duration = int(callback.data.split(":")[1])
    user_orders[callback.from_user.id]['duration'] = duration
    volumes = [20, 30, 50, 80, 100] if duration == 1 else [50, 100, 200]
    builder = InlineKeyboardBuilder()
    for v in volumes:
        builder.button(text=f"{v} گیگ", callback_data=f"vol:{v}")
    builder.adjust(3)
    builder.row(InlineKeyboardButton(text="🔙 بازگشت", callback_data="buy"))
    await callback.message.answer("حجم مورد نظر را انتخاب کنید:", reply_markup=builder.as_markup())
    await callback.answer()

@router.callback_query(F.data.startswith("vol:"))
async def final_step(callback: CallbackQuery):
    uid = callback.from_user.id
    vol = int(callback.data.split(":")[1])
    order = user_orders[uid]
    order['volume'] = vol
    price = PRICES[order['service']](vol)
    order['price'] = price

    summary = (
        f"<b>✉️ مشخصات سفارش:</b>\n"
        f"کشور: {LOCATIONS[order['location']]}\n"
        f"سرویس: {order['service']}\n"
        f"مدت: {order['duration']} ماه\n"
        f"حجم: {vol} گیگ\n"
        f"<b>مبلغ: {price:,} تومان</b>\n\n"
        f"لطفاً مبلغ را به شماره کارت زیر واریز کرده و سپس فیش را ارسال کنید:\n"
        f"<code>6037-9918-7450-3889</code>\n(به نام احمدرضا اله دادی)"
    )

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ ارسال فیش", callback_data="paid")],
        [InlineKeyboardButton(text="🔙 بازگشت", callback_data="buy")]
    ])
    await callback.message.answer(summary, reply_markup=kb)
    await callback.answer()

@router.callback_query(F.data == "paid")
async def wait_for_receipt(callback: CallbackQuery):
    await callback.message.answer("لطفاً تصویر فیش واریزی را ارسال کنید.")
    await callback.answer()

@router.message(F.content_type == ContentType.PHOTO)
async def handle_photo_receipt(message: Message):
    if message.from_user.id in user_orders:
        await message.forward(ADMIN_ID)
        await message.answer("فیش شما ارسال شد. لطفا منتظر تایید مدیر بمانید.")

@router.message(Command("send_config"))
async def handle_config(message: Message):
    if message.from_user.id != ADMIN_ID:
        return
    parts = message.text.split(" ", 2)
    if len(parts) < 3:
        await message.answer("فرمت صحیح: /send_config user_id کانفیگ")
        return
    try:
        target_id = int(parts[1])
        await bot.send_message(target_id, f"✅ کانفیگ شما آماده است:\n\n{parts[2]}")
        await message.answer("ارسال شد.")
    except Exception as e:
        await message.answer(f"خطا: {e}")

def back_button():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 بازگشت به منو", callback_data="main")]
    ])

@router.callback_query(F.data == "main")
async def back_to_menu(callback: CallbackQuery):
    await callback.message.answer("بازگشت به منو:", reply_markup=main_menu())
    await callback.answer()

# اجرای ربات
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
