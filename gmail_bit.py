import imaplib
import email
from datetime import datetime, timedelta
import html2text
import os
import re
import pandas as pd
from dotenv import load_dotenv
from flask import Flask, request, jsonify
import requests
app = Flask(__name__)
import time
import sys
# --- Configuration ---

# Загрузка переменных окружения из .env файла
load_dotenv("read_email.env")
TOKEN = os.getenv("TOKEN")  # Replace with your Telegram bot token
MASTER_ID =int(os.getenv("MASTER_ID"))
# WEBHOOK_BASE_URL - this is your public domain, without the trailing path
WEBHOOK_BASE_URL = os.getenv("WEBHOOK_BASE_URL")  # For example: https://yourdomain.com



# Form the full webhook URL with the token
WEBHOOK_URL = f"{WEBHOOK_BASE_URL}/{TOKEN}"


# Re-define or confirm your send_message function (it should already be good for MarkdownV2)
def send_message(chat_id, text):
    """Sends a message via Telegram API"""
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {
        'chat_id': chat_id,
        'text': text,
        'parse_mode': 'HTML'  # IMPORTANT: Ensure this is here for your formatted text
    }
    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        print(f"Message successfully sent to chat {chat_id}.")
        return response.json()
    except requests.exceptions.RequestException as e:
        print(text)
        print(f"Error sending message to chat {chat_id}: {e}")
        # sys.exit()
        return None


def split_message_into_chunks(text, max_length=2000):
    """
    Splits a long string into chunks that adhere to Telegram's message length limit.
    It tries to split at natural breaks (like newlines) if possible.

    Args:
        text (str): The long string to be split.
        max_length (int): The maximum desired length for each chunk.
                          Telegram's limit is 4096, but using a slightly
                          smaller number (e.g., 4000) is safer to account
                          for formatting overhead or future small changes.

    Returns:
        list: A list of strings, where each string is a message chunk.
    """
    if len(text) <= max_length:
        return [text]

    chunks = []
    current_index = 0
    while current_index < len(text):
        chunk_end = min(current_index + max_length, len(text))

        # Try to find a natural split point (e.g., newline) near the max_length
        if chunk_end < len(text):  # If not at the very end of the text
            # Search backwards from chunk_end for a newline or paragraph break
            # This helps avoid cutting words in half
            split_point = text.rfind('\n\n', current_index, chunk_end)
            if split_point == -1:  # No double newline, try single newline
                split_point = text.rfind('\n', current_index, chunk_end)

            if split_point != -1 and split_point > current_index:
                # If a split point was found within the current chunk range, use it
                chunk = text[current_index:split_point]
                current_index = split_point
            else:
                # If no natural split point found, or it's too close to current_index,
                # just split at max_length.
                chunk = text[current_index:chunk_end]
                current_index = chunk_end
        else:
            # If the remaining text is within max_length, just take it
            chunk = text[current_index:chunk_end]
            current_index = chunk_end

        # Remove any leading/trailing whitespace from the chunk
        chunks.append(chunk.strip())

    return chunks
# Your new function to send potentially long messages
def send_long_message(chat_id, long_text):
    """
    Splits a long message into chunks and sends them sequentially to Telegram.
    """
    message_chunks = split_message_into_chunks(long_text, max_length=2000)

    for i, chunk in enumerate(message_chunks):
        # Optional: Add page numbers if there's more than one chunk
        if len(message_chunks) > 1:
            header = f"Page {i + 1}/{len(message_chunks)}\n\n"
            # If the chunk is just separator or very short, add header carefully
            if not chunk.startswith("✨ *New Job Openings!*") and not chunk.startswith("🌐"):
                chunk = header + chunk
            # Else, the initial header of the first message might be sufficient
            # Or you can decide to add it always.

        print(f"Sending chunk {i + 1} of {len(message_chunks)} to {chat_id}")
        send_message(chat_id, chunk)
        # You might want to add a small delay here if sending many messages quickly

        time.sleep(0.5)


def parse_start_command(text):
    """
    Парсит команду вида '/start <arg1> <arg2>' и возвращает два аргумента.

    Args:
        text (str): Текст команды, например '/start 20250609 20250610'

    Returns:
        tuple: (arg1, arg2) если всё ок, иначе (None, None)
    """
    parts = text.strip().split()

    if len(parts) == 3 and parts[0] == '/check':
        var1 = parts[1]
        var2 = parts[2]
        return str(var1),str(var2)
    else:
        return START_DATE,END_DATE


# Dynamically create the webhook route based on the token
@app.route(f'/{TOKEN}', methods=['POST'])
def webhook():
    # ATTENTION: Without a secret token, the webhook is less secure!
    # Anyone could send requests to your webhook URL.
    # global START_DATE,END_DATE
    update = request.json
    if not update:
        print("Warning: Received empty update.")
        return jsonify(success=False)

    print(f"Received update: {update}")

    # Extract data from the message
    message = update.get('message')
    if not message:
        # This might be another type of update (e.g., edited_message, channel_post, etc.)
        print("Received update without 'message' field. Skipping.")
        return jsonify(success=True)

    chat_id = message.get('chat', {}).get('id')
    text = message.get('text', '').strip()
    user_id = message.get('from', {}).get('id')

    if chat_id is None or user_id is None:
        print("Warning: Could not extract chat_id or user_id from message.")
        return jsonify(success=False)

    print(f"Message from user {user_id} in chat {chat_id}: '{text}'")

    # Check if the message is from the master and contains the /check command
    if chat_id == MASTER_ID:
        if  '/check' in text:
            START_DATE,END_DATE=parse_start_command(text)
            # START_DATE = '20250610'  # Формат: YYYYMMDD
            # END_DATE = '20250610'  # Формат: YYYYMMDD (включительно)
            print("START_DATE",START_DATE)
            print("END_DATE",END_DATE)

            text_to_bot=chec_email(START_DATE,END_DATE)
            print("TEXT TIO BOT")
            print(text_to_bot)
            # send_message(chat_id, text_to_bot)
            send_long_message(chat_id, text_to_bot)
            # send_long_message(chat_id, "mlala")
        else:
            send_message(chat_id, "⛔ Available commands:\n/check - check bot status")
    # else:
        # Optionally: you can ignore messages from other users
        # Or send them a message indicating the bot is for the master only
        # print(f"Ignoring message from unauthorized user: {user_id}")
        # send_message(chat_id, "Sorry, this bot is only for the administrator.")

    return jsonify(success=True)

@app.route('/set_webhook', methods=['GET'])
def set_webhook():
    """Sets the Telegram webhook"""
    url = f"https://api.telegram.org/bot{TOKEN}/setWebhook"
    params = {
        'url': WEBHOOK_URL
    }
    # print(f"Attempting to set webhook to: {WEBHOOK_URL}")
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        json_response = response.json()
        # print(f"Response from Telegram for webhook setup: {json_response}")
        return jsonify(json_response)
    except requests.exceptions.RequestException as e:
        print(f"Error setting webhook: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/')
def index():
    """Main page, can be used to check if Flask is running"""
    return "Bot is running! Use Telegram to interact or go to /set_webhook to set up the webhook."


EMAIL = os.getenv("EMAIL_ID")
APP_PASSWORD = os.getenv("APP_PASS")

LABEL = 'JobOfertas'  # Название метки (точно как в Gmail)
# START_DATE = '20250610'  # Формат: YYYYMMDD
# END_DATE = '20250610'    # Формат: YYYYMMDD (включительно)


# Преобразование даты в формат IMAP
def convert_date(digits):
    date_obj = datetime.strptime(digits, '%Y%m%d')
    return date_obj.strftime('%d-%b-%Y')
def get_text(msg):
    body = ""
    html_body = ""

    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            content_disposition = str(part.get("Content-Disposition", "")).lower()

            if "attachment" in content_disposition:
                continue

            payload = part.get_payload(decode=True)
            if not payload:
                continue

            charset = part.get_content_charset()
            if charset:
                try:
                    decoded = payload.decode(charset, errors='replace')
                    if content_type == "text/plain":
                        body = decoded
                        break
                    elif content_type == "text/html" and not body:
                        html_body = decoded
                except UnicodeDecodeError:
                    continue
    else:
        payload = msg.get_payload(decode=True)
        if payload:
            charset = msg.get_content_charset()
            if charset:
                try:
                    decoded = payload.decode(charset, errors='replace')
                    if msg.get_content_type() == "text/plain":
                        body = decoded
                    elif msg.get_content_type() == "text/html":
                        html_body = decoded
                except UnicodeDecodeError:
                    pass

    # Если текст не найден, пробуем извлечь из HTML
    if not body and html_body:
        body = html2text.html2text(html_body)

    return body.strip()[:]
class Linkedin_pattern:
    @staticmethod
    def fun_find_core(txt):
        lines = txt.splitlines()
        cleaned_lines = [line for line in lines if line != '']
        cleaned_text = "\n".join(cleaned_lines)
        # print(cleaned_text)
        text = cleaned_text
        start_phrase = "your preferences."
        end_phrase = "See all jobs on LinkedIn:"
        start_index = text.find(start_phrase)
        text = text[start_index + len(start_phrase):]
        end_index = text.rfind(end_phrase)
        text = text[:end_index]
        # print(text.strip()) # Удаляем лишние пробелы/пустые строки в начале/конце
        return text.strip()

    @staticmethod
    def get_cuts(text):
        start_index = 0
        indices = []

        url_pattern = re.compile(r'https?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+')

        # Находим все совпадения в тексте
        links = url_pattern.findall(text)
        # print(links)
        start_index = 0
        indexR = []
        for ll in links:
            indexL = text.find(ll, start_index)
            indexR.append(indexL + len(ll))
        i = 1
        indexR.insert(0, 0)
        new_cutet_txt = []
        for ii in indexR[:-1]:
            i1 = indexR[i - 1]
            i2 = indexR[i]
            i = i + 1
            new_cutet_txt.append(text[i1:i2])
        return new_cutet_txt, links

    @staticmethod
    def logic_1(new_cutet_txt):
        lines = new_cutet_txt
        i = 0
        inda_str = -1
        inda_sep = -1
        for ll in lines:
            if "View job:" in ll:
                inda_str = i
            elif ll.isspace():
                inda_sep = i
            i = i + 1
        # print(inda_str,inda_sep)
        # lines[inda_sep+1]
        return inda_str, inda_sep

    @staticmethod
    def main_fun(txt1):
        txt1 = Linkedin_pattern.fun_find_core(txt1)
        new_cutet_txt, links = Linkedin_pattern.get_cuts(txt1)

        pos_name, comp_name, city_name, link_name = [], [], [], []
        for i in range(len(links)):
            inda = i

            text_analyze_lines = new_cutet_txt[i].splitlines()

            i1, i2 = Linkedin_pattern.logic_1(text_analyze_lines)
            pos_name.append(text_analyze_lines[i2 + 1])
            comp_name.append(text_analyze_lines[i2 + 2])
            city_name.append(text_analyze_lines[i2 + 3])
            link_name.append(links[inda])
        datas = {"pos_name": pos_name, "comp_name": comp_name, "city_name": city_name, "link_name": link_name}
        return datas


def format_job_listings_for_telegram_html(data):
    """
    Formats job listing data into a human-readable HTML string suitable for a Telegram post.

    Args:
        data (dict): A dictionary containing job details with keys
                     'pos_name', 'comp_name', 'city_name', and 'link_name'.

    Returns:
        str: A formatted HTML string for a Telegram post, or an error message if data is incomplete.
    """
    pos_names = data.get('pos_name')
    comp_names = data.get('comp_name')
    city_names = data.get('city_name')
    link_names = data.get('link_name')

    if not all([pos_names, comp_names, city_names, link_names]):
        return "⚠️ Error: Incomplete job data provided. Please check all required fields."

    if not (len(pos_names) == len(comp_names) == len(city_names) == len(link_names)):
        return "⚠️ Error: Mismatched data lengths. All lists (position, company, city, link) must be of equal length."

    message_parts = []
    message_parts.append("✨ <b>New Job Openings!</b> ✨<br>")
    message_parts.append("Check out these fresh opportunities:<br><br>")

    for i in range(len(pos_names)):
        position = pos_names[i]
        company = comp_names[i]
        city = city_names[i]
        link = link_names[i]

        # Escape HTML special characters
        def escape_html(text):
            return (
                text.replace("&", "&amp;")
                    .replace("<", "&lt;")
                    .replace(">", "&gt;")
            )

        position = escape_html(position)
        company = escape_html(company)
        city = escape_html(city)

        message_parts.append(f"• <b>{position}</b><br>")
        message_parts.append(f"&nbsp;&nbsp;🏢 {company}<br>")
        message_parts.append(f"&nbsp;&nbsp;📍 {city}<br>")
        message_parts.append(f"&nbsp;&nbsp;🔗 <a href=\"{link}\">Apply Here</a><br>")
        message_parts.append("----------<br>")

    message_parts.append("<br>🌐 Find more opportunities on our channel!")
    message_parts.append("<br><i>Note: Links open in your browser.</i>")

    return "".join(message_parts)
def safe_html_link(url, text="Apply Here"):
    url = url.replace("&", "&amp;")  # Escape only for HTML, not for browser behavior
    return f'<a href="{url}">{text}</a>'


def format_job_listings_for_telegram(data):
    """
    Formats job listing data into a human-readable string suitable for a Telegram post.

    Args:
        data (dict): A dictionary containing job details with keys
                     'pos_name', 'comp_name', 'city_name', and 'link_name'.

    Returns:
        str: A formatted string for a Telegram post, or an error message if data is incomplete.
    """
    pos_names = data.get('pos_name')
    comp_names = data.get('comp_name')
    city_names = data.get('city_name')
    link_names = data.get('link_name')

    if not all([pos_names, comp_names, city_names, link_names]):
        return "⚠️ Error: Incomplete job data provided. Please check all required fields."

    if not (len(pos_names) == len(comp_names) == len(city_names) == len(link_names)):
        return "⚠️ Error: Mismatched data lengths. All lists (position, company, city, link) must be of equal length."

    message_parts = []
    # message_parts.append("✨ New Job Openings! ✨\n")
    message_parts.append("Check out these fresh opportunities:\n")

    for i in range(len(pos_names)):
        position = pos_names[i]
        company = comp_names[i]
        city = city_names[i]
        link = link_names[i]

        # Telegram MarkdownV2 formatting:
        # Use bold for position and company, and an inline URL for the link.
        # Escape special characters in text that might be interpreted as Markdown.
        # See: https://core.telegram.org/bots/api#markdownv2-style
        position_escaped = position.replace('_', '\\_').replace('*', '\\*').replace('[', '\\[').replace('`',
                                                                                                        '\\`').replace(
            '.', '\\.').replace('(', '\\(').replace(')', '\\)').replace('-', '\\-').replace('!', '\\!').replace('>',
                                                                                                                '\\>').replace(
            '#', '\\#').replace('+', '\\+').replace('=', '\\=').replace('|', '\\|').replace('{', '\\{').replace('}',
                                                                                                                '\\}').replace(
            '.', '\\.').replace('~', '\\~')
        company_escaped = company.replace('_', '\\_').replace('*', '\\*').replace('[', '\\[').replace('`',
                                                                                                      '\\`').replace(
            '.', '\\.').replace('(', '\\(').replace(')', '\\)').replace('-', '\\-').replace('!', '\\!').replace('>',
                                                                                                                '\\>').replace(
            '#', '\\#').replace('+', '\\+').replace('=', '\\=').replace('|', '\\|').replace('{', '\\{').replace('}',
                                                                                                                '\\}').replace(
            '.', '\\.').replace('~', '\\~')
        city_escaped = city.replace('_', '\\_').replace('*', '\\*').replace('[', '\\[').replace('`', '\\`').replace('.',
                                                                                                                    '\\.').replace(
            '(', '\\(').replace(')', '\\)').replace('-', '\\-').replace('!', '\\!').replace('>', '\\>').replace('#',
                                                                                                                '\\#').replace(
            '+', '\\+').replace('=', '\\=').replace('|', '\\|').replace('{', '\\{').replace('}', '\\}').replace('.',
                                                                                                                '\\.').replace(
            '~', '\\~')

        message_parts.append(f"• {position_escaped}\n")
        message_parts.append(f"  🏢 {company_escaped}\n")
        message_parts.append(f"  📍 {city_escaped}\n")
        message_parts.append(f"  🔗 [Apply Here]({link})\n")
        # message_parts.append(f"  🔗 <a href=\"{link}\">Apply Here</a><br>\n")
        # message_parts.append(f'🔗 {safe_html_link(link)}')

        message_parts.append("----------\n")  # Separator between listings

    message_parts.append("🌐 Find more opportunities on our channel!")
    # message_parts.append("\n_Note: Links open in your browser._")

    return "".join(message_parts)
def parse_linkedin_jobs(text: str) :
    # print(text)
    return format_job_listings_for_telegram(Linkedin_pattern.main_fun(text))

def method_name(mail):
    global status
    jobs=[]
    for email_id in email_ids:
        # ID_google_JOB , ID_linkedin_JOB ,ID_info_JOB = [False,False,False]
        status, data = mail.fetch(email_id, '(RFC822)')
        if status != 'OK':
            # print(f"Ошибка при получении письма {email_id.decode()}")
            continue
        msg = email.message_from_bytes(data[0][1])
        # print("\n-----------))))--------------------")
        # print(f"Дата: {msg.get('Date')}")
        # print(f"От: {msg.get('From')}")
        FROM_ID = msg.get('From')
        # print(f"Тема: {msg.get('Subject')}")
        if "notify-noreply@google.com" in FROM_ID:
            # print(FROM_ID)
            # ID_google_JOB=True
            # txt = get_text(msg)
            # print(txt)
            continue
            # print(parse_linkedin_jobs(txt))
        elif "jobalerts-noreply@linkedin.com" in FROM_ID:
            ID_linkedin_JOB = True
            # print("-------------text for google-------------")
            txt = get_text(msg)
            # print(txt)
            # break
            joba = parse_linkedin_jobs(txt)
            # print("---------------------parsed------------------")
            # print(joba)
            jobs.append(joba)

            # print(jobs)

            # for jb in jobs:
            #     print(jb)
            # break
            # txt = get_text(msg)
            # print(txt)
        elif "ofertas@push.infojobs.net" in FROM_ID:
            ID_info_JOB = True
            # txt = get_text(msg)
            # print(txt)
        else:
            continue
    return " ".join(jobs)
def chec_email(START_DATE,END_DATE):
    global status, messages, email_ids
    # Подключение к Gmail
    mail = imaplib.IMAP4_SSL('imap.gmail.com')
    mail.login(EMAIL, APP_PASSWORD)
    mail.select(f'"{LABEL}"', readonly=True)

    end_date_obj = datetime.strptime(END_DATE, '%Y%m%d') + timedelta(days=1)
    adjusted_end_date = end_date_obj.strftime('%Y%m%d')
    # Формирование критерия поиска
    date_criteria = f'(SINCE "{convert_date(START_DATE)}" BEFORE "{convert_date(adjusted_end_date)}")'
    status, messages = mail.search(None, date_criteria)
    if status != 'OK' or not messages[0]:
        print("Нет писем по заданным критериям.")
        mail.logout()
        exit()
    email_ids = messages[0].split()
    print(f"Найдено писем: {len(email_ids)}")
    # Обработка писем
    text_emails=method_name(mail)
    mail.close()
    mail.logout()
    return text_emails


if __name__ == "__main__":
    # Чтобы включить END_DATE, увеличиваем её на 1 день для фильтра IMAP
    app.run(host='0.0.0.0', port=5000, debug=True)  # debug=True only for development



