import os
import json
import pandas as pd
import requests
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes, ConversationHandler

# ============================================================
# توکن ربات و تنظیمات اولیه
# ============================================================
TOKEN = "8918702072:AAGTHxPdLGLan_QzrJkQR_4uJ_3X5fZ6rpM"
LATITUDE = 33.88472
LONGITUDE = 49.35167
DATA_FILE = "astaneh_weather_data.csv"
PROFILE_FILE = "farm_profile.json"
IRRIGATION_FILE = "irrigation_data.json"

# ============================================================
# پایگاه داده محصولات
# ============================================================
CROP_COEFFICIENTS = {
    "wheat": {"name": "گندم", "type": "annual", "kc_initial": 0.3, "kc_mid": 1.15, "kc_late": 0.4, "growth_days": 150},
    "barley": {"name": "جو", "type": "annual", "kc_initial": 0.3, "kc_mid": 1.1, "kc_late": 0.4, "growth_days": 140},
    "corn": {"name": "ذرت", "type": "annual", "kc_initial": 0.3, "kc_mid": 1.2, "kc_late": 0.6, "growth_days": 120},
    "rice": {"name": "برنج", "type": "annual", "kc_initial": 1.05, "kc_mid": 1.2, "kc_late": 0.9, "growth_days": 130},
    "potato": {"name": "سیب زمینی", "type": "annual", "kc_initial": 0.4, "kc_mid": 1.1, "kc_late": 0.7, "growth_days": 120},
    "tomato": {"name": "گوجه فرنگی", "type": "annual", "kc_initial": 0.4, "kc_mid": 1.15, "kc_late": 0.7, "growth_days": 130},
    "alfalfa": {"name": "یونجه", "type": "annual", "kc_initial": 0.4, "kc_mid": 0.95, "kc_late": 0.85, "growth_days": 180},
    "canola": {"name": "کلزا", "type": "annual", "kc_initial": 0.35, "kc_mid": 1.1, "kc_late": 0.45, "growth_days": 160},
    "sugar_beet": {"name": "چغندرقند", "type": "annual", "kc_initial": 0.35, "kc_mid": 1.2, "kc_late": 0.7, "growth_days": 170},
    "sunflower": {"name": "آفتابگردان", "type": "annual", "kc_initial": 0.35, "kc_mid": 1.15, "kc_late": 0.5, "growth_days": 140},
    "soybean": {"name": "سویا", "type": "annual", "kc_initial": 0.4, "kc_mid": 1.15, "kc_late": 0.5, "growth_days": 130},
    "walnut": {"name": "گردو", "type": "perennial", "kc_initial": 0.5, "kc_mid": 1.1, "kc_late": 0.65, "growth_days": 200},
    "apple": {"name": "سیب", "type": "perennial", "kc_initial": 0.5, "kc_mid": 0.95, "kc_late": 0.85, "growth_days": 210},
    "peach": {"name": "هلو", "type": "perennial", "kc_initial": 0.5, "kc_mid": 0.9, "kc_late": 0.85, "growth_days": 190},
    "cherry": {"name": "گیلاس", "type": "perennial", "kc_initial": 0.5, "kc_mid": 0.9, "kc_late": 0.85, "growth_days": 180},
    "pomegranate": {"name": "انار", "type": "perennial", "kc_initial": 0.4, "kc_mid": 1.0, "kc_late": 0.75, "growth_days": 200},
    "olive": {"name": "زیتون", "type": "perennial", "kc_initial": 0.45, "kc_mid": 0.65, "kc_late": 0.6, "growth_days": 210},
    "grape": {"name": "انگور", "type": "perennial", "kc_initial": 0.3, "kc_mid": 0.85, "kc_late": 0.6, "growth_days": 170},
    "almond": {"name": "بادام", "type": "perennial", "kc_initial": 0.5, "kc_mid": 0.9, "kc_late": 0.65, "growth_days": 200},
    "pistachio": {"name": "پسته", "type": "perennial", "kc_initial": 0.4, "kc_mid": 0.9, "kc_late": 0.6, "growth_days": 210},
    "orange": {"name": "پرتقال", "type": "perennial", "kc_initial": 0.5, "kc_mid": 0.7, "kc_late": 0.65, "growth_days": 240},
}

SOIL_COEFFICIENTS = {
    "sandy": {"name": "شنی", "factor": 0.85, "description": "زهکشی سریع، نیاز به آبیاری مکرر"},
    "sandy_loam": {"name": "ماسه و شن", "factor": 0.95, "description": "زهکشی خوب، متوسط"},
    "loamy": {"name": "لومی", "factor": 1.0, "description": "ایده‌ال برای کشاورزی"},
    "clay": {"name": "رسی", "factor": 1.1, "description": "نگهداری آب بالا، زهکشی کم"},
}

# ============================================================
# دانشنامه آفات و بیماری‌ها با سموم پیشنهادی
# ============================================================
PEST_DISEASE_DB = {
    "wheat": [
        {"disease": "فوزاریوم سنبله (Fusarium Head Blight)", "season": "اواخر بهار", "month_range": (4, 5),
         "conditions": "بارندگی در زمان گلدهی، رطوبت بالا", "fungicide": "Miravis Ace, Prosaro Pro, Sphaerex [citation:1]",
         "dosage": "طبق دستور", "phi": 30, "growth_stage": "گلدهی (Feekes 10.5.1) [citation:2]"},
        {"disease": "زنگ زرد (Stripe Rust)", "season": "اوایل بهار", "month_range": (3, 5),
         "conditions": "هوای خنک، رطوبت بالا", "fungicide": "Plaxium (isoflucypram + fluopyram + prothioconazole) [citation:5]",
         "dosage": "1.5 L/ha", "phi": 35, "growth_stage": "پرچم تا گلدهی"},
        {"disease": "زنگ قهوه‌ای (Leaf Rust)", "season": "بهار تا تابستان", "month_range": (4, 7),
         "conditions": "گرم و مرطوب", "fungicide": "SEGURIS Flexi (isopyrazam) [citation:4]",
         "dosage": "600 mL/ha", "phi": 42, "growth_stage": "پیشگیرانه"},
        {"disease": "سپتوریا برگ (Septoria tritici)", "season": "اواخر بهار تا اوایل تابستان", "month_range": (4, 6),
         "conditions": "بارندگی، رطوبت بالا", "fungicide": "SEGURIS Flexi [citation:4]",
         "dosage": "1000 mL/ha", "phi": 42, "growth_stage": "ساقه‌رفتن تا سنبله‌دهی"},
    ],
    "walnut": [
        {"disease": "بلایت باکتریایی (Bacterial Blight)", "season": "بهار", "month_range": (3, 5),
         "conditions": "بارندگی بهاری", "fungicide": "مس + مانکوزب [citation:7]",
         "dosage": "طبق دستور", "phi": 14, "growth_stage": "باز شدن جوانه تا تشکیل میوه"},
        {"disease": "شته گردو (Walnut Aphid)", "season": "بهار تا تابستان", "month_range": (4, 8),
         "conditions": "هوای گرم", "insecticide": "Chloropyriphos [citation:7]",
         "dosage": "200ml/100L", "phi": 21, "growth_stage": "رشد فعال"},
        {"disease": "کنه گال (Blister Mite)", "season": "بهار", "month_range": (4, 6),
         "conditions": "هوای خشک", "insecticide": "Chloropyriphos [citation:7]",
         "dosage": "100ml/100L", "phi": 21, "growth_stage": "قبل از گلدهی"},
    ],
    "apple": [
        {"disease": "سیب (Apple Scab)", "season": "بهار", "month_range": (3, 5),
         "conditions": "بارندگی، رطوبت بالا", "fungicide": "SEGURIS Flexi + DMI [citation:4]",
         "dosage": "80ml/100L", "phi": 35, "growth_stage": "خوشه فشرده تا 90% گلبرگ ریزی"},
        {"disease": "سفیدک پودری (Powdery Mildew)", "season": "بهار تا تابستان", "month_range": (4, 7),
         "conditions": "هوای گرم و خشک", "fungicide": "SEGURIS Flexi [citation:4]",
         "dosage": "80ml/100L", "phi": 35, "growth_stage": "خوشه فشرده تا 90% گلبرگ ریزی"},
        {"disease": "شته سیب (Apple Aphid)", "season": "بهار", "month_range": (4, 6),
         "conditions": "رشد جدید", "insecticide": "Phosalone + Methyl Dimeton [citation:7]",
         "dosage": "140ml/100L + 80ml/100L", "phi": 14, "growth_stage": "بعد از گلدهی"},
    ],
    "grape": [
        {"disease": "سفیدک پودری (Powdery Mildew)", "season": "بهار تا تابستان", "month_range": (5, 8),
         "conditions": "هوای گرم و خشک", "fungicide": "گوگرد + تبوکونازول",
         "dosage": "طبق دستور", "phi": 14, "growth_stage": "رشد اولیه تا تشکیل خوشه"},
        {"disease": "سفیدک کرکی (Downy Mildew)", "season": "بهار تا تابستان", "month_range": (5, 7),
         "conditions": "بارندگی، رطوبت بالا", "fungicide": "مانکوزب + مس", "dosage": "طبق دستور", "phi": 21, "growth_stage": "قبل از گلدهی"},
    ],
}

SPRAY_CONDITIONS = {
    'max_wind_speed': 5.0,
    'min_temp': 10.0,
    'max_temp': 28.0,
    'min_humidity': 40.0,
    'max_humidity': 75.0,
    'max_uv': 5.0,
    'good_hours_morning': (6, 10),
    'good_hours_evening': (16, 19)
}

# ============================================================
# توابع کمکی
# ============================================================
def load_profile():
    if os.path.exists(PROFILE_FILE):
        with open(PROFILE_FILE, 'r') as f:
            return json.load(f)
    return None

def save_profile(profile):
    with open(PROFILE_FILE, 'w') as f:
        json.dump(profile, f, indent=4)

def load_irrigation_data():
    if os.path.exists(IRRIGATION_FILE):
        with open(IRRIGATION_FILE, 'r') as f:
            return json.load(f)
    return {"interval_days": None, "last_irrigation": None}

def save_irrigation_data(data):
    with open(IRRIGATION_FILE, 'w') as f:
        json.dump(data, f, indent=4)

def get_crop_stage(planting_date_str, crop_type):
    if not planting_date_str or planting_date_str == "unknown":
        return "mid"
    try:
        planting = datetime.strptime(planting_date_str, "%Y-%m-%d")
        days_passed = (datetime.now() - planting).days
        growth_days = CROP_COEFFICIENTS.get(crop_type, {}).get("growth_days", 150)
        
        if days_passed < growth_days * 0.3:
            return "initial"
        elif days_passed < growth_days * 0.7:
            return "mid"
        else:
            return "late"
    except:
        return "mid"

def get_kc(crop_type, stage):
    crop_data = CROP_COEFFICIENTS.get(crop_type, {})
    if stage == "initial":
        return crop_data.get("kc_initial", 0.5)
    elif stage == "mid":
        return crop_data.get("kc_mid", 0.9)
    else:
        return crop_data.get("kc_late", 0.7)

def calculate_water_requirement(eto, crop_type, soil_type, planting_date, crop_age_years=1):
    stage = get_crop_stage(planting_date, crop_type)
    kc = get_kc(crop_type, stage)
    ks = SOIL_COEFFICIENTS.get(soil_type, {}).get("factor", 1.0)
    
    age_factor = 1.0
    if CROP_COEFFICIENTS.get(crop_type, {}).get("type") == "perennial":
        if crop_age_years < 3:
            age_factor = 0.5
        elif crop_age_years < 6:
            age_factor = 0.75
        else:
            age_factor = 1.0
    
    etc = eto * kc * ks * age_factor
    return round(etc, 2), stage, kc, ks, age_factor

def get_fertilizer_advice(crop_type, stage):
    fertilizer_table = {
        "wheat": {"initial": "NPK 20-20-0 + نیتروژن پایه", "mid": "NPK 30-0-0 (نیتروژن)", "late": "NPK 0-0-50"},
        "barley": {"initial": "NPK 20-20-0", "mid": "NPK 30-0-0", "late": "NPK 0-0-40"},
        "corn": {"initial": "NPK 20-20-0", "mid": "NPK 30-0-0", "late": "NPK 0-0-60"},
        "rice": {"initial": "NPK 20-20-0", "mid": "NPK 30-0-0", "late": "NPK 0-0-50"},
        "potato": {"initial": "NPK 15-15-15", "mid": "NPK 20-20-20", "late": "NPK 0-15-45"},
        "tomato": {"initial": "NPK 15-15-15", "mid": "NPK 10-20-30", "late": "NPK 0-10-40"},
        "alfalfa": {"initial": "NPK 10-20-20", "mid": "NPK 0-0-50", "late": "NPK 0-20-30"},
        "canola": {"initial": "NPK 20-20-0", "mid": "NPK 30-0-0", "late": "NPK 0-0-50"},
        "sugar_beet": {"initial": "NPK 20-20-20", "mid": "NPK 30-0-0", "late": "NPK 0-0-50"},
        "sunflower": {"initial": "NPK 20-20-0", "mid": "NPK 30-0-0", "late": "NPK 0-0-60"},
        "soybean": {"initial": "NPK 10-20-20", "mid": "NPK 0-0-40", "late": "NPK 0-0-40"},
        "walnut": {"initial": "NPK 20-20-20 + روی", "mid": "NPK 15-5-30 + پتاسیم بالا", "late": "NPK 0-20-50 + پتاسیم"},
        "apple": {"initial": "NPK 20-20-20", "mid": "NPK 12-12-36", "late": "NPK 0-20-50"},
        "peach": {"initial": "NPK 20-20-20", "mid": "NPK 12-12-36", "late": "NPK 0-20-50"},
        "cherry": {"initial": "NPK 20-20-20", "mid": "NPK 12-12-36", "late": "NPK 0-20-50"},
        "pomegranate": {"initial": "NPK 15-15-15", "mid": "NPK 10-20-30", "late": "NPK 0-15-45"},
        "olive": {"initial": "NPK 15-15-15", "mid": "NPK 10-20-30", "late": "NPK 0-15-45"},
        "grape": {"initial": "NPK 15-15-15", "mid": "NPK 10-20-30", "late": "NPK 0-15-45"},
        "almond": {"initial": "NPK 20-20-20", "mid": "NPK 15-5-30", "late": "NPK 0-20-50"},
        "pistachio": {"initial": "NPK 15-15-15", "mid": "NPK 10-20-30", "late": "NPK 0-15-45"},
        "orange": {"initial": "NPK 15-15-15", "mid": "NPK 12-12-36", "late": "NPK 0-15-45"},
    }
    stage_persian = {"initial": "رشد رویشی", "mid": "گلدهی/میوه‌دهی", "late": "رسیدن"}
    fertilizer = fertilizer_table.get(crop_type, {}).get(stage, "NPK 20-20-20 (کود کامل)")
    return fertilizer, stage_persian.get(stage, stage)

def get_pest_disease_advice(crop_type, current_month):
    """دریافت آفات و بیماری‌های فعال برای محصول مورد نظر"""
    pests = PEST_DISEASE_DB.get(crop_type, [])
    active_pests = []
    for pest in pests:
        month_min, month_max = pest.get("month_range", (1, 12))
        if month_min <= current_month <= month_max:
            active_pests.append(pest)
    return active_pests

def check_hour_conditions(temp, humidity, wind, uv):
    issues = []
    if wind > SPRAY_CONDITIONS['max_wind_speed']:
        issues.append(f"💨 باد شدید ({wind:.1f} m/s)")
    if temp < SPRAY_CONDITIONS['min_temp']:
        issues.append(f"🌡️ دمای پایین ({temp:.1f}°C)")
    elif temp > SPRAY_CONDITIONS['max_temp']:
        issues.append(f"🌡️ دمای بالا ({temp:.1f}°C)")
    if humidity < SPRAY_CONDITIONS['min_humidity']:
        issues.append(f"💧 رطوبت پایین ({humidity:.0f}%)")
    elif humidity > SPRAY_CONDITIONS['max_humidity']:
        issues.append(f"💧 رطوبت بالا ({humidity:.0f}%)")
    if uv > SPRAY_CONDITIONS['max_uv']:
        issues.append(f"☀️ تابش شدید (UV {uv:.1f})")
    score = max(0, 10 - len(issues))
    return issues, score

def fetch_weather_forecast():
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": LATITUDE,
        "longitude": LONGITUDE,
        "hourly": ["temperature_2m", "relative_humidity_2m", "precipitation", "wind_speed_10m", "uv_index"],
        "timezone": "auto",
        "forecast_days": 7
    }
    response = requests.get(url, params=params)
    data = response.json()
    df = pd.DataFrame(data['hourly'])
    df['time'] = pd.to_datetime(df['time'])
    df.rename(columns={
        'temperature_2m': 'temp',
        'relative_humidity_2m': 'humidity',
        'precipitation': 'rain',
        'wind_speed_10m': 'wind',
        'uv_index': 'uv'
    }, inplace=True)
    return df

def fetch_eto():
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": LATITUDE, "longitude": LONGITUDE,
        "daily": ["et0_fao_evapotranspiration"],
        "timezone": "auto", "forecast_days": 1
    }
    try:
        response = requests.get(url, params=params, timeout=30)
        data = response.json()
        return data['daily']['et0_fao_evapotranspiration'][0]
    except:
        return 4.0

def fetch_forecast_daily():
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": LATITUDE, "longitude": LONGITUDE,
        "daily": ["temperature_2m_max", "temperature_2m_min", "precipitation_sum", "wind_speed_10m_max", "et0_fao_evapotranspiration"],
        "timezone": "auto", "forecast_days": 7
    }
    response = requests.get(url, params=params)
    data = response.json()
    df = pd.DataFrame(data['daily'])
    df['time'] = pd.to_datetime(df['time'])
    return df

def get_best_spray_times(df):
    best_slots = []
    for idx, row in df.iterrows():
        hour = row['time'].hour
        is_good_hour = (
            (SPRAY_CONDITIONS['good_hours_morning'][0] <= hour < SPRAY_CONDITIONS['good_hours_morning'][1]) or
            (SPRAY_CONDITIONS['good_hours_evening'][0] <= hour < SPRAY_CONDITIONS['good_hours_evening'][1])
        )
        if not is_good_hour:
            continue
        issues, score = check_hour_conditions(row['temp'], row['humidity'], row['wind'], row['uv'])
        best_slots.append({
            'time': row['time'],
            'temp': row['temp'],
            'humidity': row['humidity'],
            'wind': row['wind'],
            'rain': row['rain'],
            'uv': row['uv'],
            'issues': issues,
            'score': score
        })
    best_slots.sort(key=lambda x: x['score'], reverse=True)
    return best_slots[:10]

# ============================================================
# منوهای ربات
# ============================================================
def get_main_menu():
    keyboard = [
        [InlineKeyboardButton("📅 پیش‌بینی ۷ روزه هوا", callback_data="forecast")],
        [InlineKeyboardButton("🌿 وضعیت سمپاشی", callback_data="spray")],
        [InlineKeyboardButton("🌦️ وضعیت فعلی هوا", callback_data="weather")],
        [InlineKeyboardButton("🚿 مدیریت آبیاری", callback_data="irrigation_menu")],
        [InlineKeyboardButton("📊 آمار دیتاست", callback_data="status")],
        [InlineKeyboardButton("⚙️ تنظیمات مزرعه", callback_data="farm_settings")],
        [InlineKeyboardButton("🔄 به‌روزرسانی داده", callback_data="update")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_farm_settings_menu():
    keyboard = [
        [InlineKeyboardButton("🌾 ثبت/ویرایش اطلاعات مزرعه", callback_data="edit_farm_profile")],
        [InlineKeyboardButton("📋 مشاهده پروفایل مزرعه", callback_data="view_farm_profile")],
        [InlineKeyboardButton("💧 محاسبه نیاز آبی روزانه", callback_data="water_requirement")],
        [InlineKeyboardButton("🧪 پیشنهاد کود هوشمند", callback_data="fertilizer_advice")],
        [InlineKeyboardButton("🔙 بازگشت به منوی اصلی", callback_data="main_menu")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_irrigation_menu():
    keyboard = [
        [InlineKeyboardButton("📝 تنظیم بازه آبیاری", callback_data="set_irrigation_interval")],
        [InlineKeyboardButton("📅 ثبت آخرین آبیاری", callback_data="set_last_irrigation")],
        [InlineKeyboardButton("📊 وضعیت آبیاری", callback_data="show_irrigation_status")],
        [InlineKeyboardButton("🔙 بازگشت به منوی اصلی", callback_data="main_menu")]
    ]
    return InlineKeyboardMarkup(keyboard)

# ============================================================
# هندلرهای منوی اصلی
# ============================================================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🌾 **ربات هوشمند کشاورزی آستانه**\n\n"
        "لطفاً یکی از گزینه‌های زیر را انتخاب کنید:",
        reply_markup=get_main_menu(), parse_mode='Markdown'
    )

async def main_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "🌾 **ربات هوشمند کشاورزی آستانه**\n\nلطفاً یکی از گزینه‌های زیر را انتخاب کنید:",
        reply_markup=get_main_menu(), parse_mode='Markdown'
    )

async def forecast_7d(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("🔄 در حال دریافت پیش‌بینی ۷ روزه...")
    try:
        df = fetch_forecast_daily()
        message = "📅 **پیش‌بینی ۷ روزه هوای آستانه**\n\n"
        for _, day in df.iterrows():
            message += (
                f"📆 {day['time'].strftime('%A %Y-%m-%d')}\n"
                f"   🌡️ دما: {day['temperature_2m_min']:.0f}°C ~ {day['temperature_2m_max']:.0f}°C\n"
                f"   🌧️ بارش: {day['precipitation_sum']:.1f} mm\n"
                f"   💨 باد: {day['wind_speed_10m_max']:.1f} m/s\n"
                f"   💧 ETo: {day['et0_fao_evapotranspiration']:.1f} mm\n\n"
            )
        await query.edit_message_text(message, parse_mode='Markdown')
        await query.message.reply_text("📋 **بازگشت به منوی اصلی:**", reply_markup=get_main_menu())
    except Exception as e:
        await query.edit_message_text(f"❌ خطا: {e}")
        await query.message.reply_text("📋 بازگشت به منو:", reply_markup=get_main_menu())

async def current_weather(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("🔄 در حال دریافت وضعیت فعلی هوا...")
    try:
        url = "https://api.open-meteo.com/v1/forecast"
        params = {
            "latitude": LATITUDE, "longitude": LONGITUDE,
            "current_weather": True,
            "timezone": "auto"
        }
        response = requests.get(url, params=params)
        data = response.json()
        current = data['current_weather']
        
        message = (
            f"🌦️ **وضعیت هوای آستانه (لحظه حال)**\n"
            f"🕒 {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"
            f"🌡️ دما: {current['temperature']:.1f}°C\n"
            f"💨 سرعت باد: {current['windspeed']:.1f} m/s\n"
            f"🧭 جهت باد: {current.get('winddirection', 'نامشخص')}°"
        )
        await query.edit_message_text(message, parse_mode='Markdown')
        await query.message.reply_text("📋 **بازگشت به منوی اصلی:**", reply_markup=get_main_menu())
    except Exception as e:
        await query.edit_message_text(f"❌ خطا: {e}")
        await query.message.reply_text("📋 بازگشت به منو:", reply_markup=get_main_menu())

# ============================================================
# وضعیت سمپاشی هوشمند (با آفات و بیماری‌ها)
# ============================================================
async def spray_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("🔄 در حال بررسی وضعیت سمپاشی و تحلیل ۷ روز آینده...")
    
    profile = load_profile()
    if not profile:
        await query.edit_message_text(
            "❌ ابتدا پروفایل مزرعه را تکمیل کنید.\n"
            "از بخش 'تنظیمات مزرعه' > 'ثبت/ویرایش اطلاعات مزرعه' استفاده کنید.",
            parse_mode='Markdown'
        )
        await query.message.reply_text("📋 بازگشت به منوی اصلی:", reply_markup=get_main_menu())
        return
    
    try:
        df = fetch_weather_forecast()
        now = datetime.now()
        current_month = now.month
        farm = profile.get('farm_profile', {})
        crop_type = farm.get('crop_type', 'walnut')
        crop_info = CROP_COEFFICIENTS.get(crop_type, {})
        planting_date = farm.get('planting_date')
        
        # دریافت آفات و بیماری‌های فعال فصل
        active_pests = get_pest_disease_advice(crop_type, current_month)
        
        # ========== بخش 1: وضعیت فعلی ==========
        current = df.iloc[(df['time'] - now).abs().argsort()[:1]].iloc[0]
        current_issues, current_score = check_hour_conditions(current['temp'], current['humidity'], current['wind'], current['uv'])
        
        if not current_issues:
            current_status = "✅ **وضعیت عالی! شرایط برای سمپاشی در حال حاضر مساعد است.**"
            current_advice = "می‌توانید اقدام به سمپاشی کنید."
        else:
            current_status = "❌ **وضعیت نامناسب. در حال حاضر شرایط برای سمپاشی مساعد نیست.**"
            current_advice = "\n".join([f"• {issue}" for issue in current_issues])
        
        # ========== بخش 2: بهترین زمان‌های ۷ روز آینده ==========
        best_slots = get_best_spray_times(df)
        
        forecast_message = ""
        if best_slots:
            forecast_message = "\n\n⏳ **بهترین زمان‌ها برای سمپاشی در ۷ روز آینده:**\n"
            for i, slot in enumerate(best_slots[:7]):
                date_str = slot['time'].strftime('%A %Y-%m-%d - ساعت %H:%M')
                if slot['score'] >= 9:
                    emoji = "🟢"
                    status_text = "عالی"
                elif slot['score'] >= 7:
                    emoji = "🟡"
                    status_text = "قابل قبول"
                else:
                    emoji = "🟠"
                    status_text = "با احتیاط"
                
                forecast_message += f"\n{emoji} **{date_str}** - {status_text}\n"
                forecast_message += f"   🌡️ دما: {slot['temp']:.1f}°C | 💧 رطوبت: {slot['humidity']:.0f}%\n"
                forecast_message += f"   💨 باد: {slot['wind']:.1f} m/s | ☀️ UV: {slot['uv']:.1f}\n"
                if slot['issues']:
                    forecast_message += f"   ⚠️ {', '.join(slot['issues'])}\n"
        else:
            forecast_message = "\n\n⚠️ **در 7 روز آینده هیچ زمان مناسبی برای سمپاشی پیدا نشد.**"
        
        # ========== بخش 3: آفات و بیماری‌های فعال فصل ==========
        pest_message = ""
        if active_pests:
            pest_message = "\n\n🐛 **آفات و بیماری‌های فعال این فصل:**\n"
            for pest in active_pests:
                pest_message += f"\n🔸 **{pest['disease']}**\n"
                pest_message += f"   📅 زمان: {pest['season']}\n"
                pest_message += f"   🌧️ شرایط مساعد: {pest['conditions']}\n"
                if 'fungicide' in pest:
                    pest_message += f"   💊 سم پیشنهادی: `{pest['fungicide']}`\n"
                if 'insecticide' in pest:
                    pest_message += f"   🧪 حشره‌کش پیشنهادی: `{pest['insecticide']}`\n"
                pest_message += f"   💧 میزان مصرف: {pest['dosage']}\n"
                pest_message += f"   ⏳ فاصله تا برداشت (PHI): {pest['phi']} روز\n"
                pest_message += f"   🌱 مرحله مصرف: {pest['growth_stage']}\n"
        else:
            pest_message = "\n\n✅ **هیچ آفت یا بیماری خاصی برای این محصول در این فصل گزارش نشده است.**"
        
        # ========== بخش 4: راهنمای عمومی سمپاشی ==========
        guide_message = (
            "\n\n📋 **راهنمای سمپاشی:**\n"
            "• بهترین زمان: صبح زود (۶-۱۰) یا عصر (۴-۷)\n"
            "• سرعت باد مجاز: کمتر از ۵ متر بر ثانیه\n"
            "• دمای مناسب: ۱۰ تا ۲۸ درجه سانتی‌گراد\n"
            "• رطوبت مناسب: ۴۰ تا ۷۵ درصد\n"
            "• از سمپاشی در هوای خیلی گرم یا در معرض تابش مستقیم خورشید خودداری کنید [citation:3]\n"
            "• در صورت بارش قریب‌الوقوع، سمپاشی را به تعویق بیندازید [citation:3]\n"
            "• پس از سمپاشی، فاصله امن تا برداشت (PHI) را رعایت کنید"
        )
        
        stage = get_crop_stage(planting_date, crop_type)
        stage_persian = {"initial": "رشد رویشی", "mid": "گلدهی/میوه‌دهی", "late": "رسیدن"}
        
        message = (
            f"🌾 **محصول: {crop_info.get('name', 'ثبت نشده')}**\n"
            f"🌱 مرحله رشد: {stage_persian.get(stage, stage)}\n"
            f"📅 فصل: {['', 'فروردین', 'اردیبهشت', 'خرداد', 'تیر', 'مرداد', 'شهریور', 'مهر', 'آبان', 'آذر', 'دی', 'بهمن', 'اسفند'][current_month]}\n"
            f"🕒 زمان بررسی: {now.strftime('%Y-%m-%d %H:%M')}\n"
            f"{'='*40}\n"
            f"🌿 **وضعیت فعلی:** {current_status}\n"
            f"🔍 {current_advice}"
            f"{forecast_message}"
            f"{pest_message}"
            f"{guide_message}"
        )
        
        await query.edit_message_text(message, parse_mode='Markdown')
        await query.message.reply_text("📋 **بازگشت به منوی اصلی:**", reply_markup=get_main_menu())
        
    except Exception as e:
        await query.edit_message_text(f"❌ خطا در دریافت داده: {e}")
        await query.message.reply_text("📋 بازگشت به منو:", reply_markup=get_main_menu())

# ============================================================
# مدیریت آبیاری
# ============================================================
async def irrigation_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "🚿 **مدیریت آبیاری**\n\nلطفاً یکی از گزینه‌های زیر را انتخاب کنید:",
        reply_markup=get_irrigation_menu(), parse_mode='Markdown'
    )

async def set_irrigation_interval_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "📝 لطفاً **بازه آبیاری** را به تعداد روز وارد کنید.\n"
        "(مثال: 5)\n\n"
        "برای لغو، دستور /cancel را بزنید."
    )
    return 1

async def set_irrigation_interval_end(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        interval = int(update.message.text)
        if interval <= 0:
            raise ValueError
        data = load_irrigation_data()
        data['interval_days'] = interval
        save_irrigation_data(data)
        await update.message.reply_text(f"✅ بازه آبیاری با موفقیت روی **هر {interval} روز یک بار** تنظیم شد.")
    except ValueError:
        await update.message.reply_text("❌ مقدار وارد شده معتبر نیست. لطفاً یک عدد صحیح مثبت وارد کنید.")
        return 1
    await update.message.reply_text("📋 بازگشت به منوی آبیاری:", reply_markup=get_irrigation_menu())
    return ConversationHandler.END

async def set_last_irrigation_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "📅 لطفاً **تاریخ آخرین آبیاری** را به فرمت YYYY-MM-DD وارد کنید:\n"
        "(مثال: 2026-06-07)\n\n"
        "برای لغو، دستور /cancel را بزنید."
    )
    return 2

async def set_last_irrigation_end(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        last_date = datetime.strptime(update.message.text.strip(), "%Y-%m-%d").date()
        data = load_irrigation_data()
        data['last_irrigation'] = last_date.isoformat()
        save_irrigation_data(data)
        await update.message.reply_text(f"✅ تاریخ آخرین آبیاری با موفقیت ثبت شد: {last_date}")
    except ValueError:
        await update.message.reply_text("❌ تاریخ وارد شده معتبر نیست. لطفاً با فرمت YYYY-MM-DD وارد کنید.")
        return 2
    await update.message.reply_text("📋 بازگشت به منوی آبیاری:", reply_markup=get_irrigation_menu())
    return ConversationHandler.END

async def show_irrigation_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    data = load_irrigation_data()
    interval = data.get('interval_days')
    last_irrigation_str = data.get('last_irrigation')
    
    message = "🚿 **وضعیت آبیاری**\n\n"
    
    if interval is None:
        message += "• بازه آبیاری: ❌ تنظیم نشده است\n"
    else:
        message += f"• بازه آبیاری: هر **{interval} روز** یک بار\n"
    
    if last_irrigation_str is None:
        message += "• آخرین آبیاری: ❌ ثبت نشده است\n"
    else:
        last_date = datetime.strptime(last_irrigation_str, "%Y-%m-%d").date()
        days_since = (datetime.now().date() - last_date).days
        message += f"• آخرین آبیاری: {last_date} ({days_since} روز پیش)\n"
        
        if interval:
            days_remaining = max(0, interval - days_since)
            if days_remaining == 0:
                message += f"\n⚠️ **امروز روز آبیاری است!**\n• حتماً آبیاری را انجام دهید."
            else:
                message += f"\n⏳ روزهای باقی‌مانده تا آبیاری بعدی: **{days_remaining} روز**"
    
    await query.edit_message_text(message, parse_mode='Markdown')
    await query.message.reply_text("📋 بازگشت به منوی آبیاری:", reply_markup=get_irrigation_menu())

# ============================================================
# مدیریت مزرعه
# ============================================================
async def farm_settings_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "⚙️ **تنظیمات مزرعه**\n\nلطفاً یکی از گزینه‌های زیر را انتخاب کنید:",
        reply_markup=get_farm_settings_menu(), parse_mode='Markdown'
    )

async def view_farm_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    profile = load_profile()
    if not profile:
        await query.edit_message_text(
            "📭 **پروفایل مزرعه تنظیم نشده است.**\n"
            "لطفاً از بخش 'ثبت/ویرایش اطلاعات مزرعه'، آن را تکمیل کنید.",
            parse_mode='Markdown'
        )
    else:
        farm = profile.get('farm_profile', {})
        crop_info = CROP_COEFFICIENTS.get(farm.get('crop_type', ''), {})
        soil_info = SOIL_COEFFICIENTS.get(farm.get('soil_type', ''), {})
        message = (
            f"🌾 **پروفایل مزرعه**\n\n"
            f"📛 نام: {farm.get('farm_name', 'ثبت نشده')}\n"
            f"📏 مساحت: {farm.get('area_sqm', 0):,} متر مربع\n"
            f"🌱 نوع خاک: {soil_info.get('name', farm.get('soil_type', 'ثبت نشده'))}\n"
            f"🍃 نوع محصول: {crop_info.get('name', farm.get('crop_type', 'ثبت نشده'))}\n"
            f"🌿 نوع کشت: {'درختی' if crop_info.get('type') == 'perennial' else 'زراعی'}\n"
            f"📅 سن محصول: {farm.get('crop_age_years', 0)} سال\n"
            f"📆 تاریخ کاشت: {farm.get('planting_date', 'ثبت نشده')}\n\n"
            f"📋 توضیحات خاک: {soil_info.get('description', '-')}"
        )
        await query.edit_message_text(message, parse_mode='Markdown')
    await query.message.reply_text("📋 **بازگشت به منوی تنظیمات:**", reply_markup=get_farm_settings_menu())

async def water_requirement(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("🔄 در حال محاسبه نیاز آبی روزانه...")
    
    profile = load_profile()
    if not profile:
        await query.edit_message_text(
            "❌ ابتدا پروفایل مزرعه را تکمیل کنید.\n"
            "از بخش 'تنظیمات مزرعه' > 'ثبت/ویرایش اطلاعات مزرعه' استفاده کنید.",
            parse_mode='Markdown'
        )
        await query.message.reply_text("📋 بازگشت به منوی تنظیمات:", reply_markup=get_farm_settings_menu())
        return
    
    farm = profile.get('farm_profile', {})
    soil_type = farm.get('soil_type', 'loamy')
    crop_type = farm.get('crop_type', 'walnut')
    planting_date = farm.get('planting_date')
    crop_age = farm.get('crop_age_years', 1)
    
    try:
        eto = fetch_eto()
        water_need, stage, kc, ks, age_factor = calculate_water_requirement(
            eto, crop_type, soil_type, planting_date, crop_age
        )
        
        crop_info = CROP_COEFFICIENTS.get(crop_type, {})
        soil_info = SOIL_COEFFICIENTS.get(soil_type, {})
        stage_persian = {"initial": "رشد رویشی", "mid": "گلدهی/میوه‌دهی", "late": "رسیدن"}
        
        area = farm.get('area_sqm', 0)
        total_water_liters = round(water_need * area * 1.0)
        
        message = (
            f"💧 **نیاز آبی روزانه محاسبه شده**\n\n"
            f"🌡️ ETo امروز: {eto:.1f} mm\n"
            f"🍃 محصول: {crop_info.get('name', crop_type)}\n"
            f"🌱 مرحله رشد: {stage_persian.get(stage, stage)}\n"
            f"📊 ضریب گیاهی (Kc): {kc}\n"
            f"🟫 ضریب خاک (Ks): {ks} ({soil_info.get('name', soil_type)})\n"
            f"📈 ضریب سنی: {age_factor}\n\n"
            f"📊 **نیاز آبی خالص**: {water_need} میلی‌متر در روز\n"
            f"📏 مساحت مزرعه: {area:,} متر مربع\n"
            f"🚰 **حجم آب مورد نیاز**: {total_water_liters:,} لیتر در روز\n\n"
            f"⚠️ نکته: این مقدار بر اساس شرایط ایده‌آل محاسبه شده است.\n"
            f"بارندگی‌های اخیر و رطوبت فعلی خاک را نیز در نظر بگیرید."
        )
        await query.edit_message_text(message, parse_mode='Markdown')
    except Exception as e:
        await query.edit_message_text(f"❌ خطا در محاسبه: {e}")
    
    await query.message.reply_text("📋 بازگشت به منوی تنظیمات:", reply_markup=get_farm_settings_menu())

async def fertilizer_advice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("🔄 در حال تولید پیشنهاد کود...")
    
    profile = load_profile()
    if not profile:
        await query.edit_message_text("❌ ابتدا پروفایل مزرعه را تکمیل کنید.")
        await query.message.reply_text("📋 بازگشت به منوی تنظیمات:", reply_markup=get_farm_settings_menu())
        return
    
    farm = profile.get('farm_profile', {})
    crop_type = farm.get('crop_type', 'walnut')
    planting_date = farm.get('planting_date')
    age = farm.get('crop_age_years', 1)
    
    stage = get_crop_stage(planting_date, crop_type)
    fertilizer, stage_name = get_fertilizer_advice(crop_type, stage)
    
    crop_info = CROP_COEFFICIENTS.get(crop_type, {})
    
    message = (
        f"🧪 **پیشنهاد کود هوشمند**\n\n"
        f"🍃 محصول: {crop_info.get('name', crop_type)}\n"
        f"🌱 مرحله رشد: {stage_name}\n"
        f"📅 سن گیاه: {age} سال\n\n"
        f"✅ **کود پیشنهادی:** {fertilizer}\n\n"
        f"⚠️ **نکات مهم:**\n"
        f"• کود را هنگام خنکی هوا (صبح زود یا عصر) بدهید.\n"
        f"• بهتر است کود را همزمان با آبیاری (Fertigation) دهید.\n"
        f"• از تماس مستقیم کود با برگ‌ها خودداری کنید."
    )
    await query.edit_message_text(message, parse_mode='Markdown')
    await query.message.reply_text("📋 بازگشت به منوی تنظیمات:", reply_markup=get_farm_settings_menu())

async def dataset_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if not os.path.exists(DATA_FILE):
        await query.edit_message_text(
            "📭 **آمار دیتاست**\n\n"
            "هنوز داده‌ای جمع‌آوری نشده است.\n"
            "لطفاً از دکمه 'به‌روزرسانی داده' استفاده کنید.",
            parse_mode='Markdown'
        )
    else:
        try:
            df = pd.read_csv(DATA_FILE)
            df['time'] = pd.to_datetime(df['time'])
            message = (
                f"📊 **آمار دیتاست هواشناسی آستانه**\n\n"
                f"📅 بازه زمانی: {df['time'].min().strftime('%Y-%m-%d')} تا {df['time'].max().strftime('%Y-%m-%d')}\n"
                f"📈 تعداد رکوردها: {len(df):,}\n"
                f"🌡️ میانگین دما: {df['temp_c'].mean():.1f}°C\n"
                f"💧 میانگین رطوبت: {df['humidity'].mean():.0f}%\n"
                f"🌧️ مجموع بارش: {df['rain_mm'].sum():.1f} mm\n\n"
                f"🕒 آخرین به‌روزرسانی: {df['time'].max().strftime('%Y-%m-%d %H:%M')}"
            )
            await query.edit_message_text(message, parse_mode='Markdown')
        except Exception as e:
            await query.edit_message_text(f"❌ خطا در خواندن دیتاست: {e}")
    
    await query.message.reply_text("📋 **بازگشت به منوی اصلی:**", reply_markup=get_main_menu())

async def update_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("🔄 در حال به‌روزرسانی داده‌های هواشناسی...")
    try:
        df = fetch_weather_forecast()
        df['temp_c'] = df['temp']
        df['humidity'] = df['humidity']
        df['rain_mm'] = df['rain']
        df['wind_ms'] = df['wind']
        df['uv'] = df['uv']
        df.to_csv(DATA_FILE, index=False)
        await query.edit_message_text(f"✅ داده‌ها با موفقیت به‌روز شدند!\n📊 تعداد رکوردها: {len(df)}")
        await query.message.reply_text("📋 **بازگشت به منوی اصلی:**", reply_markup=get_main_menu())
    except Exception as e:
        await query.edit_message_text(f"❌ خطا در به‌روزرسانی: {e}")
        await query.message.reply_text("📋 بازگشت به منو:", reply_markup=get_main_menu())

# ============================================================
# مکالمه تنظیم پروفایل مزرعه
# ============================================================
async def edit_farm_profile_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "📝 **ثبت اطلاعات مزرعه**\n\n"
        "لطفاً **نام مزرعه** را وارد کنید:\n"
        "(مثال: باغ آستانه)"
    )
    return 1

async def edit_farm_profile_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['farm_name'] = update.message.text
    await update.message.reply_text(
        "📏 لطفاً **مساحت مزرعه** را به متر مربع وارد کنید:\n"
        "(مثال: 5000)"
    )
    return 2

async def edit_farm_profile_area(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        context.user_data['area_sqm'] = int(update.message.text)
    except:
        context.user_data['area_sqm'] = 0
    await update.message.reply_text(
        "🌱 **نوع خاک مزرعه خود را انتخاب کنید:**\n"
        "1️⃣ شنی (Sandy)\n"
        "2️⃣ ماسه و شن (Sandy Loam)\n"
        "3️⃣ لومی (Loamy)\n"
        "4️⃣ رسی (Clay)\n\n"
        "لطفاً شماره گزینه را وارد کنید:"
    )
    return 3

async def edit_farm_profile_soil(update: Update, context: ContextTypes.DEFAULT_TYPE):
    soil_map = {"1": "sandy", "2": "sandy_loam", "3": "loamy", "4": "clay"}
    soil_type = soil_map.get(update.message.text.strip(), "loamy")
    context.user_data['soil_type'] = soil_type
    
    crop_list = []
    for key, value in CROP_COEFFICIENTS.items():
        crop_list.append(f"{len(crop_list)+1}️⃣ {value['name']}")
    
    crop_message = "🍃 **نوع محصول خود را انتخاب کنید:**\n\n" + "\n".join(crop_list) + "\n\nلطفاً شماره گزینه را وارد کنید:"
    await update.message.reply_text(crop_message)
    return 4

async def edit_farm_profile_crop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    crop_map = {}
    for i, (key, value) in enumerate(CROP_COEFFICIENTS.items(), 1):
        crop_map[str(i)] = key
    
    crop_type = crop_map.get(update.message.text.strip(), "walnut")
    context.user_data['crop_type'] = crop_type
    
    crop_info = CROP_COEFFICIENTS.get(crop_type, {})
    if crop_info.get('type') == 'perennial':
        await update.message.reply_text(
            "📅 لطفاً **سن محصول** را به سال وارد کنید:\n"
            "(مثال: 5)"
        )
        return 5
    else:
        context.user_data['crop_age_years'] = 1
        await update.message.reply_text(
            "📆 لطفاً **تاریخ کاشت** را به فرمت YYYY-MM-DD وارد کنید:\n"
            "(مثال: 2024-11-15)\n\n"
            "اگر تاریخ دقیق را نمی‌دانید، کلمه 'unknown' را وارد کنید."
        )
        return 6

async def edit_farm_profile_age(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        context.user_data['crop_age_years'] = int(update.message.text)
    except:
        context.user_data['crop_age_years'] = 1
    await update.message.reply_text(
        "📆 لطفاً **تاریخ کاشت** را به فرمت YYYY-MM-DD وارد کنید:\n"
        "(مثال: 2021-03-15)\n\n"
        "اگر تاریخ دقیق را نمی‌دانید، کلمه 'unknown' را وارد کنید."
    )
    return 6

async def edit_farm_profile_planting(update: Update, context: ContextTypes.DEFAULT_TYPE):
    planting_date = update.message.text.strip()
    if planting_date == "unknown":
        planting_date = None
    
    profile = {
        "farm_profile": {
            "farm_name": context.user_data.get('farm_name', 'مزرعه من'),
            "area_sqm": context.user_data.get('area_sqm', 0),
            "soil_type": context.user_data.get('soil_type', 'loamy'),
            "crop_type": context.user_data.get('crop_type', 'walnut'),
            "crop_age_years": context.user_data.get('crop_age_years', 1),
            "planting_date": planting_date
        }
    }
    save_profile(profile)
    await update.message.reply_text("✅ **پروفایل مزرعه با موفقیت ذخیره شد!**")
    await update.message.reply_text("📋 بازگشت به منوی تنظیمات:", reply_markup=get_farm_settings_menu())
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ عملیات لغو شد.")
    await update.message.reply_text("📋 بازگشت به منوی اصلی:", reply_markup=get_main_menu())
    return ConversationHandler.END

# ============================================================
# تابع اصلی
# ============================================================
def main():
    app = Application.builder().token(TOKEN).build()
    
    # هندلرهای منوی اصلی
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(main_menu_callback, pattern="main_menu"))
    app.add_handler(CallbackQueryHandler(forecast_7d, pattern="forecast"))
    app.add_handler(CallbackQueryHandler(spray_status, pattern="spray"))
    app.add_handler(CallbackQueryHandler(current_weather, pattern="weather"))
    app.add_handler(CallbackQueryHandler(irrigation_menu, pattern="irrigation_menu"))
    app.add_handler(CallbackQueryHandler(dataset_status, pattern="status"))
    app.add_handler(CallbackQueryHandler(farm_settings_menu, pattern="farm_settings"))
    app.add_handler(CallbackQueryHandler(view_farm_profile, pattern="view_farm_profile"))
    app.add_handler(CallbackQueryHandler(water_requirement, pattern="water_requirement"))
    app.add_handler(CallbackQueryHandler(fertilizer_advice, pattern="fertilizer_advice"))
    app.add_handler(CallbackQueryHandler(update_data, pattern="update"))
    app.add_handler(CallbackQueryHandler(show_irrigation_status, pattern="show_irrigation_status"))
    
    # هندلر مکالمه تنظیم بازه آبیاری
    interval_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(set_irrigation_interval_start, pattern="set_irrigation_interval")],
        states={1: [MessageHandler(filters.TEXT & ~filters.COMMAND, set_irrigation_interval_end)]},
        fallbacks=[CommandHandler("cancel", cancel)]
    )
    app.add_handler(interval_conv)
    
    # هندلر مکالمه ثبت آخرین آبیاری
    last_irrigation_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(set_last_irrigation_start, pattern="set_last_irrigation")],
        states={2: [MessageHandler(filters.TEXT & ~filters.COMMAND, set_last_irrigation_end)]},
        fallbacks=[CommandHandler("cancel", cancel)]
    )
    app.add_handler(last_irrigation_conv)
    
    # هندلر مکالمه تنظیم پروفایل مزرعه
    profile_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(edit_farm_profile_start, pattern="edit_farm_profile")],
        states={
            1: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_farm_profile_name)],
            2: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_farm_profile_area)],
            3: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_farm_profile_soil)],
            4: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_farm_profile_crop)],
            5: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_farm_profile_age)],
            6: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_farm_profile_planting)],
        },
        fallbacks=[CommandHandler("cancel", cancel)]
    )
    app.add_handler(profile_conv)
    
    print("=" * 60)
    print("🤖 ربات هوشمند کشاورزی آستانه - نسخه نهایی")
    print("=" * 60)
    print("✅ قابلیت‌های فعال:")
    print("   • پیش‌بینی ۷ روزه هوا")
    print("   • وضعیت سمپاشی (تحلیل هوا + آفات و بیماری‌های فصلی + بهترین زمان‌ها)")
    print("   • وضعیت فعلی هوا")
    print("   • مدیریت آبیاری (تنظیم بازه + ثبت آخرین آبیاری + نمایش وضعیت)")
    print("   • آمار دیتاست")
    print("   • تنظیمات مزرعه (20 محصول)")
    print("   • محاسبه نیاز آبی علمی (FAO)")
    print("   • پیشنهاد کود هوشمند")
    print("=" * 60)
    app.run_polling()

if __name__ == "__main__":
    main()