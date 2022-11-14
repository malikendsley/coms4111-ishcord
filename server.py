import os

# accessible as a variable in index.html:
from sqlalchemy import *
from flask import Flask, flash, jsonify, make_response, request, render_template, g, redirect, url_for
from functools import wraps

tmpl_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')
static_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static')
app = Flask(__name__, template_folder=tmpl_dir, static_folder=static_dir)

import secrets
secret_key = secrets.token_hex(16)
app.config['SECRET_KEY'] = secret_key

DATABASEURI = "postgresql://mse2143:3607@34.75.94.195/proj1part2"

# This line creates a database engine that knows how to connect to the URI above.
engine = create_engine(DATABASEURI)

# ============ Request wrappers ============== #

@app.before_request
def before_request():
	try:
		g.conn = engine.connect()
	except:
		print("Problem connecting to database")
		import traceback
		traceback.print_exc()
		g.conn = None

@app.teardown_request
def teardown_request(exception):
	if exception:
		print("Teardown exception:", exception)
	try:
		g.conn.close()
	except Exception as e:
		print("Conncetion closure exception:", e)

# ===================== Utility functions ===================== #

def login_required(f):
	@wraps(f)
	def decorated_function(*args, **kwargs):
		print("User hit guard page:", request.url)
		#check if user cookie is set
		if not authd(request):
			return redirect(url_for('login', next=request.url))
		return f(*args, **kwargs)
	return decorated_function

def authd(request):
	return request.cookies.get('uid') is not None and request.cookies.get('name') is not None

# ============== These functions serve pages ================== #

@app.route('/register', methods=['GET', 'POST'])
def register():
	# for GET, show registration form
	if request.method == 'GET':
		# go to dashboard if already logged in
		if authd(request):
			return redirect(url_for('dashboard'))
		else:
			print("User visited register page")
			return render_template("register.html")

	# for POST, create new user if name not taken
	elif request.method == 'POST':
		print("User registration request")
		name = request.form['username']
		color = request.form['color'][1:]
		print("Color: ", color)
		# check if user exists
		cursor = g.conn.execute("SELECT name FROM users WHERE name = %s", name)
		if len(name) == 0:
			flash("Username cannot be empty")
			cursor.close()
			return redirect('/register')
		elif cursor.rowcount > 0:
			flash('User already exists')
			cursor.close()
			return redirect('/register')
		# create new user, then go to dashboard
		else:
			cursor.close()
			# try to create user in users table
			try:
				cursor = g.conn.execute("INSERT INTO users(name, color) VALUES (%s, %s)", name, color)
				# get uid of new user
				cursor = g.conn.execute("SELECT uid FROM users WHERE name = %s", name)
				uid = cursor.fetchone()[0]
				print(type(uid))
				print("New user created:", name, uid)
				resp = make_response(redirect('/dashboard'))
				resp.set_cookie('name', name)
				resp.set_cookie('uid', str(uid))
				return resp
			except Exception as e:
				print("Error creating user:", e)
				flash("Error creating user, please try again")
				return redirect('/register')
			finally:
				cursor.close()

@app.route('/login', methods=['GET', 'POST'])
def login():
	# if GET, show login page
	if request.method == 'GET':
		# if logged in, go to dashboard
		if authd(request):
			return redirect(url_for('dashboard'))
		else:
			print("User visited login page")
			return render_template('login.html')
	# if POST, check db for user
	else:
		print("User login request")
		name = request.form['username']
		# require name
		if not name:
			flash('Please enter a username')
			return redirect('/login')
		# check if user exists
		cursor = g.conn.execute("SELECT name FROM users WHERE name = %s", name)
		if cursor.rowcount == 0:
			flash('Username does not exist')
			cursor.close()
			return redirect('/login')
		# log in user, go to dashboard
		else:
			print("Logging in as " + name)
			# close cursor
			cursor.close()
			# get uid of user, set cookie
			cursor = g.conn.execute("SELECT (uid) FROM users WHERE name = %s", name)
			uid = cursor.fetchone()[0]
			cursor.close()
			resp = make_response(redirect('/dashboard'))
			resp.set_cookie('name', name)
			resp.set_cookie('uid', str(uid))
			return resp

@app.route('/dashboard', methods=['GET'])
@login_required
def dashboard():
	print("User visited dashboard")
	# if logged in, show dashboard
	return render_template('dashboard.html')

@app.route('/', methods=['GET'])
def index():
	# if logged in, go to dashboard
	if authd(request):
		return redirect(url_for('dashboard'))
	else:
		print("User visited index page")
		return render_template('splash.html')

@app.errorhandler(404)
def page_not_found(e):
	print("User hit 404:", request.url)
	return render_template('404.html'), 404

# ============= These functions are API endpoints ============= #

# get all messages in a channel
@app.route('/api/<server>/<channel>/messages', methods=['GET'])
def get_messages(server, channel):
	print("User requested messages for channel:", channel, "on server:", server)
	try:
		cursor = g.conn.execute("SELECT * FROM messages_sends_appears_in WHERE fid = %s AND cname = %s", server, channel)
		messages = []
		columns = cursor.keys()
		for row in cursor:
			messages.append(dict(zip(columns, row)))
		cursor.close()
		return jsonify(messages)
	except Exception as e:
		print("Error getting messages:", e)
		return jsonify({'error': 'Error getting messages'})

# get all channels in a server
@app.route('/api/<server>/channels', methods=['GET'])
def get_channels(server):
	print("User requested channels for server:", server)
	try:
		cursor = g.conn.execute("SELECT * FROM channels_contains WHERE fid = %s", server)
		channels = []
		columns = cursor.keys()
		for row in cursor:
			channels.append(dict(zip(columns, row)))
		cursor.close()
		return jsonify(channels)
	except Exception as e:
		print("Error getting channels:", e)
		return jsonify({'error': 'Error getting channels'})

# get all server ids for a user
@app.route('/api/<uid>/servers', methods=['GET'])
def get_servers(uid):
	print("User requested servers for user:", uid)
	try:
		cursor = g.conn.execute("SELECT * FROM member_of WHERE uid = %s", uid)
		servers = []
		columns = cursor.keys()
		for row in cursor:
			servers.append(dict(zip(columns, row)))
		cursor.close()
		return jsonify(servers)
	except Exception as e:
		print("Error getting servers:", e)
		return jsonify({'error': 'Error getting servers'})

# get all users in a server
@app.route('/api/<server>/users', methods=['GET'])
def get_users(server):
	print("User requested users for server:", server)
	try:
		# get all uids in server
		server_cursor = g.conn.execute("SELECT * FROM member_of WHERE fid = %s", server)
		users = []
		columns = server_cursor.keys()
		# only include columns named uid and since
		users = [{k: v for k, v in row.items() if k in ['uid', 'since']} for row in server_cursor]
		# for each uid in users, get name from users table
		for key in users:
			uid = key['uid']
			user_cursor = g.conn.execute("SELECT name FROM users WHERE uid = %s", uid)
			key['name'] = user_cursor.fetchone()[0]
			user_cursor.close()
		server_cursor.close()
		return jsonify(users)
	except Exception as e:
		print("Error getting users:", e)
		return jsonify({'error': 'Error getting users'})

if __name__ == "__main__":
	import click

	@click.command()
	@click.option('--debug', is_flag=True)
	@click.option('--threaded', is_flag=True)
	@click.argument('HOST', default='0.0.0.0')
	@click.argument('PORT', default=8111, type=int)
	def run(debug, threaded, host, port):
		"""
		This function handles command line parameters.
		Run the server using:
			python3 server.py

		Show the help text using:
			python3 server.py --help

		"""

		HOST, PORT = host, port
		print("running on %s:%d" % (HOST, PORT))
		app.run(host=HOST, port=PORT, debug=debug, threaded=threaded)

	run()
