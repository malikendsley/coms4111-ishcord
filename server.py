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

def retrieve_prefs(uid):
    	# retrieve preferences from db
	try:
		cursor = g.conn.execute("""
			select color as user_color, text_size, primary_color, accent_color, line_spacing 
   			from users, theme_profiles_creates where theme_profiles_creates.uid = %s 
      		and theme_profiles_creates.name = current_theme;
			""", uid)
		prefs = cursor.fetchone()
		columns = cursor.keys()
		cursor.close()
	except:
		if cursor:
			cursor.close()
		return None
	return dict(zip(columns, prefs))
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
	try: 
		# require unique, non-empty username
		if len(name) == 0:
			raise Exception("Please enter a username")
		cursor = g.conn.execute("SELECT * FROM users WHERE name = %s", name)
		if cursor.rowcount > 0:
			raise Exception("Username already taken")
		cursor.close()
		# create new user and default theme, redirect to dashboard
		cursor = g.conn.execute("""
            BEGIN;
            INSERT INTO users (name, color) VALUES (%s, %s);
            INSERT INTO theme_profiles_creates (name, uid) VALUES ('default', currval('uid_sequence'));
			UPDATE users SET current_theme = 'default' WHERE uid = currval('uid_sequence');
   			COMMIT;
            """, name, color)
		# get uid of new user by name
		cursor = g.conn.execute("SELECT uid FROM users WHERE name = %s", name)
		uid = cursor.fetchone()[0]
		
		cursor.close()

	except Exception as e:
		print(f"Registration error: {e}")
		flash(f"Registration error: {str(e)}")
		return redirect(url_for('register'))
  
	print(f"User {name} registered with uid {uid} successfully")
	resp = make_response(redirect(url_for('dashboard')))
	resp.set_cookie('uid', str(uid))
	resp.set_cookie('name', name)
	flash(f"Welcome, {name}!")
	return resp

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
@app.route('/dashboard/<server>/', methods=['GET'], defaults={'channel': None})
@app.route('/dashboard/<server>/<channel>', methods=['GET'])
@login_required
def dashboard(server, channel):
	prefs = retrieve_prefs(request.cookies.get('uid'))
	if not prefs:
		flash("Error retrieving preferences")
	
	print("User visited dashboard")
	print(f"Server: {server}, Channel: {channel}")
	# if server and channel are specified, set cookies
	if server and not channel:
		resp = make_response(render_template('dashboard.html', name=request.cookies.get('name'), server=server, channel="general", uid=request.cookies.get('uid'), prefs=prefs))
		resp.set_cookie('server', server)
		resp.set_cookie('channel', "general")
		return resp
	if server and channel:
		resp = make_response(render_template('dashboard.html', name=request.cookies.get('name'), server=server, channel=channel, uid=request.cookies.get('uid'), prefs=prefs))
		resp.set_cookie('server', server)
		resp.set_cookie('channel', str(channel))
		return resp
	# if not, just show dashboard
	else:
		print("No server or channel specified")
		return render_template('dashboard.html', name=request.cookies.get('name'), server=server, channel=channel, uid=request.cookies.get('uid'), prefs=prefs)

@app.route('/', methods=['GET'])
def index():
	# if logged in, go to dashboard
	if authd(request):
		return redirect(url_for('dashboard'))
	else:
		print("User visited index page")
		return render_template('splash.html')

@app.route('/logout', methods=['GET'])
def logout():
	print("User logged out")
	resp = make_response(redirect('/'))
	resp.set_cookie('name', '', expires=0)
	resp.set_cookie('uid', '', expires=0)
	resp.set_cookie('server', '', expires=0)
	resp.set_cookie('channel', '', expires=0)
	return resp

@app.route('/profile', methods=['GET'])
@login_required	
def profile():
	print("User visited profile page")

	prefs = retrieve_prefs(request.cookies.get('uid'))
	if not prefs:
		flash("Error retrieving user preferences")
		return redirect(url_for('dashboard'))
	print(f"User preferences: {prefs}")
	return render_template('profile.html', name=request.cookies.get('name'), uid=request.cookies.get('uid'), prefs=prefs)

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
	server_name = request.form['server-name']
	server_desc = request.form['server-description']

	print(f"User {uid} try create server:", server_name, server_desc)
	# insert into db
	try:
		# check if server exists
		cursor = g.conn.execute("SELECT name FROM forums_administrates WHERE name = %s", server_name)
		if cursor.rowcount > 0:
			cursor.close()
			raise Exception("Server already exists")
		# try to setup server
		else:
			cursor.close()
			# TOOD: implement image URI
			nextfid = g.connn.execute("select nextval('forums_administrates_fid_seq')").fetchone()[0]
			if nextfid is None:
				raise Exception("Error getting next fid")
			g.conn.execute("""
				BEGIN;
    			INSERT INTO forums_administrates (name, description, uid) VALUES (%s, %s, %s);
				INSERT INTO channels_contains (cname, topic, fid) VALUES ('general', "general chat goes here", %s);
            	INSERT INTO member_of (uid, fid) VALUES (%s, %s);
				COMMIT;
              	""", 
          		server_name, server_desc, uid, nextfid, uid, nextfid)
			print(f"Server named {server_name} created, general channel created, user {uid} added to server")
	except Exception as e:
		print("Error creating server:", e)
		flash(f"Error creating server: {str(e)}")
		return redirect('/dashboard')

	flash("Server created successfully")
	return redirect('/dashboard')

# create a new channel
@app.route('/api/<fid>/create_channel', methods=['POST'])
def create_channel(fid):
	# get details
	name = request.form['channel-name']
	topic = request.form['channel-topic']

	print(f"New channel {name} created in server {fid}")
	try:
		# check if channel exists
		cursor = g.conn.execute("SELECT cname FROM channels_contains WHERE cname = %s AND fid = %s", name, fid)
		if cursor.rowcount > 0:
			cursor.close()
			raise Exception("Channel already exists")
		# create channel
		else:
			cursor.close()
			g.conn.execute("INSERT INTO channels_contains (cname, topic, fid) VALUES (%s, %s, %s)", name, topic, fid)
			print("New channel created")
		# get cname of new channel
		cursor = g.conn.execute("SELECT cname FROM channels_contains WHERE cname = %s AND fid = %s", name, fid)
		cname = cursor.fetchone()[0]
	except Exception as e:
		print(f"Error creating channel: {e}")
		flash(f"Error creating channel: {str(e)}")
		return redirect(f'/dashboard/{fid}')

	flash("Channel created successfully")
	return redirect(f'/dashboard/{fid}/{cname}')

# get all messages in a channel, long polling style
@app.route('/api/<server>/<channel>/<last>', methods=['GET'])
def get_messages(server, channel, last):
    
	print(f"User {request.cookies.get('uid')} requested messages in {server}/{channel} since {last}")
	
	try:
		while True:
			# get all messages since last_id3
			cursor = g.conn.execute("SELECT name, color, body, timestamp, mid FROM messages_sends_appears_in NATURAL JOIN users WHERE fid = %s AND cname = %s AND mid > %s", server, channel, last)
			# if there are new messages, return them
			if cursor.rowcount > 0:
				print("Sending new messages")
				messages = []
				for row in cursor:
					messages.append({'name': row[0], 'color': row[1], 'body': row[2], 'timestamp': row[3], 'mid': row[4]})
				cursor.close()
				return jsonify({'messages': messages})
			# otherwise, wait for new messages
			else:
				#print("Waiting for new messages")
				cursor.close()
				# increase this if sqlalchemy explodes
				time.sleep(3)
	except Exception as e:
		print("Error getting messages:", e)
		return jsonify({'success': False})

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
