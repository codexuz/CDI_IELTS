# bot/app/handlers/common.py
from __future__ import annotations
from aiogram import Router, types
from aiogram.filters import CommandStart, Command

from ..keyboards import main_menu

router = Router(name="common")


@router.message(CommandStart())
async def start_cmd(msg: types.Message) -> None:
    await msg.answer(
        "Salom! Men CDI IELTS botiman. Kerakli OTP turini tanlang:",
        reply_markup=main_menu(),
    )


@router.message(Command("help"))
async def help_cmd(msg: types.Message) -> None:
    await msg.answer("📎 /start — menyu\n📲 Register code\n🔐 Login code")
