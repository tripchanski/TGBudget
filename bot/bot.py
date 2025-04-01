from aiogram import Bot, Dispatcher # type: ignore
import logging, os, asyncio
from app.handlers import router

logging.basicConfig(level=logging.INFO)

BOT_TOKEN = Bot(token=os.getenv("BOT_TOKEN"))

dp = Dispatcher()

async def main():
    dp.include_router(router)
    await dp.start_polling(BOT_TOKEN)

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print('Exit')
