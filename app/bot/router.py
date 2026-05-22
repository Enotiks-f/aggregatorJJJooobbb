from aiogram import Router

from app.bot.handlers import channels_router, commands_router

bot_router = Router(name="bot")
bot_router.include_router(commands_router)
bot_router.include_router(channels_router)
