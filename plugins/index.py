import logging
import asyncio
from pyrogram import Client, filters
from pyrogram.errors import FloodWait
from pyrogram.errors.exceptions.bad_request_400 import ChatAdminRequired
from info import ADMINS, LOG_CHANNEL
from database.ia_filterdb import save_file
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from utils import temp
logger = logging.getLogger(__name__)
lock = asyncio.Lock()



@Client.on_callback_query(filters.regex(r'^index'))
async def index_files(bot, query):
    if query.data.startswith('index_cancel'):
        temp.CANCEL=True
        return await query.answer("Cancelling Indexing")
    _, raju, chat, lst_msg_id, from_user = query.data.split("#")
    if raju == 'reject':
        await query.message.delete()
        await bot.send_message(int(from_user), f'Your Submission for indexing {chat} has been decliened by our moderators.', reply_to_message_id=int(lst_msg_id))
        return

    if lock.locked():
        return await query.answer('Wait until previous process complete.', show_alert=True)
    msg = query.message

    await query.answer('𝐇𝐚𝐜𝐤𝐢𝐧𝐠 𝐅𝐢𝐥𝐞𝐬...🙈', show_alert=True)
    if int(from_user) not in ADMINS:
        await bot.send_message(int(from_user), f'Your Submission for indexing {chat} has been accepted by our moderators and will be added soon.', reply_to_message_id=int(lst_msg_id))
    await msg.edit(
        "Starting Indexing",
        reply_markup = InlineKeyboardMarkup(
            [[InlineKeyboardButton('🄲🄰🄽🄲🄴🄻', callback_data='index_cancel')]]
        )
    )
    try:
        chat = int(chat)
    except:
        chat = chat
    await index_files_to_db(int(lst_msg_id), chat, msg, bot)


@Client.on_message(filters.forwarded & filters.private & filters.incoming)
async def send_for_index(bot, message):
    if message.forward_from_chat.type != 'channel':
        return
    
    last_msg_id = message.forward_from_message_id
    chat_id = message.forward_from_chat.username or message.forward_from_chat.id
    try:
        await bot.get_messages(chat_id, last_msg_id)
    except:
        return await message.reply('Make Sure That Iam An Admin In The Channel, if channel is private')
    
    if message.from_user.id in ADMINS:
        buttons = [
            [
                InlineKeyboardButton('🅈🄴🅂', callback_data=f'index#accept#{chat_id}#{last_msg_id}#{message.from_user.id}')
            ],
            [
                InlineKeyboardButton('🄲🄰🄽🄲🄴🄻', callback_data='close_data'),
            ]
            ]
        reply_markup = InlineKeyboardMarkup(buttons)
        return await message.reply(f'Do you Want To Index This Channel?\n\nChat ID/ Username: <code>{chat_id}</code>\nLast Message ID: <code>{last_msg_id}</code>', reply_markup=reply_markup)

    if not message.forward_from_chat.username:
        try:
            link = (await bot.create_chat_invite_link(chat_id)).invite_link
        except ChatAdminRequired:
            return await message.reply('Make sure iam an admin in the chat and have permission to invite users.')
    else:
        link = f"@{message.forward_from_chat.username}"
    buttons = [
        [
            InlineKeyboardButton('🄰🄲🄲🄴🄿🅃 🄸🄽🄳🄴🅇', callback_data=f'index#accept#{chat_id}#{last_msg_id}#{message.from_user.id}')
        ],
        [
            InlineKeyboardButton('🅁🄴🄹🄴🄲🅃 🄸🄽🄳🄴🅇', callback_data=f'index#reject#{chat_id}#{message.message_id}#{message.from_user.id}'),
        ]
        ]
    reply_markup = InlineKeyboardMarkup(buttons)
    await bot.send_message(LOG_CHANNEL, f'#IndexRequest\n\nBy : {message.from_user.mention}\nChat ID/ Username - <code> {chat_id}</code>\nLast Message ID - <code>{last_msg_id}</code>\nInviteLink - {link}', reply_markup=reply_markup)
    await message.reply('ThankYou For the Contribution, Wait For My Moderators to verify the files.')
        
        

@Client.on_message(filters.command('setskip') & filters.user(ADMINS))
async def set_skip_number(bot, message):
    if ' ' in message.text:
        _, skip = message.text.split(" ")
        try:
            skip = int(skip)
        except:
            return await message.reply("Skip number should be an integer.")
        await message.reply(f"Succesfully set SKIP number as {skip}")
        temp.CURRENT=int(skip)
    else:
        await message.reply("Give me a skip number")


async def index_files_to_db(lst_msg_id, chat, msg, bot):
    total_files = 0
    async with lock:
        try:
            total=lst_msg_id + 1
            current=temp.CURRENT
            temp.CANCEL=False
            while current < total:
                if temp.CANCEL:
                    await msg.edit("Succesfully Cancelled")
                    break
                try:
                    message = await bot.get_messages(chat_id=chat, message_ids=current, replies=0)
                except FloodWait as e:
                    await asyncio.sleep(e.x)
                    message = await bot.get_messages(
                        chat,
                        current,
                        replies=0
                        )
                except Exception as e:
                    print(e)
                try:
                    for file_type in ("document", "video", "audio"):
                        media = getattr(message, file_type, None)
                        if media is not None:
                            break
                        else:
                            continue
                    media.file_type = file_type
                    media.caption = message.caption
                    await save_file(media)
                    total_files += 1
                except TypeError:
                    pass
                except Exception as e:
                    print(e)
                current+=1
                if current % 20 == 0:
                    can = [[InlineKeyboardButton('Cancel', callback_data='index_cancel')]]
                    reply = InlineKeyboardMarkup(can)
                    await msg.edit_text(
                        text=f"Total messages fetched: <code>{current}</code>\nTotal messages saved: <code>{total_files}</code>",
                        reply_markup=reply)
        except Exception as e:
            logger.exception(e)
            await msg.edit(f'Error: {e}')
        else:
            await msg.edit(f'Total <code>{total_files}</code> Saved To DataBase!')
