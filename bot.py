import telebot 
import configure
import sqlite3
import os
from bs4 import BeautifulSoup
from sqlite3 import Error
from telebot import types

bot = telebot.TeleBot(configure.config['token'])

#подключение к бд
def post_sql_query(sql_query):
	with sqlite3.connect('database.db') as connection:
		cursor = connection.cursor()
		try:
			cursor.execute(sql_query)
		except Error:
			pass
		result = cursor.fetchall()
		return result

def register_user(user, first_name, username):
	user_check_query = f'SELECT * FROM customers WHERE user_id = {user};'
	user_check_data = post_sql_query(user_check_query)
	if not user_check_data:
		insert_to_db_query = f'INSERT INTO customers (user_id, name, username) VALUES ({user}, "{first_name}", "{username}");'
		post_sql_query(insert_to_db_query)

def mainmenu():
	keyboard = types.ReplyKeyboardMarkup(1, row_width=2, selective=0)
	keyboard.add(*[types.KeyboardButton(text=name)
					for name in ['📂 Каталог', '🛒 Корзина', '🔎 Поиск', '📡 Новости', '🌪 Промокод', '❓ Помощь']])
	return keyboard

#реакция на команду /start  	
@bot.message_handler(commands=['start'])
def start(message):
	register_user(message.from_user.id, message.from_user.first_name, message.from_user.username)

	send_mess = f"<b>Привет {message.from_user.first_name}, классный ник!\nА теперь давай найдем тебе классную одежду</b>"
	bot.send_message(message.chat.id, send_mess, parse_mode='html', reply_markup = mainmenu())

def catalog(message):
	cid = message.chat.id

	sqlite_connection = sqlite3.connect('database.db')
	cursor = sqlite_connection.cursor()

	cursor.execute('SELECT id_categories FROM products')
	prod = cursor.fetchall()
	print(prod)

	cursor.execute('SELECT COUNT(*) FROM categories_products')
	N = cursor.fetchone()
	N = int(str(N)[1:-2])

	cursor.execute('SELECT name FROM categories_products')

	catalog = []
	for i in range(N):
		catalog.append(str(cursor.fetchone())[2:-3])

	keyboard = types.ReplyKeyboardMarkup(1, row_width=2, selective=0)
	keyboard.add(*[types.KeyboardButton(text=name)
					for name in catalog])
	keyboard.add(types.KeyboardButton(text='🤷‍♀️ Главное меню'))

	msg = bot.send_message(cid, 'Выберите товар:', reply_markup=keyboard)
	bot.register_next_step_handler(msg, catalogselect)

def catalogselect(message):
	cid = message.chat.id

	sqlite_connection = sqlite3.connect('database.db')
	cursor = sqlite_connection.cursor()

	if message.text == '🤷‍♀️ Главное меню':
		bot.clear_step_handler_by_chat_id(cid)
		bot.send_message(cid, 'Вы вернулись в главное меню', reply_markup = mainmenu())

	else:
		try:
			cursor.execute(f'SELECT id FROM categories_products WHERE name=\'{message.text}\'')
			category = cursor.fetchone()
			category = int(str(category)[1:-2])
			print('category = ' + str(category))

			cursor.execute(f'SELECT COUNT(*) FROM products WHERE id_categories=\'{category}\'')
			N = cursor.fetchone()
			N = int(str(N)[1:-2])
			print('N = ' + str(N))

			cursor.execute(f'SELECT id FROM products WHERE id_categories=\'{category}\'')

			clothing = []
			for i in range(N):
				clothing.append(str(cursor.fetchone())[1:-2])

			for i in clothing:
				keyboard = types.InlineKeyboardMarkup()
				keyboard.add(*[types.InlineKeyboardButton(text=name, callback_data=name)
								for name in ['Добавить в корзину']])

				cursor.execute(f'SELECT name FROM products WHERE id=\'{i}\'')
				name = cursor.fetchone()
				name = str(name)[2:-3]

				cursor.execute(f'SELECT description FROM products WHERE id=\'{i}\'')
				description = cursor.fetchone()
				description = str(description)[2:-3]

				cursor.execute(f'SELECT amount FROM products WHERE id=\'{i}\'')
				amount = cursor.fetchone()
				amount = str(amount)[1:-2]

				cursor.execute(f'SELECT price FROM products WHERE id=\'{i}\'')
				price = cursor.fetchone()
				price = str(price)[1:-2]

				msg = bot.send_photo(cid, open(f'product/{name}.jpg', 'rb'), caption=name +
					'\n' + description + '\n1 шт - ' + price + ' грн\n' +
					'В наличие - ' + amount + ' шт', reply_markup=keyboard)

			bot.register_next_step_handler(msg, catalogselect)

		except:
			sqlite_connection.rollback()
			msg = bot.send_message(cid, 'Прости, сейчас нет в наличии')
			bot.register_next_step_handler(msg, catalogselect)

#aдмин панель
@bot.message_handler(commands=['admin'])
def admin(message):
	cid = message.chat.id

	msg = bot.send_message(cid, 'Введите пароль:')
	bot.register_next_step_handler(msg, adminpassword)


def adminpassword(message):
	cid = message.chat.id

	if message.text == (configure.password['password']):
		keyboard = types.ReplyKeyboardMarkup(1, row_width=2, selective=0)
		keyboard.add(*[types.KeyboardButton(text=name)
						for name in ['Добавить товар🤲', 'Удалить товар🙌', 'Редактировать товар👐', 'Показать отчёт🤝']])
		keyboard.add('Выйти из админ панели😎')
		msg = bot.send_message(cid, f"Доброго времени суток {message.from_user.first_name}😊\nВыберите команду:", reply_markup=keyboard)
		bot.register_next_step_handler(msg, admmainmenu)

	else:
		bot.send_message(cid, 'Это точно не тот пароль😱')

def admmainmenu(message):
	cid = message.chat.id

	sqlite_connection = sqlite3.connect('database.db')
	cursor = sqlite_connection.cursor()

	if message.text == 'Выйти из админ панели😎':
		bot.clear_step_handler_by_chat_id(cid)
		bot.send_message(cid, 'Вы вышли из админ панели', reply_markup=mainmenu())

	elif message.text == 'Добавить товар🤲':
		keyboard = types.ReplyKeyboardMarkup(1, 1)
		keyboard.add(*[types.KeyboardButton(text=name)
						for name in ['В другой раз']])

		cursor.execute('SELECT COUNT(*) FROM categories_products')
		N = cursor.fetchone()
		N = int(str(N)[1:-2])

		cursor.execute('SELECT name FROM categories_products')
		clothingS = ''
		for i in range(N):
			clothingS += str(cursor.fetchone())[2:-3] + '\n'
		bot.send_message(cid, 'Категории👇\n' + clothingS)

		msg = bot.send_message(cid, 'Введите название категории: ', reply_markup=keyboard)
		bot.register_next_step_handler(msg, admaddcategories)	

	elif message.text == 'Удалить товар🙌':
		cursor.execute('SELECT COUNT(*) FROM products')
		N = cursor.fetchone()
		N = int(str(N)[1:-2])

		cursor.execute('SELECT name FROM products')

		clothingS = ''
		clothingD = {}
		for i in range(N):
			tmp = str(cursor.fetchone())[2:-3]
			clothingD[i+1] = tmp
			clothingS += f'{i+1}. ' + tmp + '\n'
		bot.send_message(cid, clothingS)

		keyboard = types.ReplyKeyboardMarkup(1, 1)
		keyboard.add(*[types.KeyboardButton(text=name) for name in ['В другой раз']])

		msg = bot.send_message(cid, 'Введите название товара, который нужно удалить:', reply_markup=keyboard)
		bot.register_next_step_handler(msg, delpositionadm, clothingD)	

	elif message.text == 'Редактировать товар👐':
		cursor.execute('SELECT COUNT(*) FROM products')
		N = cursor.fetchone()
		N = int(str(N)[1:-2])

		cursor.execute('SELECT name FROM products')

		clothingS = ''
		clothingD = {}
		for i in range(N):
			tmp = str(cursor.fetchone())[2:-3]
			clothingD[i+1] = tmp
			clothingS += f'{i+1}. ' + tmp + '\n'

		bot.send_message(cid, clothingS)

		keyboard = types.ReplyKeyboardMarkup(1, 1)
		keyboard.add(*[types.KeyboardButton(text=name) for name in ['В другой раз']])

		msg = bot.send_message(cid, 'Введите название товара, который нужно редактировать: ', reply_markup=keyboard)
		bot.register_next_step_handler(msg, editpositionadm, clothingD)

	elif message.text == 'Показать отчёт🤝':
		msg = bot.send_message(cid, 'отчёт')
		bot.register_next_step_handler(msg, admmainmenu)
	
	else:
		bot.send_message(cid, 'Такой команды нет')

#добавление товара
def admaddcategories(message):
    cid = message.chat.id

    sqlite_connection = sqlite3.connect('database.db')
    cursor = sqlite_connection.cursor()

    if message.text != 'В другой раз':
        category = message.text
        request = f'INSERT INTO categories_products(name) SELECT * FROM(SELECT \'{category}\') AS tmp WHERE NOT EXISTS(SELECT name FROM categories_products WHERE name = \'{category}\') LIMIT 1'

        try:
            cursor.execute(request)
            sqlite_connection.commit()
        except:
            sqlite_connection.rollback()

        msg = bot.send_message(cid, 'Введите название товара:')
        bot.register_next_step_handler(msg, addpositionadm, category)

    else:
        keyboard = types.ReplyKeyboardMarkup(1, row_width=2, selective=0)
        keyboard.add(*[types.KeyboardButton(text=admbutton)
                        for admbutton in ['Добавить товар🤲', 'Удалить товар🙌', 'Редактировать товар👐', 'Показать отчёт🤝', 'Выйти из админ панели😎']])
        msg = bot.send_message(cid, 'Ладно', reply_markup=keyboard)
        bot.register_next_step_handler(msg, admmainmenu)

def addpositionadm(message, category):
    cid = message.chat.id

    sqlite_connection = sqlite3.connect('database.db')
    cursor = sqlite_connection.cursor()

    if message.text != 'В другой раз':
        category = category
        clothingnew = message.text

        cursor.execute(f'SELECT id FROM categories_products WHERE name=\'{category}\'')
        categoryId = int(str(cursor.fetchone())[1:-2])
        print(categoryId)

        try:
            cursor.execute(f'INSERT INTO products (id_categories, name) VALUES (\'{categoryId}\', \'{clothingnew}\')')
            sqlite_connection.commit()
        except:
            sqlite_connection.rollback()

        msg = bot.send_message(cid, '📝Опишите товар:')
        bot.register_next_step_handler(msg, adddescriptionadm, clothingnew)

    else:
        keyboard = types.ReplyKeyboardMarkup(1, row_width=2, selective=0)
        keyboard.add(*[types.KeyboardButton(text=admbutton)
                        for admbutton in ['Добавить товар🤲', 'Удалить товар🙌', 'Редактировать товар👐', 'Показать отчёт🤝', 'Выйти из админ панели😎']])
        msg = bot.send_message(cid, 'Ладно', reply_markup=keyboard)
        bot.register_next_step_handler(msg, admmainmenu)

def adddescriptionadm(message, clothingnew):
	cid = message.chat.id

	sqlite_connection = sqlite3.connect('database.db')
	cursor = sqlite_connection.cursor()

	if message.text != 'В другой раз':
		clothingnew = clothingnew
		description = message.text

		request = f'UPDATE products SET description = \'{description}\'WHERE name = \'{clothingnew}\''
		try:
			cursor.execute(request)
			sqlite_connection.commit()
		except:
			sqlite_connection.rollback()

		msg = bot.send_message(cid, '💰Введите цену:')
		bot.register_next_step_handler(msg, addpriceadm, clothingnew)

	else:
		keyboard = types.ReplyKeyboardMarkup(1, row_width=2, selective=0)
		keyboard.add(*[types.KeyboardButton(text=admbutton)
						for admbutton in ['Добавить товар🤲', 'Удалить товар🙌', 'Редактировать товар👐', 'Показать отчёт🤝', 'Выйти из админ панели😎']])
		msg = bot.send_message(cid, 'Ладно', reply_markup=keyboard)
		bot.register_next_step_handler(msg, admmainmenu)

def addpriceadm(message, clothingnew):
	cid = message.chat.id

	sqlite_connection = sqlite3.connect('database.db')
	cursor = sqlite_connection.cursor()

	if message.text != 'В другой раз':
		clothingnew = clothingnew
		price = message.text

		request = f'UPDATE products SET price = \'{price}\'WHERE name = \'{clothingnew}\''
		try:
			cursor.execute(request)
			sqlite_connection.commit()
		except:
			sqlite_connection.rollback()

		msg = bot.send_message(cid, '🧮Введите количество:')
		bot.register_next_step_handler(msg, addamountadm, clothingnew)
	else:
		keyboard = types.ReplyKeyboardMarkup(1, row_width=2, selective=0)
		keyboard.add(*[types.KeyboardButton(text=admbutton)
						for admbutton in ['Добавить товар🤲', 'Удалить товар🙌', 'Редактировать товар👐', 'Показать отчёт🤝', 'Выйти из админ панели😎']])
		msg = bot.send_message(cid, 'Ладно', reply_markup=keyboard)
		bot.register_next_step_handler(msg, admmainmenu)

def addamountadm(message, clothingnew):
	cid = message.chat.id

	sqlite_connection = sqlite3.connect('database.db')
	cursor = sqlite_connection.cursor()

	if message.text != 'В другой раз':
		clothingnew = clothingnew
		amount = message.text

		request = f'UPDATE products SET amount = \'{amount}\'WHERE name = \'{clothingnew}\''
		try:
			cursor.execute(request)
			sqlite_connection.commit()
		except:
			sqlite_connection.rollback()

		msg = bot.send_message(cid, '📷Прикрепите фото:')
		bot.register_next_step_handler(msg, addphotoadm, clothingnew)

	else:
		keyboard = types.ReplyKeyboardMarkup(1, row_width=2, selective=0)
		keyboard.add(*[types.KeyboardButton(text=admbutton)
						for admbutton in ['Добавить товар🤲', 'Удалить товар🙌', 'Редактировать товар👐', 'Показать отчёт🤝', 'Выйти из админ панели😎']])
		msg = bot.send_message(cid, 'Ладно', reply_markup=keyboard)
		bot.register_next_step_handler(msg, admmainmenu)

def addphotoadm(message, clothingnew):
	cid = message.chat.id

	sqlite_connection = sqlite3.connect('database.db')
	cursor = sqlite_connection.cursor()

	try:
		if message.text != 'В другой раз':
			clothingnew = clothingnew

			cursor.execute(f'SELECT name FROM products WHERE name=\'{clothingnew}\'')
			clothing = cursor.fetchone()
			clothing = str(clothing)[2:-3]
			print(clothing)

			file_info = bot.get_file(message.document.file_id)
			downloaded_file = bot.download_file(file_info.file_path)

			src = 'product/' + str(clothing) + '.jpg'
			with open(src, 'wb') as file:
				file.write(downloaded_file)

			keyboard = types.ReplyKeyboardMarkup(1, row_width=2, selective=0)
			keyboard.add(*[types.KeyboardButton(text=admbutton)
							for admbutton in ['Добавить товар🤲', 'Удалить товар🙌', 'Редактировать товар👐', 'Показать отчёт🤝', 'Выйти из админ панели😎']])
			msg = bot.send_message(cid, 'Товар добавлен', reply_markup=keyboard)
			bot.register_next_step_handler(msg, admmainmenu)

		else:
			keyboard = types.ReplyKeyboardMarkup(1, row_width=2, selective=0)
			keyboard.add(*[types.KeyboardButton(text=admbutton)
							for admbutton in ['Добавить товар🤲', 'Удалить товар🙌', 'Редактировать товар👐', 'Показать отчёт🤝', 'Выйти из админ панели😎']])
			msg = bot.send_message(cid, 'Ладно', reply_markup=keyboard)
			bot.register_next_step_handler(msg, admmainmenu)

	except Exception as error:
		print(error)
		msg = bot.reply_to(message, 'Не сжимайте изображение\nПопробуйте ещё раз')
		bot.register_next_step_handler(msg, addphotoadm, clothingnew)

#удаление товара
def delpositionadm(message, clothingD):
	cid = message.chat.id

	sqlite_connection = sqlite3.connect('database.db')
	cursor = sqlite_connection.cursor()

	if message.text != 'В другой раз':
		clothingD = clothingD.copy()
		delclothing = message.text
		print(clothingD)
		print(delclothing)

		cursor.execute(f'SELECT name FROM products WHERE name=\'{delclothing}\'')
		delname = cursor.fetchone()
		delname = str(delname)[2:-3]
		os.remove(f'product/{delname}.jpg')

		request = f'DELETE FROM products WHERE name = \'{delclothing}\''

		try:
			cursor.execute(request)
			sqlite_connection.commit()
		except:
			sqlite_connection.rollback()

		keyboard = types.ReplyKeyboardMarkup(1, row_width=2, selective=0)
		keyboard.add(*[types.KeyboardButton(text=admbutton)
						for admbutton in ['Добавить товар🤲', 'Удалить товар🙌', 'Редактировать товар👐', 'Показать отчёт🤝']])
		keyboard.add('Выйти из админ панели😎')
		msg = bot.send_message(cid, 'Товар удален', reply_markup=keyboard)
		bot.register_next_step_handler(msg, admmainmenu)

	else:
		keyboard = types.ReplyKeyboardMarkup(1, row_width=2, selective=0)
		keyboard.add(*[types.KeyboardButton(text=admbutton)
						for admbutton in ['Добавить товар🤲', 'Удалить товар🙌', 'Редактировать товар👐', 'Показать отчёт🤝']])
		keyboard.add('Выйти из админ панели😎')
		msg = bot.send_message(cid, 'Ладно', reply_markup=keyboard)
		bot.register_next_step_handler(msg, admmainmenu)

#редактирование товара 
def editpositionadm(message, clothingD):
	cid = message.chat.id

	sqlite_connection = sqlite3.connect('database.db')
	cursor = sqlite_connection.cursor()

	if message.text != 'В другой раз':
		clothingD = clothingD.copy()
		editclothing = message.text
		print(clothingD)
		print(editclothing)

		cursor.execute(f'SELECT name, description, price, amount FROM products WHERE name=\'{editclothing}\'')
		clothingedit = cursor.fetchone()
		print(clothingedit)

		keyboard = types.ReplyKeyboardMarkup(1, row_width=2, selective=0)
		keyboard.add(*[types.KeyboardButton(text=name)
						for name in ['Редактировать описание📝', 'Редактировать цену💰', 'Редактировать количество🧮']])
		keyboard.add('В другой раз')

		msg = bot.send_message(cid, clothingedit[0] + '\n' + clothingedit[1] + '\n1шт - ' + str(clothingedit[2]) + 'грн\n'
								'В наличие - ' + str(clothingedit[3]) + 'шт', reply_markup=keyboard)
		bot.register_next_step_handler(msg, editadmin, clothingD, editclothing)

	else:
		keyboard = types.ReplyKeyboardMarkup(1, row_width=2, selective=0)
		keyboard.add(*[types.KeyboardButton(text=admbutton)
						for admbutton in ['Добавить товар🤲', 'Удалить товар🙌', 'Редактировать товар👐', 'Показать отчёт🤝']])
		keyboard.add('Выйти из админ панели😎')
		msg = bot.send_message(cid, 'Ладно', reply_markup=keyboard)
		bot.register_next_step_handler(msg, admmainmenu)

def editadmin(message, clothingD, editclothing):
	cid = message.chat.id

	if message.text != 'В другой раз':
		clothingD = clothingD.copy()
		editclothing = editclothing
		keyboard = types.ReplyKeyboardMarkup(1, row_width=2, selective=0)
		keyboard.add('В другой раз')

		if message.text == 'Редактировать описание📝':
			msg = bot.send_message(cid, 'Введите новое описание:', reply_markup=keyboard)
			bot.register_next_step_handler(msg, editdescriptionadm, clothingD, editclothing)

		elif message.text == 'Редактировать цену💰':
			msg = bot.send_message(cid, 'Введите новую цену:', reply_markup=keyboard)
			bot.register_next_step_handler(msg, editpriceadm, clothingD, editclothing)

		elif message.text == 'Редактировать количество🧮':
			msg = bot.send_message(cid, 'Ведите новое количество:', reply_markup=keyboard)
			bot.register_next_step_handler(msg, editamountadm, clothingD, editclothing)

	else:
		keyboard = types.ReplyKeyboardMarkup(1, row_width=2, selective=0)
		keyboard.add(*[types.KeyboardButton(text=admbutton)
						for admbutton in ['Добавить товар🤲', 'Удалить товар🙌', 'Редактировать товар👐', 'Показать отчёт🤝']])
		keyboard.add('Выйти из админ панели😎')
		msg = bot.send_message(cid, 'Ладно', reply_markup=keyboard)
		bot.register_next_step_handler(msg, admmainmenu)		

def editdescriptionadm(message, clothingD, editclothing):
	cid = message.chat.id

	sqlite_connection = sqlite3.connect('database.db')
	cursor = sqlite_connection.cursor()

	if message.text != 'В другой раз':

		clothingD = clothingD.copy()
		editclothing = editclothing

		try:
			cursor.execute(f'UPDATE products SET description = \'{message.text}\' WHERE name = \'{editclothing}\'')
			sqlite_connection.commit()
		except:
			sqlite_connection.rollback()
			msg = bot.send_message(cid, 'Попробуйте ещё раз:')
			bot.register_next_step_handler(cid, adminEditAmount, clothingD, editclothing)

		keyboard = types.ReplyKeyboardMarkup(1, row_width=2, selective=0)
		keyboard.add(*[types.KeyboardButton(text=name)
						for name in ['Редактировать описание📝', 'Редактировать цену💰', 'Редактировать количество🧮']])
		keyboard.add('В другой раз')

		msg = bot.send_message(cid, 'Изменения сохранены', reply_markup=keyboard)
		bot.register_next_step_handler(msg, editadmin, clothingD, editclothing)

	else:
		keyboard = types.ReplyKeyboardMarkup(1, row_width=2, selective=0)
		keyboard.add(*[types.KeyboardButton(text=admbutton)
						for admbutton in ['Добавить товар🤲', 'Удалить товар🙌', 'Редактировать товар👐', 'Показать отчёт🤝']])
		keyboard.add('Выйти из админ панели😎')
		msg = bot.send_message(cid, 'Ладно', reply_markup=keyboard)
		bot.register_next_step_handler(msg, admmainmenu)

def editpriceadm(message, clothingD, editclothing):
	cid = message.chat.id

	sqlite_connection = sqlite3.connect('database.db')
	cursor = sqlite_connection.cursor()

	if message.text != 'В другой раз':

		clothingD = clothingD.copy()
		editclothing = editclothing

		try:
			cursor.execute(f'UPDATE products SET price = \'{message.text}\' WHERE name = \'{editclothing}\'')
			sqlite_connection.commit()
		except:
			sqlite_connection.rollback()
			msg = bot.send_message(cid, 'Попробуйте ещё раз:')
			bot.register_next_step_handler(cid, adminEditAmount, clothingD, editclothing)

		keyboard = types.ReplyKeyboardMarkup(1, row_width=2, selective=0)
		keyboard.add(*[types.KeyboardButton(text=name)
						for name in ['Редактировать описание📝', 'Редактировать цену💰', 'Редактировать количество🧮']])
		keyboard.add('В другой раз')

		msg = bot.send_message(cid, 'Изменения сохранены', reply_markup=keyboard)
		bot.register_next_step_handler(msg, editadmin, clothingD, editclothing)

	else:
		keyboard = types.ReplyKeyboardMarkup(1, row_width=2, selective=0)
		keyboard.add(*[types.KeyboardButton(text=admbutton)
						for admbutton in ['Добавить товар🤲', 'Удалить товар🙌', 'Редактировать товар👐', 'Показать отчёт🤝']])
		keyboard.add('Выйти из админ панели😎')
		msg = bot.send_message(cid, 'Ладно', reply_markup=keyboard)
		bot.register_next_step_handler(msg, admmainmenu)

def editamountadm(message, clothingD, editclothing):
	cid = message.chat.id

	sqlite_connection = sqlite3.connect('database.db')
	cursor = sqlite_connection.cursor()

	if message.text != 'В другой раз':
		clothingD = clothingD.copy()
		editclothing = editclothing

		try:
			cursor.execute(f'UPDATE products SET amount = \'{message.text}\' WHERE name = \'{editclothing}\'')
			sqlite_connection.commit()
		except:
			sqlite_connection.rollback()
			msg = bot.send_message(cid, 'Попробуйте ещё раз:')
			bot.register_next_step_handler(cid, adminEditAmount, clothingD, editclothing)

		keyboard = types.ReplyKeyboardMarkup(1, row_width=2, selective=0)
		keyboard.add(*[types.KeyboardButton(text=name)
						for name in ['Редактировать описание📝', 'Редактировать цену💰', 'Редактировать количество🧮']])
		keyboard.add('В другой раз')

		msg = bot.send_message(cid, 'Изменения сохранены', reply_markup=keyboard)
		bot.register_next_step_handler( msg, editadmin, clothingD, editclothing)

	else:
		keyboard = types.ReplyKeyboardMarkup(1, row_width=2, selective=0)
		keyboard.add(*[types.KeyboardButton(text=admbutton)
 						for admbutton in ['Добавить товар🤲', 'Удалить товар🙌', 'Редактировать товар👐', 'Показать отчёт🤝']])
		keyboard.add('Выйти из админ панели😎')
		msg = bot.send_message(cid, 'Ладно', reply_markup=keyboard)
		bot.register_next_step_handler(msg, admmainmenu)

@bot.message_handler(content_types = ['news'])	
def now_news(message):
	pass

#теакция на текст 
@bot.message_handler(content_types = ['text'])
def mein_menu(message):
	cid = message.chat.id

	if message.text == '🤷‍♀️ Главное меню':
		bot.clear_step_handler_by_chat_id(cid)
		bot.send_message(cid, 'Вы вернулись в главное меню', reply_markup = mainmenu())

	elif message.text == '🔎 Поиск':
		search(message)

	elif message.text == '📂 Каталог':
		catalog(message)

	else:  
		bot.send_message(cid, 'Сейчас не понял 😒')

#реакция на инлайновую клавиатуру
@bot.callback_query_handler(func=lambda call: True)
def back_menu(call):
	cid = call.message.chat.id
	mid = call.message.message_id

	qlite_connection = sqlite3.connect('database.db')
	cursor = sqlite_connection.cursor()

def basket(message):
 	pass

#поиск по бд
@bot.message_handler(commands=['search'])
def search(message):
	cid = message.chat.id

	sqlite_connection = sqlite3.connect('database.db')
	cursor = sqlite_connection.cursor()

	cursor.execute("SELECT id_categories FROM products")
	prod = cursor.fetchall()
	print('prod = ' + str(prod))

	keyboard = types.ReplyKeyboardMarkup(1, row_width=1, selective=0)
	keyboard.add(types.KeyboardButton(text='🤷‍♀️ Главное меню'))

	msg = bot.send_message(cid, 'Введите название товара:', reply_markup=keyboard)
	bot.register_next_step_handler(msg, searchcategory)

def searchcategory(message):
	cid = message.chat.id

	sqlite_connection = sqlite3.connect('database.db')
	cursor = sqlite_connection.cursor()

	if message.text == '🤷‍♀️ Главное меню':
		bot.clear_step_handler_by_chat_id(cid)
		bot.send_message(cid, 'Вы вернулись в главное меню', reply_markup = mainmenu())

	else:
		try:
			cursor.execute(f'SELECT name FROM products WHERE name=\'{message.text}\'')
			name = cursor.fetchone()
			name = str(name)[2:-3]

			cursor.execute(f'SELECT description FROM products WHERE name=\'{message.text}\'')
			description = cursor.fetchone()
			description = str(description)[2:-3]

			cursor.execute(f'SELECT amount FROM products WHERE name=\'{message.text}\'')
			amount = cursor.fetchone()
			amount = str(amount)[1:-2]

			cursor.execute(f'SELECT price FROM products WHERE name=\'{message.text}\'')
			price = cursor.fetchone()
			price = str(price)[1:-2]

			keyboard = types.InlineKeyboardMarkup()
			keyboard.add(*[types.InlineKeyboardButton(text=name, callback_data=name)
							for name in ['Добавить в корзину']])

			msg = bot.send_photo(cid, open(f'product/{name}.jpg', 'rb'), caption=name +
				'\n' + description + '\nВ наличие - ' + amount + ' шт\n' +
				'1 шт - ' + price + ' грн', reply_markup=keyboard)

			bot.register_next_step_handler(msg, searchcategory)
		
		except:
			sqlite_connection.rollback()
			msg = bot.send_message(cid, 'Прости, сейчас нет в наличии')
			bot.register_next_step_handler(msg, searchcategory)

bot.polling(none_stop=True)