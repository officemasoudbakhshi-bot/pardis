import os
import logging
from telegram import (
    Update,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
    KeyboardButton,
    InlineKeyboardButton,
    InlineKeyboardMarkup
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ConversationHandler,
    CallbackQueryHandler,
    ContextTypes
)
from collections import defaultdict
from datetime import datetime
import random
import asyncio

# تنظیمات از متغیرهای محیطی
BOT_TOKEN = os.environ.get('BOT_TOKEN')
ADMIN_ID = int(os.environ.get('ADMIN_ID', 5872842793))
GROUP_CHAT_ID = int(os.environ.get('GROUP_CHAT_ID', -1002907242405))

# حالت‌های مکالمه
(
    NAME, PHONE, SCREENSHOT, CONFIRMATION,
    MEETING_DATE, MEETING_TIME, MEETING_DURATION,
    MEETING_LOCATION, MEETING_MANAGER, MEETING_TOPICS,
    MEETING_INVITEES, MEETING_LINK, MEETING_FILES,
    MEETING_CONFIRMATION
) = range(14)

# دیکشنری برای ذخیره اطلاعات
user_data = {}
verified_users = set()
blocked_users = set()
user_message_count = defaultdict(int)
pending_approvals = {}
user_registration_date = {}

# مدیریت جلسات
meetings = {}
active_meetings = {}
meeting_attendance = defaultdict(set)
meeting_messages = {}

# تنظیمات لاگینگ
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ایجاد application
application = Application.builder().token(BOT_TOKEN).build()

def save_bot_state():
    try:
        print("💾 Bot state saved")
    except Exception as e:
        logger.error(f"Error saving state: {e}")

def load_bot_state():
    try:
        print("💾 Bot state loaded")
    except Exception as e:
        logger.error(f"Error loading state: {e}")

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_first_name = update.effective_user.first_name

    if user_id == ADMIN_ID:
        await show_admin_panel(update, context)
        return

    if user_id in blocked_users:
        await update.message.reply_text(
            "❌ حساب شما مسدود شده است. لطفا با ادمین تماس بگیرید.",
            reply_markup=ReplyKeyboardRemove()
        )
        return ConversationHandler.END

    if update.effective_chat.type in ['group', 'supergroup']:
        if user_id in verified_users:
            return
        else:
            await update.message.reply_text(
                f"سلام {user_first_name} عزیz! 👋\nبرای فعال‌سازی حساب، لطفا ربات را در چت خصوصی استارت کنید:\n@{context.bot.username}",
                reply_markup=ReplyKeyboardRemove()
            )
    else:
        context.user_data.clear()
        await update.message.reply_text(
            "سلام! خوش آمدید. 👋\nبرای تکمیل احراز هویت، لطفا اطلاعات زیر را وارد کنید.\n\n"
            "لطفا نام و نام خانوادگی خود را وارد کنید:",
            reply_markup=ReplyKeyboardRemove()
        )
        return NAME

async def show_admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    total_verified = len(verified_users)
    total_pending = len(pending_approvals)
    total_blocked = len(blocked_users)
    total_meetings = len(meetings)
    active_meetings_count = len(active_meetings)

    admin_keyboard = [
        ['📊 آمار کاربران', '📋 کاربران در انتظار'],
        ['✅ کاربران تأیید شده', '❌ کاربران مسدود شده'],
        ['📅 مدیریت جلسات', '🎯 ایجاد جلسه جدید'],
        ['🗑️ پاک کردن حافظه', '🔄 بروزرسانی پنل']
    ]
    reply_markup = ReplyKeyboardMarkup(admin_keyboard, resize_keyboard=True)

    stats_message = (
        "👨‍💼 پنل مدیریت حرفه‌ای ربات\n\n"
        f"📊 آمار کلی:\n"
        f"✅ کاربران تأیید شده: {total_verified} نفر\n"
        f"⏳ کاربران در انتظار: {total_pending} نفر\n"
        f"❌ کاربران مسدود شده: {total_blocked} نفر\n"  # اینجا f انگلیسی است
        f"📅 جلسات ثبت شده: {total_meetings} جلسه\n"
        f"🎯 جلسات فعال: {active_meetings_count} جلسه\n\n"
        "🔧 گزینه مورد نظر را انتخاب کنید:"
    )

    await update.message.reply_text(stats_message, reply_markup=reply_markup)

async def show_user_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    total_verified = len(verified_users)
    total_pending = len(pending_approvals)
    total_blocked = len(blocked_users)

    stats_message = (
        "📊 آمار دقیق کاربران:\n\n"
        f"✅ کاربران تأیید شده: {total_verified} نفر\n"
        f"⏳ کاربران در انتظار تأیید: {total_pending} نفر\n"
        f"❌ کاربران مسدود شده: {total_blocked} نفر\n\n"
        f"📈 مجموع کاربران: {total_verified + total_pending + total_blocked} نفر\n"
        f"🔄 آخرین بروزرسانی: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    )

    await update.message.reply_text(stats_message)

async def show_pending_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not pending_approvals:
        await update.message.reply_text("✅ هیچ کاربری در انتظار تأیید نیست.")
        return

    pending_list = "📋 کاربران در انتظار تأیید:\n\n"
    for i, (user_id, data) in enumerate(pending_approvals.items(), 1):
        pending_list += (
            f"#{i} - 🆔 {user_id}\n"
            f"   📛 نام: {data['name']}\n"
            f"   📱 تلفن: {data['phone']}\n"
            f"   🕒 ثبت: {data.get('registration_time', 'نامشخص')}\n"
            f"   ────────────────────\n"
        )

    pending_list += f"\n📝 تعداد کل: {len(pending_approvals)} کاربر"

    await update.message.reply_text(pending_list[:4000])

async def show_verified_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not verified_users:
        await update.message.reply_text("📭 هیچ کاربر تأیید شده‌ای وجود ندارد.")
        return

    verified_list = "✅ کاربران تأیید شده:\n\n"
    for i, user_id in enumerate(list(verified_users)[:15], 1):
        reg_date = user_registration_date.get(user_id, 'نامشخص')
        verified_list += f"#{i} - 🆔 {user_id} - 📅 {reg_date}\n"

    if len(verified_users) > 15:
        verified_list += f"\n📦 و {len(verified_users) - 15} کاربر دیگر..."

    verified_list += f"\n📊 تعداد کل: {len(verified_users)} کاربر"

    await update.message.reply_text(verified_list)

async def show_blocked_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not blocked_users:
        await update.message.reply_text("✅ هیچ کاربر مسدود شده‌ای وجود ندارد.")
        return

    blocked_list = "❌ کاربران مسدود شده:\n\n"
    for i, user_id in enumerate(list(blocked_users)[:15], 1):
        blocked_list += f"#{i} - 🆔 {user_id}\n"

    if len(blocked_users) > 15:
        blocked_list += f"\n📦 و {len(blocked_users) - 15} کاربر دیگر..."

    blocked_list += f"\n📊 تعداد کل: {len(blocked_users)} کاربر"

    await update.message.reply_text(blocked_list)

async def clear_memory(update: Update, context: ContextTypes.DEFAULT_TYPE):
    confirm_keyboard = [['🔥 بله، پاک کن', '❌ انصراف']]
    reply_markup = ReplyKeyboardMarkup(confirm_keyboard, resize_keyboard=True)

    confirmation_message = (
        "⚠️ هشدار: عملیات پاک کردن حافظه\n\n"
        "🔸 این عمل تمام داده‌های زیر را پاک می‌کند:\n"
        "   • کاربران تأیید شده\n"
        "   • کاربران در انتظار\n"
        "   • کاربران مسدود شده\n"
        "   • تاریخ‌های ثبت نام\n"
        "   • شمارنده پیام‌ها\n\n"
        "🔸 داده‌های کاربران باید مجدداً ثبت شوند.\n"
        "🔸 این عمل غیرقابل بازگشت است!\n\n"
        "آیا مطمئن هستید?"
    )

    await update.message.reply_text(confirmation_message, reply_markup=reply_markup)

async def handle_clear_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_choice = update.message.text

    if user_choice == '🔥 بله، پاک کن':
        total_verified = len(verified_users)
        total_pending = len(pending_approvals)
        total_blocked = len(blocked_users)

        verified_users.clear()
        pending_approvals.clear()
        blocked_users.clear()
        user_message_count.clear()
        user_registration_date.clear()

        report_message = (
            "✅ حافظه ربات با موفقیت پاک شد!\n\n"
            f"📊 داده‌های پاک شده:\n"
            f"   • کاربران تأیید شده: {total_verified} نفر\n"
            f"   • کاربران در انتظار: {total_pending} نفر\n"
            f"   • کاربران مسدود شده: {total_blocked} نفر\n"
            f"   • تاریخ‌های ثبت نام: {len(user_registration_date)} مورد\n\n"
            f"🔄 تمام داده‌ها reset شدند.\n"
            f"⏰ زمان: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )

        await update.message.reply_text(report_message, reply_markup=ReplyKeyboardRemove())
        logger.info("Memory cleared by admin")
        await show_admin_panel(update, context)

    elif user_choice == '❌ انصراف':
        await update.message.reply_text(
            "❌ عملیات پاک کردن حافظه لغو شد.",
            reply_markup=ReplyKeyboardRemove()
        )
        await show_admin_panel(update, context)

async def get_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id in blocked_users:
        await update.message.reply_text("❌ حساب شما مسدود شده است.")
        return ConversationHandler.END

    name = update.message.text

    if len(name.split()) < 2:
        await update.message.reply_text("لطفا نام و نام خانوادگی را به طور کامل وارد کنید:")
        return NAME

    context.user_data['name'] = name
    context.user_data['user_id'] = user_id
    context.user_data['username'] = update.effective_user.username
    context.user_data['first_name'] = update.effective_user.first_name

    phone_button = KeyboardButton("📱 ارسال شماره تماس", request_contact=True)
    keyboard = [[phone_button]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

    await update.message.reply_text(
        f"ممنون {name.split()[0]}! 🙏\n\n"
        "لطفا شماره تماس خود را ارسال کنید:",
        reply_markup=reply_markup
    )
    return PHONE

async def get_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if user_id in blocked_users:
        await update.message.reply_text("❌ حساب شما مسدود شده است.")
        return ConversationHandler.END

    if update.message.contact:
        phone_number = update.message.contact.phone_number
        context.user_data['phone'] = phone_number
    else:
        phone_number = update.message.text
        context.user_data['phone'] = phone_number

    await update.message.reply_text(
        "📸 لطفا مرحله اول اسکرین شات مربوط به سایت مسکن ملی را مانند نمونه ارسال کنید:",
        reply_markup=ReplyKeyboardRemove()
    )
    return SCREENSHOT

async def get_screenshot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if user_id in blocked_users:
        await update.message.reply_text("❌ حساب شما مسدود شده است.")
        return SCREENSHOT

    if not update.message.photo:
        await update.message.reply_text("❌ لطفا یک عکس ارسال کنید:")
        return SCREENSHOT

    context.user_data['screenshot_file_id'] = update.message.photo[-1].file_id

    keyboard = [['✅ تایید اطلاعات', '❌ ویرایش مجدد']]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

    await update.message.reply_text(
        f"📋 اطلاعات شما:\n\n"
        f"👤 نام: {context.user_data['name']}\n"
        f"📱 شماره تماس: {context.user_data['phone']}\n"
        f"📸 اسکرین شات: ✅ ارسال شد\n\n"
        f"آیا اطلاعات صحیح است?",
        reply_markup=reply_markup
    )
    return CONFIRMATION

async def confirm_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = context.user_data['user_id']
    user_choice = update.message.text

    if user_choice == '✅ تایید اطلاعات':
        reg_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        context.user_data['registration_time'] = reg_time
        user_registration_date[user_id] = reg_time

        pending_approvals[user_id] = context.user_data.copy()

        await update.message.reply_text(
            "⏳ اطلاعات شما برای تأیید به ادمین ارسال شد.\n"
            "لطفا منتظر تأیید ادمین بمانید.",
            reply_markup=ReplyKeyboardRemove()
        )

        try:
            admin_keyboard = [
                [f'✅ تایید کاربر {user_id}', f'❌ رد کاربر {user_id}']
            ]
            admin_reply_markup = ReplyKeyboardMarkup(admin_keyboard, resize_keyboard=True)

            await context.bot.send_photo(
                chat_id=ADMIN_ID,
                photo=context.user_data['screenshot_file_id'],
                caption=(
                    f"👤 درخواست احراز هویت جدید:\n\n"
                    f"🆔 User ID: {user_id}\n"
                    f"📛 نام: {context.user_data['name']}\n"
                    f"📱 شماره: {context.user_data['phone']}\n"
                    f"👤 First Name: {context.user_data['first_name']}\n"
                    f"🔗 Username: @{context.user_data['username'] or 'ندارد'}\n"
                    f"🕒 زمان ثبت: {reg_time}\n\n"
                    f"لطفا کاربر را تأیید یا رد کنید:"
                ),
                reply_markup=admin_reply_markup
            )
        except Exception as e:
            logger.error(f"Error sending message to admin: {e}")

        return ConversationHandler.END

    elif user_choice == '❌ ویرایش مجدد':
        await update.message.reply_text(
            "لطفا نام و نام خانوادگی خود را مجدداً وارد کنید:",
            reply_markup=ReplyKeyboardRemove()
        )
        return NAME
    else:
        await update.message.reply_text("لطفا از گزینه‌های بالا انتخاب کنید:")
        return CONFIRMATION

async def handle_admin_approval(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    message_text = update.message.text

    if '✅ تایید کاربر' in message_text:
        try:
            user_id = int(message_text.split()[-1])
        except:
            await update.message.reply_text("❌ خطا در پردازش درخواست")
            return

        if user_id in pending_approvals:
            verified_users.add(user_id)
            user_data = pending_approvals.pop(user_id)

            try:
                await context.bot.send_message(
                    chat_id=user_id,
                    text="✅ حساب شما توسط ادمین تأیید شد!\n\nاکنون می‌توانید در گروه به صورت آزادانه چت کنید. 🎉"
                )
            except Exception as e:
                logger.error(f"Error sending approval message to user {user_id}: {e}")

            try:
                welcome_message = (
                    f"🎉 به {user_data['first_name']} خوش آمدیم!\n\n"
                    f"👤 کاربر جدید با موفقیت احراز هویت شد.\n"
                    f"📛 نام: {user_data['name']}\n"
                    f"🕒 زمان عضویت: {user_data['registration_time']}\n\n"
                    "از حضور شما در گروه خوشحالیم! 🌟"
                )

                await context.bot.send_message(
                    chat_id=GROUP_CHAT_ID,
                    text=welcome_message
                )
            except Exception as e:
                logger.error(f"Error sending welcome message to group: {e}")

            await update.message.reply_text(
                f"✅ کاربر {user_id} با موفقیت تأیید شد.\n"
                f"📛 نام: {user_data['name']}\n"
                f"📱 شماره: {user_data['phone']}\n\n"
                f"پیام خوش آمدگویی در گروه ارسال شد.",
                reply_markup=ReplyKeyboardRemove()
            )

            logger.info(f"User {user_id} approved by admin")

        else:
            await update.message.reply_text("❌ کاربر یافت نشد یا قبلاً پردازش شده است.")

    elif '❌ رد کاربر' in message_text:
        try:
            user_id = int(message_text.split()[-1])
        except:
            await update.message.reply_text("❌ خطا در پردازش درخواست")
            return

        if user_id in pending_approvals:
            blocked_users.add(user_id)
            user_data = pending_approvals.pop(user_id)

            try:
                await context.bot.send_message(
                    chat_id=user_id,
                    text="❌ درخواست احراز هویت شما توسط ادمین رد شد.\n\nلطفا با ادمین تماس بگیرید."
                )
            except Exception as e:
                logger.error(f"Error sending rejection message to user {user_id}: {e}")

            await update.message.reply_text(
                f"❌ کاربر {user_id} رد شد و مسدود گردید.\n"
                f"📛 نام: {user_data['name']}\n"
                f"📱 شماره: {user_data['phone']}\n\n"
                f"این کاربر نمی‌تواند مجدداً ثبت نام کند.",
                reply_markup=ReplyKeyboardRemove()
            )

            logger.info(f"User {user_id} rejected by admin")
        else:
            await update.message.reply_text("❌ کاربر یافت نشد یا قبلاً پردازش شده است.")

async def handle_admin_commands(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    command = update.message.text

    # فقط دستورات عمومی ادمین را پردازش کن
    if command == '📊 آمار کاربران':
        await show_user_stats(update, context)
    elif command == '📋 کاربران در انتظار':
        await show_pending_users(update, context)
    elif command == '✅ کاربران تأیید شده':
        await show_verified_users(update, context)
    elif command == '❌ کاربران مسدود شده':
        await show_blocked_users(update, context)
    elif command == '🗑️ پاک کردن حافظه':
        await clear_memory(update, context)
    elif command == '🔄 بروزرسانی پنل':
        await show_admin_panel(update, context)
    elif command in ['🔥 بله، پاک کن', '❌ انصراف']:
        await handle_clear_confirmation(update, context)
    else:
        # اگر دستور مربوط به جلسات نبود، پنل ادمین را نشان بده
        await show_admin_panel(update, context)
    if update.effective_user.id != ADMIN_ID:
        return

    command = update.message.text

    if command == '📊 آمار کاربران':
        await show_user_stats(update, context)
    elif command == '📋 کاربران در انتظار':
        await show_pending_users(update, context)
    elif command == '✅ کاربران تأیید شده':
        await show_verified_users(update, context)
    elif command == '❌ کاربران مسدود شده':
        await show_blocked_users(update, context)
    elif command == '🗑️ پاک کردن حافظه':
        await clear_memory(update, context)
    elif command == '🔄 بروزرسانی پنل':
        await show_admin_panel(update, context)
    elif command in ['🔥 بله، پاک کن', '❌ انصراف']:
        await handle_clear_confirmation(update, context)
    else:
        await show_admin_panel(update, context)

async def handle_group_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id != GROUP_CHAT_ID:
        return

    user_id = update.effective_user.id
    message_text = update.message.text.lower() if update.message.text else ""

    if user_id in blocked_users:
        try:
            await update.message.delete()
        except:
            pass
        return

    if user_id == ADMIN_ID or user_id in verified_users:
        if any(greeting in message_text for greeting in ['سلام', 'سلام علیکم', 'سلام بر شما', 'hello', 'hi']):
            responses = [
                "سلام علیکم! 😊",
                "سلام بر شما! 🙏",
                "درود بر شما! 🌟",
                "سلام عزیز! 👋"
            ]
            response = random.choice(responses)
            await update.message.reply_text(response)
        return

    user_message_count[user_id] += 1
    message_count = user_message_count[user_id]

    if message_count > 3:
        try:
            await update.message.delete()
        except Exception as e:
            logger.error(f"Error deleting message: {e}")

        warning_message = (
            f"👤 کاربر عزیز {update.effective_user.first_name},\n"
            "برای ارسال پیام در گروه، باید ابتدا احراز هویت شوید.\n\n"
            f"لطفا ربات را استارت کنید:\n@{context.bot.username}"
        )

        try:
            await context.bot.send_message(
                chat_id=GROUP_CHAT_ID,
                text=warning_message
            )
        except Exception as e:
            logger.error(f"Error sending warning: {e}")

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "فرآیند احراز هویت لغو شد. با دستور /start می‌توانید مجدداً شروع کنید.",
        reply_markup=ReplyKeyboardRemove()
    )
    return ConversationHandler.END

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.error(f"Error: {context.error}")
    save_bot_state()

# ==================== مدیریت جلسات ====================

async def manage_meetings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """مدیریت جلسات"""
    if not meetings:
        await update.message.reply_text("📭 هیچ جلسه‌ای ثبت نشده است.")
        return

    meetings_list = "📅 لیست جلسات:\n\n"
    for meeting_id, meeting_data in list(meetings.items())[:10]:
        status = "✅ فعال" if meeting_id in active_meetings else "❌ غیرفعال"
        meetings_list += (
            f"🎯 جلسه #{meeting_id}\n"
            f"   📅 تاریخ: {meeting_data['date']}\n"
            f"   ⏰ ساعت: {meeting_data['time']}\n"
            f"   📍 موضوع: {meeting_data['topics'][:20]}...\n"
            f"   🔰 وضعیت: {status}\n"
            f"   ────────────────────\n"
        )

    if len(meetings) > 10:
        meetings_list += f"\n📦 و {len(meetings) - 10} جلسه دیگر..."

    management_keyboard = [
        ['🔍 مشاهده جلسه', '✅ فعال‌سازی جلسه'],
        ['❌ غیرفعال کردن', '🗑️ حذف جلسه'],
        ['📊 آمار حضور', '🔙 بازگشت']
    ]
    reply_markup = ReplyKeyboardMarkup(management_keyboard, resize_keyboard=True)

    await update.message.reply_text(meetings_list, reply_markup=reply_markup)

async def create_meeting_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """شروع ایجاد جلسه جدید"""
    context.user_data['meeting_data'] = {}
    await update.message.reply_text(
        "🎯 ایجاد جلسه جدید\n\n"
        "لطفا تاریخ جلسه را وارد کنید (مثال: 1403/06/20):",
        reply_markup=ReplyKeyboardRemove()
    )
    return MEETING_DATE

async def get_meeting_date(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دریافت تاریخ جلسه"""
    context.user_data['meeting_data']['date'] = update.message.text
    await update.message.reply_text(
        "⏰ لطفا ساعت شروع جلسه را وارد کنید (مثال: 18:00):"
    )
    return MEETING_TIME

async def get_meeting_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دریافت زمان جلسه"""
    context.user_data['meeting_data']['time'] = update.message.text
    await update.message.reply_text(
        "⏳ لطفا مدت زمان جلسه را وارد کنید (مثال: 1.5 ساعت):"
    )
    return MEETING_DURATION

async def get_meeting_duration(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دریافت مدت زمان جلسه"""
    context.user_data['meeting_data']['duration'] = update.message.text
    await update.message.reply_text(
        "📍 لطفا مکان جلسه را وارد کنید:"
    )
    return MEETING_LOCATION

async def get_meeting_location(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دریافت مکان جلسه"""
    context.user_data['meeting_data']['location'] = update.message.text
    await update.message.reply_text(
        "🎙️ لطفا نام مدیر جلسه را وارد کنید:"
    )
    return MEETING_MANAGER

async def get_meeting_manager(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دریافت مدیر جلسه"""
    context.user_data['meeting_data']['manager'] = update.message.text
    await update.message.reply_text(
        "📌 لطفا موضوعات جلسه را وارد کنید (هر موضوع در یک خط):"
    )
    return MEETING_TOPICS

async def get_meeting_topics(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دریافت موضوعات جلسه"""
    context.user_data['meeting_data']['topics'] = update.message.text
    await update.message.reply_text(
        "👥 لطفا اعضای دعوت شده را وارد کنید (هر نام در یک خط):"
    )
    return MEETING_INVITEES

async def get_meeting_invitees(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دریافت اعضای دعوت شده"""
    context.user_data['meeting_data']['invitees'] = update.message.text.split('\n')
    await update.message.reply_text(
        "🔗 لطفا لینک جلسه را وارد کنید (اختیاری):"
    )
    return MEETING_LINK

async def get_meeting_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دریافت لینک جلسه"""
    context.user_data['meeting_data']['link'] = update.message.text
    await update.message.reply_text(
        "📎 لطفا فایل‌های مرتبط را ارسال کنید یا 'ندارد' بنویسید:"
    )
    return MEETING_FILES

async def get_meeting_files(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دریافت فایل‌های جلسه"""
    if update.message.document:
        context.user_data['meeting_data']['files'] = update.message.document.file_id
    else:
        context.user_data['meeting_data']['files'] = update.message.text

    # نمایش خلاصه اطلاعات
    meeting_data = context.user_data['meeting_data']
    summary = (
        f"📋 خلاصه اطلاعات جلسه:\n\n"
        f"📅 تاریخ: {meeting_data['date']}\n"
        f"⏰ ساعت: {meeting_data['time']}\n"
        f"⏳ مدت: {meeting_data['duration']}\n"
        f"📍 مکان: {meeting_data['location']}\n"
        f"🎙️ مدیر: {meeting_data['manager']}\n"
        f"📌 موضوعات:\n{meeting_data['topics']}\n"
        f"👥 اعضا: {len(meeting_data['invitees'])} نفر\n"
        f"🔗 لینك: {meeting_data['link'] or 'ندارد'}\n"
        f"📎 فایل: {'دارد' if meeting_data['files'] != 'ندارد' else 'ندارد'}\n\n"
        f"آیا اطلاعات صحیح است?"
    )

    keyboard = [['✅ بله، تأیید و ارسال', '❌ ویرایش مجدد']]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

    await update.message.reply_text(summary, reply_markup=reply_markup)
    return MEETING_CONFIRMATION

async def confirm_meeting(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """تأیید و ارسال جلسه"""
    user_choice = update.message.text

    if user_choice == '✅ بله، تأیید و ارسال':
        meeting_data = context.user_data['meeting_data']
        meeting_id = len(meetings) + 1

        # ذخیره اطلاعات جلسه
        meetings[meeting_id] = meeting_data
        active_meetings[meeting_id] = meeting_data
        meeting_attendance[meeting_id] = set()

        # ارسال جلسه به گروه
        try:
            message = await send_meeting_to_group(context, meeting_id, meeting_data)
            meeting_messages[meeting_id] = message.message_id
        except Exception as e:
            logger.error(f"Error sending meeting to group: {e}")
            await update.message.reply_text("❌ خطا در ارسال جلسه به گروه")
            return ConversationHandler.END

        await update.message.reply_text(
            f"✅ جلسه #{meeting_id} با موفقیت ایجاد و ارسال شد!",
            reply_markup=ReplyKeyboardRemove()
        )

        # بازگشت به پنل مدیریت
        await show_admin_panel(update, context)

    elif user_choice == '❌ ویرایش مجدد':
        await update.message.reply_text(
            "لطفا تاریخ جلسه را مجدداً وارد کنید:",
            reply_markup=ReplyKeyboardRemove()
        )
        return MEETING_DATE
    else:
        await update.message.reply_text("لطفا از گزینه‌های بالا انتخاب کنید:")
        return MEETING_CONFIRMATION

async def send_meeting_to_group(context: ContextTypes.DEFAULT_TYPE, meeting_id, meeting_data):
    """ارسال جلسه به گروه با فرمت زیبا"""

    # ایجاد دکمه شیشه‌ای
    keyboard = [
        [InlineKeyboardButton("📋 اعلام حضور من", callback_data=f"attend_{meeting_id}")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    # ساخت متن پیام
    message_text = (
        f"🎯 **جلسه هماهنگی پروژه**\n\n"
        f"📅 **تاریخ:** {meeting_data['date']}\n"
        f"⏰ **ساعت:** {meeting_data['time']} ({meeting_data['duration']})\n"
        f"📍 **مکان:** {meeting_data['location']}\n"
        f"🎙️ **مدیر جلسه:** {meeting_data['manager']}\n\n"
        f"📌 **موضوعات جلسه:**\n"
    )

    # اضافه کردن موضوعات
    topics = meeting_data['topics'].split('\n')
    for topic in topics:
        message_text += f"• {topic}\n"

    message_text += f"\n👥 **اعضای دعوت شده ({len(meeting_data['invitees'])} نفر):**\n"

    # اضافه کردن اعضا
    for i, invitee in enumerate(meeting_data['invitees'][:5], 1):
        message_text += f"✅ {invitee}\n"

    if len(meeting_data['invitees']) > 5:
        message_text += f"📦 و {len(meeting_data['invitees']) - 5} نفر دیگر...\n"

    message_text += (
        f"\n──────────────\n"
        f"🔔 **اعلام حضور:**\n"
        f"──────────────\n\n"
        f"📊 **حضور و غیاب (0 نفر):**\n"
        f"✅ حاضرین (0): \n"
        f"⏳ در انتظار ({len(meeting_data['invitees'])}): \n"
        f"❌ غایبین (0): \n"
    )

    if meeting_data['link'] and meeting_data['link'] != 'ندارد':
        message_text += f"\n💬 **لینک جلسه:** {meeting_data['link']}\n"

    if meeting_data['files'] and meeting_data['files'] != 'ندارد':
        message_text += f"📎 **فایل‌های مرتبط:** ✅ ارسال شده\n"

    message_text += f"\n⏰ **شناسه جلسه:** #{meeting_id}"

    # ارسال پیام
    if meeting_data.get('files') and meeting_data['files'] != 'ندارد':
        message = await context.bot.send_document(
            chat_id=GROUP_CHAT_ID,
            document=meeting_data['files'],
            caption=message_text,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    else:
        message = await context.bot.send_message(
            chat_id=GROUP_CHAT_ID,
            text=message_text,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )

    return message

async def handle_attendance_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """مدیریت کلیک روی دکمه حضور"""
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    meeting_id = int(query.data.split('_')[1])

    if meeting_id not in active_meetings:
        await query.edit_message_text("❌ این جلسه منقضی شده است.")
        return

    # اضافه کردن کاربر به لیست حضور
    meeting_attendance[meeting_id].add(user_id)

    # آپدیت پیام
    await update_meeting_message(context, meeting_id)

    await query.edit_message_reply_markup(reply_markup=InlineKeyboardMarkup([[
        InlineKeyboardButton("✅ حضور شما ثبت شد", callback_data="attended")
    ]]))

async def update_meeting_message(context: ContextTypes.DEFAULT_TYPE, meeting_id):
    """آپدیت پیام جلسه با لیست حضور جدید"""
    if meeting_id not in meetings or meeting_id not in meeting_messages:
        return

    meeting_data = meetings[meeting_id]
    attendees = meeting_attendance[meeting_id]
    total_invitees = len(meeting_data['invitees'])

    # ساخت متن جدید
    message_text = (
        f"🎯 **جلسه هماهنگی پروژه**\n\n"
        f"📅 **تاریخ:** {meeting_data['date']}\n"
        f"⏰ **ساعت:** {meeting_data['time']} ({meeting_data['duration']})\n"
        f"📍 **مکان:** {meeting_data['location']}\n"
        f"🎙️ **مدیر جلسه:** {meeting_data['manager']}\n\n"
        f"📌 **موضوعات جلسه:**\n"
    )

    topics = meeting_data['topics'].split('\n')
    for topic in topics:
        message_text += f"• {topic}\n"

    message_text += f"\n👥 **اعضای دعوت شده ({total_invitees} نفر):**\n"

    for i, invitee in enumerate(meeting_data['invitees'][:5], 1):
        message_text += f"✅ {invitee}\n"

    if total_invitees > 5:
        message_text += f"📦 و {total_invitees - 5} نفر دیگر...\n"

    message_text += (
        f"\n──────────────\n"
        f"🔔 **اعلام حضور:**\n"
        f"──────────────\n\n"
        f"📊 **حضور و غیاب ({len(attendees)} نفر):**\n"
        f"✅ حاضرین ({len(attendees)}): \n"
    )

    # نمایش 5 کاربر اول
    attendee_names = []
    for user_id in list(attendees)[:5]:
        try:
            user = await context.bot.get_chat(user_id)
            attendee_names.append(f"@{user.username}" if user.username else user.first_name)
        except:
            attendee_names.append(f"User_{user_id}")

    if attendee_names:
        message_text += ", ".join(attendee_names) + "\n"

    if len(attendees) > 5:
        message_text += f"📦 و {len(attendees) - 5} نفر دیگر...\n"

    waiting = total_invitees - len(attendees)
    message_text += f"⏳ در انتظار ({waiting}): \n"
    message_text += f"❌ غایبین (0): \n"

    if meeting_data['link'] and meeting_data['link'] != 'ندارد':
        message_text += f"\n💬 **لینک جلسه:** {meeting_data['link']}\n"

    if meeting_data['files'] and meeting_data['files'] != 'ندارد':
        message_text += f"📎 **فایل‌های مرتبط:** ✅ ارسال شده\n"

    message_text += f"\n⏰ **شناسه جلسه:** #{meeting_id}"

    # آپدیت پیام
    try:
        await context.bot.edit_message_text(
            chat_id=GROUP_CHAT_ID,
            message_id=meeting_messages[meeting_id],
            text=message_text,
            parse_mode='Markdown'
        )
    except Exception as e:
        logger.error(f"Error updating meeting message: {e}")

# اضافه کردن هندلرها
# در تابع setup_handlers() این بخش را اصلاح کنید:

def setup_handlers():
    """تنظیم و اضافه کردن هندلرها"""

    # اضافه کردن هندلرهای اصلی
    application.add_handler(MessageHandler(
        filters.TEXT & filters.Chat(chat_id=ADMIN_ID) &
        (filters.Regex(r'✅ تایید کاربر \d+') | filters.Regex(r'❌ رد کاربر \d+')),
        handle_admin_approval
    ))

    # هندلر برای دستورات ادمین - این باید قبل از هندلر عمومی ادمین باشد
    application.add_handler(MessageHandler(
        filters.TEXT & filters.Chat(chat_id=ADMIN_ID) &
        (filters.Regex('^📊 آمار کاربران$') | 
         filters.Regex('^📋 کاربران در انتظار$') |
         filters.Regex('^✅ کاربران تأیید شده$') |
         filters.Regex('^❌ کاربران مسدود شده$') |
         filters.Regex('^🗑️ پاک کردن حافظه$') |
         filters.Regex('^🔄 بروزرسانی پنل$') |
         filters.Regex('^🔥 بله، پاک کن$') |
         filters.Regex('^❌ انصراف$')),
        handle_admin_commands
    ))

    # هندلر برای مدیریت جلسات
    application.add_handler(MessageHandler(
        filters.TEXT & filters.Chat(chat_id=ADMIN_ID) &
        filters.Regex('^📅 مدیریت جلسات$'),
        manage_meetings
    ))

    # هندلر برای ایجاد جلسه جدید
    application.add_handler(MessageHandler(
        filters.TEXT & filters.Chat(chat_id=ADMIN_ID) &
        filters.Regex('^🎯 ایجاد جلسه جدید$'),
        create_meeting_start
    ))

    # ConversationHandler برای احراز هویت
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start_command)],
        states={
            NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_name)],
            PHONE: [MessageHandler(filters.CONTACT | (filters.TEXT & ~filters.COMMAND), get_phone)],
            SCREENSHOT: [MessageHandler(filters.PHOTO, get_screenshot)],
            CONFIRMATION: [MessageHandler(filters.TEXT & ~filters.COMMAND, confirm_data)]
        },
        fallbacks=[CommandHandler('cancel', cancel)],
        allow_reentry=True
    )

    application.add_handler(conv_handler)
    application.add_handler(MessageHandler(filters.TEXT & filters.Chat(chat_id=GROUP_CHAT_ID), handle_group_messages))
    application.add_error_handler(error_handler)

    # ConversationHandler برای ایجاد جلسه
    meeting_conv_handler = ConversationHandler(
        entry_points=[MessageHandler(
            filters.TEXT & filters.Chat(chat_id=ADMIN_ID) &
            filters.Regex('^🎯 ایجاد جلسه جدید$'),
            create_meeting_start
        )],
        states={
            MEETING_DATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_meeting_date)],
            MEETING_TIME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_meeting_time)],
            MEETING_DURATION: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_meeting_duration)],
            MEETING_LOCATION: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_meeting_location)],
            MEETING_MANAGER: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_meeting_manager)],
            MEETING_TOPICS: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_meeting_topics)],
            MEETING_INVITEES: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_meeting_invitees)],
            MEETING_LINK: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_meeting_link)],
            MEETING_FILES: [MessageHandler(filters.TEXT | filters.Document.ALL, get_meeting_files)],
            MEETING_CONFIRMATION: [MessageHandler(filters.TEXT & ~filters.COMMAND, confirm_meeting)]
        },
        fallbacks=[CommandHandler('cancel', cancel)],
        allow_reentry=True
    )

    application.add_handler(meeting_conv_handler)

    # اضافه کردن هندلر callback برای دکمه حضور
    application.add_handler(CallbackQueryHandler(
        handle_attendance_callback,
        pattern=r"^attend_"
    ))

    # هندلر عمومی برای ادمین (این باید در آخر باشد)
    application.add_handler(MessageHandler(
        filters.TEXT & filters.Chat(chat_id=ADMIN_ID),
        handle_admin_commands
    ))
    """تنظیم و اضافه کردن هندلرها"""

    # اضافه کردن هندلرهای اصلی
    application.add_handler(MessageHandler(
        filters.TEXT & filters.Chat(chat_id=ADMIN_ID) &
        (filters.Regex(r'✅ تایید کاربر \d+') | filters.Regex(r'❌ رد کاربر \d+')),
        handle_admin_approval
    ))

    application.add_handler(MessageHandler(
        filters.TEXT & filters.Chat(chat_id=ADMIN_ID),
        handle_admin_commands
    ))

    # ConversationHandler برای احراز هویت
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start_command)],
        states={
            NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_name)],
            PHONE: [MessageHandler(filters.CONTACT | (filters.TEXT & ~filters.COMMAND), get_phone)],
            SCREENSHOT: [MessageHandler(filters.PHOTO, get_screenshot)],
            CONFIRMATION: [MessageHandler(filters.TEXT & ~filters.COMMAND, confirm_data)]
        },
        fallbacks=[CommandHandler('cancel', cancel)],
        allow_reentry=True
    )

    application.add_handler(conv_handler)
    application.add_handler(MessageHandler(filters.TEXT & filters.Chat(chat_id=GROUP_CHAT_ID), handle_group_messages))
    application.add_error_handler(error_handler)

    # اضافه کردن هندلر مدیریت جلسات
    application.add_handler(MessageHandler(
        filters.TEXT & filters.Chat(chat_id=ADMIN_ID) &
        (filters.Regex('📅 مدیریت جلسات')),
        manage_meetings
    ))

    application.add_handler(MessageHandler(
        filters.TEXT & filters.Chat(chat_id=ADMIN_ID) &
        (filters.Regex('🎯 ایجاد جلسه جدید')),
        create_meeting_start
    ))

    # ConversationHandler برای ایجاد جلسه
    meeting_conv_handler = ConversationHandler(
        entry_points=[MessageHandler(
            filters.TEXT & filters.Chat(chat_id=ADMIN_ID) &
            filters.Regex('🎯 ایجاد جلسه جدید'),
            create_meeting_start
        )],
        states={
            MEETING_DATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_meeting_date)],
            MEETING_TIME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_meeting_time)],
            MEETING_DURATION: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_meeting_duration)],
            MEETING_LOCATION: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_meeting_location)],
            MEETING_MANAGER: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_meeting_manager)],
            MEETING_TOPICS: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_meeting_topics)],
            MEETING_INVITEES: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_meeting_invitees)],
            MEETING_LINK: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_meeting_link)],
            MEETING_FILES: [MessageHandler(filters.TEXT | filters.Document.ALL, get_meeting_files)],
            MEETING_CONFIRMATION: [MessageHandler(filters.TEXT & ~filters.COMMAND, confirm_meeting)]
        },
        fallbacks=[CommandHandler('cancel', cancel)],
        allow_reentry=True
    )

    application.add_handler(meeting_conv_handler)

    # اضافه کردن هندلر callback برای دکمه حضور
    application.add_handler(CallbackQueryHandler(
        handle_attendance_callback,
        pattern=r"^attend_"
    ))

# راه‌اندازی اولیه
setup_handlers()
load_bot_state()

def main():
    """تابع اصلی برای اجرای ربات"""
    print("🤖 Starting Telegram Bot...")
    
    # اجرای polling (مناسب برای GitHub Actions)
    application.run_polling(
        allowed_updates=Update.ALL_TYPES,
        drop_pending_updates=True
    )

if __name__ == '__main__':
    main()
