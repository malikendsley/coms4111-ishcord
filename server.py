import os
import time

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
		print("User hit login guard page:", request.url)
		#check if user cookie is set
		if not authd(request):
			return redirect(url_for('login', next=request.url))
		return f(*args, **kwargs)
	return decorated_function

def server_selection_required(f):
	@wraps(f)
	def decorated_function(*args, **kwargs):
		print("User hit server guard:", request.url)
		#check if a server and channel are selected
		if not server_selected(request):
			return redirect(url_for('dashboard'))
		return f(*args, **kwargs)
	return decorated_function

def authd(request):
	return request.cookies.get('uid') is not None and request.cookies.get('name') is not None

def server_selected(request):
	return request.cookies.get('server') is not None and request.cookies.get('channel') is not None

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
	elif request.method == 'POST':
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

@app.route('/dashboard', methods=['GET'], defaults={'server': None, 'channel': None})
@app.route('/dashboard/<server>/<channel>', methods=['GET'])
@login_required
def dashboard(server, channel):
	print("User visited dashboard")
	# if server and channel are specified, set cookies
	if server and channel:
		resp = make_response(render_template('dashboard.html'))
		resp.set_cookie('server', server)
		# strip quotes from channel name
		resp.set_cookie('channel', str(channel))
		return resp
	# if not, just show dashboard
	else:
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

# post a new message
@app.route('/api/<server>/<channel>/post', methods=['POST'])
@login_required
def post(server, channel):
	# get message
	body = request.form['message']
	# get uid
	uid = request.cookies.get('uid')
	# get server and channel
	fid = server
	cname = channel
	# insert into db
	print("User posted message:", body, "to", fid, cname)
	try:
		g.conn.execute("INSERT INTO messages_sends_appears_in (body, uid, fid, cname) VALUES (%s, %s, %s, %s)", body, uid, fid, cname)
		print("New message posted:", body, uid, fid, cname)
		return jsonify({'success': True})
	except Exception as e:
		print("Error posting message:", e)
		return jsonify({'success': False})

# create a new server
@app.route('/api/<uid>/create_server', methods=['POST'])
def create_server(uid):
	# get details
	name = request.form['server-name']
	description = request.form['server-description']

	print("User created server:", name, description, uid)
	# insert into db
	try:
		# check if server exists
		cursor = g.conn.execute("SELECT name FROM forums_administrates WHERE name = %s", name)
		if cursor.rowcount > 0:
			cursor.close()
			print("Server already exists")
			flash("Server already exists")
			return redirect('/dashboard')
		# create server
		else:
			cursor.close()
			# TOOD: implement image URI
			g.conn.execute("INSERT INTO forums_administrates (name, description, uid) VALUES (%s, %s, %s)", name, description, uid)
			print("New server created:", name, description, uid)
			# get fid of new server 
			cursor = g.conn.execute("SELECT fid FROM forums_administrates WHERE name = %s", name)
			fid = cursor.fetchone()[0]
			cursor.close()
	except Exception as e:
		print("Error creating server:", e)
		flash("Error creating server, please try again")
		redirect('/dashboard')
 	# create default general channel
	try:
		g.conn.execute("INSERT INTO channels_contains (cname, topic, fid) VALUES (%s, %s, %s)", "general", "general chat goes here", fid)
		print("New channel created:", "general", name)
	except Exception as e:
		print("Error creating channel:", e)
		flash("Error creating channel, please try again")
		redirect('/dashboard')
	# add creator to server
	try:
		# add creator to server
		g.conn.execute("INSERT INTO member_of (uid, fid) VALUES (%s, %s)", uid, fid)
		print("User added to server:", uid, fid)
	except Exception as e:
		print("Error adding user to server")
		flash("Error adding user to server")
		redirect('/dashboard')
	flash("Server created successfully")
	return redirect('/dashboard')
  
# get all messages in a channel, long polling style
@app.route('/api/<server>/<channel>/', methods=['GET'], defaults={'last': None})
@app.route('/api/<server>/<channel>/<last>', methods=['GET'])
def get_messages(server, channel, last):
	print("User requested messages for channel:", channel, "on server:", server)
	# get last message id
	last_id = last
	print("Last message id:", last_id)
	# if last_id is None, set to 0
	if last_id is None:
		print("Last message id is None, setting to 0")
		last_id = 0
	try:
		while True:
			# get all messages since last_id
			cursor = g.conn.execute("SELECT name, body, timestamp, mid FROM messages_sends_appears_in NATURAL JOIN users WHERE fid = %s AND cname = %s AND mid > %s", server, channel, last_id)
			# if there are new messages, return them
			if cursor.rowcount > 0:
				print("Sending new messages")
				messages = []
				for row in cursor:
					messages.append({'name': row[0], 'body': row[1], 'timestamp': row[2], 'mid': row[3]})
				cursor.close()
				return jsonify({'messages': messages})
			# otherwise, wait for new messages
			else:
				#print("Waiting for new messages")
				cursor.close()
				time.sleep(1)
	except Exception as e:
		print("Error getting messages:", e)
		return jsonify({'success': False})

# get all channels in a server
@app.route('/api/<server>/channels', methods=['GET'])
def get_channels(server):
	print("User requested channels for server:", server)
	try:
		cursor = g.conn.execute("SELECT cname, topic FROM channels_contains WHERE fid = %s", server)
		channels = []
		columns = cursor.keys()
		for row in cursor:
			channels.append(dict(zip(columns, row)))
		cursor.close()
		return jsonify(channels)
	except Exception as e:
		print("Error getting channels:", e)
		return jsonify({'error': 'Error getting channels'})

# get all servers for a user
@app.route('/api/<uid>/servers', methods=['GET'])
def get_servers(uid):
	print("User requested servers for user:", uid)
	try:
		cursor = g.conn.execute("SELECT * FROM member_of WHERE uid = %s", uid)
		servers = []
		# only include columns named fid and since
		servers = [{k: v for k, v in row.items() if k in ['fid', 'since']} for row in cursor]
		cursor.close()
		# for each server, get its name, icon, and description
		for server in servers:
			cursor = g.conn.execute("SELECT name, icon, description FROM forums_administrates WHERE fid = %s", server['fid'])
			row = cursor.fetchone()
			server['name'] = row[0]
			server['icon'] = row[1]
			server['description'] = row[2]
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
		# only include columns named uid and since
		users = [{k: v for k, v in row.items() if k in ['uid', 'since']} for row in server_cursor]
		# for each uid in users, get name from users table
		server_cursor.close()
		for key in users:
			uid = key['uid']
			user_cursor = g.conn.execute("SELECT name FROM users WHERE uid = %s", uid)
			key['name'] = user_cursor.fetchone()[0]
			user_cursor.close()
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
