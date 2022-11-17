import os
import urllib
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
		print("Connection closure exception:", e)

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
		select P.name as theme_name, color as user_color, text_size, primary_color, accent_color, line_spacing 
		from theme_profiles_creates as P left join users as U on U.uid = P.uid 
  		where P.name = U.current_theme and U.uid = %s;
			""", uid)
		prefs = cursor.fetchone()
		columns = cursor.keys()
	except:
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
		

	except Exception as e:
		print(f"Registration error: {e}")
		flash(f"Registration error: {str(e)}")
		return redirect(url_for('register'))
  
	print(f"User {name} registered with uid {uid} successfully")
	resp = make_response(redirect(url_for('dashboard')))
	print(uid)
	resp.set_cookie('uid', str(uid))
	resp.set_cookie('name', urllib.parse.quote(name))
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
			return redirect('/login')
		# log in user, go to dashboard
		else:
			print("Logging in as " + name)
			# close cursor
			# get uid of user, set cookie
			cursor = g.conn.execute("SELECT (uid) FROM users WHERE name = %s", name)
			uid = cursor.fetchone()[0]
			resp = make_response(redirect('/dashboard'))
			resp.set_cookie('name', urllib.parse.quote(name))
			resp.set_cookie('uid', urllib.parse.quote(str(uid)))
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
		resp.set_cookie('server', urllib.parse.quote(server))
		resp.set_cookie('channel', "general")
		return resp
	if server and channel:
		resp = make_response(render_template('dashboard.html', name=request.cookies.get('name'), server=server, channel=channel, uid=request.cookies.get('uid'), prefs=prefs))
		resp.set_cookie('server', server)
		print(f"Setting channel cookie to {channel}")
		# url encode channel name
		resp.set_cookie('channel', urllib.parse.quote(channel))
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

@app.route('/profiles/<uid>', methods=['GET'])
@login_required	
def profile(uid):
	print("User visited profile page")

	prefs = retrieve_prefs(request.cookies.get('uid'))
	if not prefs:
		flash("Error retrieving user preferences")
		return redirect(url_for('dashboard'))
	print(f"User preferences: {prefs}")
	return render_template('profile.html', name=request.cookies.get('name'), uid=uid, prefs=prefs)

@app.route('/profiles/<uid>/themes', methods=['GET', 'POST'])
@login_required
def themes(uid):
    # get themes for user
	if request.method == 'GET':
		print("User visited themes page")
		cursor = g.conn.execute("SELECT name, text_size, primary_color, accent_color, line_spacing FROM theme_profiles_creates WHERE uid = %s", uid)
		themes = []
		for row in cursor:
			themes.append({'name': row[0], 'text_size': row[1], 'primary_color': row[2], 'accent_color': row[3], 'line_spacing': row[4]})
		prefs = retrieve_prefs(request.cookies.get('uid'))
		if not prefs:
			flash("Error retrieving user preferences")
			return redirect(url_for('dashboard'))
		print(f"User preferences: {prefs}")
		return render_template('themes.html', name=request.cookies.get('name'), uid=request.cookies.get('uid'), prefs=prefs, themes=themes)
	elif request.method == 'POST':
		# update current_theme in users table
		print(f"User try change theme to {request.form['theme']}")
		try:
			theme = request.form['theme']
			g.conn.execute("UPDATE users SET current_theme = %s WHERE uid = %s", (theme, uid))
		except Exception as e:
			flash("Error updating theme")
			print(f"Error updating theme: {e}")
			return redirect(url_for('themes', uid=uid))
		print(f"Setting theme to {theme}")
		return redirect(url_for('themes', uid=uid))

@app.route('/profiles/<uid>/edit-theme', methods=['GET', 'POST'])
@login_required
def edit_theme(uid):
	if request.method == 'GET':
		print("User visited edit theme page")
		prefs = retrieve_prefs(request.cookies.get('uid'))
		if not prefs:
			flash("Error retrieving user preferences")
			return redirect(url_for('dashboard'))
		print(f"User preferences: {prefs}")
		return render_template('edit_theme.html', name=request.cookies.get('name'), uid=request.cookies.get('uid'), prefs=prefs)
	elif request.method == 'POST':
		# get new theme data from form
		theme_name = request.form['theme_name']
		text_size = request.form['text_size']
		primary_color = request.form['primary_color']
		accent_color = request.form['accent_color']
		line_spacing = request.form['line_spacing']
		# update theme
		try: 
			g.conn.execute("UPDATE theme_profiles_creates SET name = %s, text_size = %s, primary_color = %s, accent_color = %s, line_spacing = %s WHERE uid = %s AND name = %s", theme_name, text_size, primary_color, accent_color, line_spacing, uid, theme_name)
		except Exception as e:
			print(f"Error updating theme {theme_name}: {e}")
			flash("Error updating theme")
			return redirect(url_for('themes', uid=uid))
		print(f"Updated theme {theme_name}")
		flash("Theme updated")
		return redirect(url_for('themes', uid=uid))

@app.route('/profiles/<uid>/moderation', methods=['GET'])
@login_required
def moderation_landing(uid):
	print("User visited moderation page")
	prefs = retrieve_prefs(request.cookies.get('uid'))
	# get list of servers user is admin of
	try:
		cursor = g.conn.execute("""
			SELECT fid, name, created, description FROM forums_administrates WHERE uid = %s
  			""", uid)
		servers = []
		for row in cursor:
			servers.append({'fid': row[0], 'name': row[1], 'created': row[2], 'description': row[3]})
	except Exception as e:
		print(f"Error retrieving servers user {uid}")
		flash("Error retrieving servers")
		return redirect(url_for('dashboard', uid=uid))
	if not prefs:
		flash("Error retrieving user preferences")
		return redirect(url_for('dashboard'))
	print(f"User preferences: {prefs}")
	return render_template('moderation.html', name=request.cookies.get('name'), uid=request.cookies.get('uid'), prefs=prefs, servers=servers)

@app.route('/profiles/<uid>/moderation/<fid>', methods=['GET'])
@login_required
def moderate_server(uid, fid):
	data = {}
	# check that the user is an admin of the server
	if request.cookies.get('uid') != uid:
		flash("You are not authorized to view this page")
		return redirect(url_for('dashboard', uid=uid))

	# get server info
	server = []
	try:
		cursor = g.conn.execute("""
			SELECT fid, name, created, description FROM forums_administrates WHERE fid = %s;
        	""", fid)
		for row in cursor:
			server.append({'fid': row[0], 'name': row[1], 'created': row[2], 'description': row[3]})
	except Exception as e:
		print(f"Error retrieving server info: {e}")
		flash("Error retrieving server info")
		return redirect(url_for('moderation_landing', uid=uid))
	# get list of users in server
	users = []
	try:
		cursor = g.conn.execute("""
			SELECT name, uid FROM member_of NATURAL JOIN users WHERE fid = %s;
   			""", fid)
		for row in cursor:
			users.append({'name': row[0], 'uid': row[1]})
	except Exception as e:
		print(f"Error retrieving users in server: {e}")
		flash("Error retrieving users in server")
		return redirect(url_for('moderation_landing', uid=uid))

	# get list of channels in server
	channels = []
	try:
		cursor = g.conn.execute("""
			SELECT cname, topic FROM channels_contains WHERE fid = %s;
        """, fid)
		for row in cursor:
			channels.append({'cname': row[0], 'topic': row[1]})
	except Exception as e:
		print(f"Error retrieving channels in server: {e}")
		flash("Error retrieving channels in server")
		return redirect(url_for('moderation_landing', uid=uid))

	# get list of users by post frequency
	users_posts = []
 
	try:
		cursor = g.conn.execute("""
			select name, COUNT(*) from messages_sends_appears_in natural join users where fid = %s group by name order by count desc; """, fid)
		for row in cursor:
			users_posts.append({'name': row[0], 'count': row[1]})
	except Exception as e:
		print(f"Error retrieving users by post frequency: {e}")
		flash("Error retrieving users by post frequency")
		return redirect(url_for('moderation_landing', uid=uid))

	# get list of users by average post length
	users_avg_post_length = []
	try:
		cursor = g.conn.execute("""
			select name, AVG(length(body)) from messages_sends_appears_in natural join users where fid = %s group by name order by avg desc; """, fid)
		for row in cursor:
			users_avg_post_length.append({'name': row[0], 'avg': row[1]})
	except Exception as e:
		print(f"Error retrieving users by average post length: {e}")
		flash("Error retrieving users by average post length")
		return redirect(url_for('moderation_landing', uid=uid))

	# assemble lists into data dictionary
	data['server'] = server
	data['users'] = users
	data['channels'] = channels
	data['users_posts'] = users_posts
	data['users_avg_post_length'] = users_avg_post_length
 
	print("User visited moderation page")
	prefs = retrieve_prefs(request.cookies.get('uid'))
	if not prefs:
		flash("Error retrieving user preferences")
		return redirect(url_for('dashboard'))
	print(f"User preferences: {prefs}")
	return render_template('moderation-server.html', name=request.cookies.get('name'), uid=request.cookies.get('uid'), server=fid, prefs=prefs, data=data)

@app.route('/profiles/<uid>/friends', methods=['GET'])
def friends(uid):
	print("User visited friends page")
	prefs = retrieve_prefs(request.cookies.get('uid'))
	if not prefs:
		flash("Error retrieving user preferences")
		return redirect(url_for('dashboard'))
	print(f"User preferences: {prefs}")
	return render_template('friends.html', name=request.cookies.get('name'), uid=request.cookies.get('uid'), prefs=prefs)

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
		print(f"Message {body} posted successfully in {fid} / {cname} by {uid}")
		return redirect(url_for('dashboard', server=server, channel=channel))
	except Exception as e:
		print("Error posting message:", e)
		flash("Error posting message")
		return redirect(url_for('dashboard', server=server, channel=channel))

# create a new server
@app.route('/api/<uid>/create_server', methods=['POST'])
def create_server(uid):
	# get details
	server_name = request.form['server-name']
	server_desc = request.form['server-description']
	is_private = True if 'private' in request.form else False
    

	print(f"User {uid} try create server:", server_name, server_desc)
	# insert into db
	try:
		# check if server exists
		cursor = g.conn.execute("SELECT name FROM forums_administrates WHERE name = %s", server_name)
		if cursor.rowcount > 0:
			raise Exception("Server already exists")
		# try to setup server
		else:
			# if server is private, run this query
			if not is_private:
				print("Private server")
				permalink = request.form['permalink']
				print(f"Permalink {permalink}")
				g.conn.execute("""
					BEGIN;
					INSERT INTO forums_administrates (name, description, uid) VALUES (%s, %s, %s);
					INSERT INTO channels_contains (cname, topic, fid) VALUES ('general', 'general chat goes here', currval('forums_administrates_fid_seq'));
					INSERT INTO public_forums (fid, permalink) VALUES (currval('forums_administrates_fid_seq'), %s);
     				INSERT INTO member_of (uid, fid) VALUES (%s, currval('forums_administrates_fid_seq'));
					COMMIT;
					""", 
					server_name, server_desc, uid, permalink, uid)
				print(f"Public server named {server_name} created, general channel created, user {uid} added to server")
			else:
				print("Public server")
				capacity = request.form['capacity']
				print(f"Capacity: {capacity}")
				# if server is public, run this query
				g.conn.execute("""
					BEGIN;
					INSERT INTO forums_administrates (name, description, uid) VALUES (%s, %s, %s);
					INSERT INTO channels_contains (cname, topic, fid) VALUES ('general', 'general chat goes here', currval('forums_administrates_fid_seq'));
					INSERT INTO private_forums (fid, capacity) VALUES (currval('forums_administrates_fid_seq'), %s);
					INSERT INTO member_of (uid, fid) VALUES (%s, currval('forums_administrates_fid_seq'));
					COMMIT;
					""", 
					server_name, server_desc, uid, capacity, uid)
				print(f"Private server named {server_name} created, general channel created, user {uid} added to server")
	except Exception as e:
		print("Error creating server:", str(e.args))
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
			raise Exception("Channel already exists")
		# create channel
		else:
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

# get all messages in a channel
@app.route('/api/<server>/<channel>/<last>', methods=['GET'])
def get_messages(server, channel, last):
    
	print(f"User {request.cookies.get('uid')} requested messages in {server}/{channel} since {last}")
	try:
		# get all messages since last_id3
		cursor = g.conn.execute("SELECT name, color, body, timestamp, mid FROM messages_sends_appears_in NATURAL JOIN users WHERE fid = %s AND cname = %s AND mid > %s ORDER BY timestamp DESC", server, channel, last)
		# if there are new messages, return them
		if cursor.rowcount > 0:
			print("Sending new messages")
			messages = []
			for row in cursor:
				messages.append({'name': row[0], 'color': row[1], 'body': row[2], 'timestamp': row[3], 'mid': row[4]})
			return jsonify({'messages': messages})
		# otherwise, wait for new messages
		else:
			#print("Waiting for new messages")
			# increase this if sqlalchemy explodes
			return jsonify({'messages': []})
	except Exception as e:
		print("Error getting messages:", e)
		return jsonify({'success': False})

# create a new theme
@app.route('/api/<uid>/new_theme', methods=['POST'])
def create_theme(uid):
	# get form data
	theme_name = request.form['theme-name']
	theme_color = request.form['accent-color'][1:]
	theme_accent = request.form['primary-color'][1:]
	line_spacing = request.form['line-spacing']
	text_size = request.form['font-size']
	print(f"User {uid} try create theme:", theme_name, theme_color, theme_accent, line_spacing)
 
	try:
		# check if theme exists
		cursor = g.conn.execute("SELECT name FROM theme_profiles_creates WHERE name = %s AND uid = %s", theme_name, uid)
		if cursor.rowcount > 0:
			raise Exception("Theme already exists")
		# create theme
		else:
			g.conn.execute("INSERT INTO theme_profiles_creates (name, text_size, accent_color, primary_color, line_spacing, uid) VALUES (%s, %s, %s, %s, %s, %s)", theme_name, text_size, theme_color, theme_accent, line_spacing, uid)
			print("New theme created")
	except Exception as e:
		print(f"Error creating theme: {e}")
		flash(f"Error creating theme: {str(e)}")
		return redirect(url_for('themes', uid=uid))

	print(f"Theme {theme_name} created")
	flash("Theme created successfully")
	return redirect(url_for('themes', uid=uid))

# delete a theme
@app.route('/api/<uid>/delete_theme', methods=['POST'])
def delete_theme(uid):
	# get form data
	theme_name = request.form['theme']

	print(f"User {uid} try delete theme:", theme_name)
 
	try:
		# check if theme exists
		cursor = g.conn.execute("SELECT name FROM theme_profiles_creates WHERE name = %s AND uid = %s", theme_name, uid)
		if cursor.rowcount == 0:
			raise Exception("Theme does not exist")
		# delete theme
		else:
			g.conn.execute("DELETE FROM theme_profiles_creates WHERE name = %s AND uid = %s", theme_name, uid)
			print("Theme deleted")
	except Exception as e:
		print(f"Error deleting theme: {e}")
		flash(f"Error deleting theme: {str(e)}")
		return redirect(url_for('themes', uid=uid))

	print(f"Theme {theme_name} deleted")
	flash("Theme deleted successfully")
	return redirect(url_for('themes', uid=uid))

# delete a channel
@app.route('/api/<fid>/delete_channel', methods=['POST'])
def delete_channel(fid):
	# get form data
	cname = request.form['channel']

	print(f"User {request.cookies.get('uid')} try delete channel:", cname)
 
	try:
		# check if channel exists
		cursor = g.conn.execute("SELECT cname FROM channels_contains WHERE cname = %s AND fid = %s", cname, fid)
		if cursor.rowcount == 0:
			raise Exception("Channel does not exist")
		# delete channel
		else:
			g.conn.execute("DELETE FROM channels_contains WHERE cname = %s AND fid = %s", cname, fid)
			print("Channel deleted")
	except Exception as e:
		print(f"Error deleting channel: {e}")
		flash(f"Error deleting channel: {str(e)}")
		return redirect(f'/dashboard/{fid}')

	print(f"Channel {cname} deleted")
	flash("Channel deleted successfully")
	return redirect(url_for('moderate_server', uid=request.cookies.get('uid'), fid=fid))

# remove a user from a server
@app.route('/api/<fid>/remove_user', methods=['POST'])
def remove_user(fid):
	# get form data
	uid = request.form['uid']

	print(f"User {request.cookies.get('uid')} try remove user {uid} from server {fid}")
 
	try:
		# check if user is in channel
		cursor = g.conn.execute("SELECT uid FROM member_of WHERE uid = %s AND fid = %s", uid, fid)
		if cursor.rowcount == 0:
			raise Exception("User is not in server")

		# check if user is owner
		cursor = g.conn.execute("SELECT uid FROM owns WHERE uid = %s AND fid = %s", uid, fid)
		if cursor.rowcount > 0:
			raise Exception("User is owner of server")

		# remove user
		else:
			g.conn.execute("DELETE FROM member_of WHERE uid = %s AND fid = %s", uid, fid)
			print("User removed")

	except Exception as e:
		print(f"Error removing user from server: {e}")
		flash(f"Error removing user from server: {str(e)}")
		return redirect(url_for('moderate_server', uid=request.cookies.get('uid'), fid=fid))

	print(f"User {uid} removed from server {fid}")
	flash("User removed from server successfully")
	return redirect(url_for('moderate_server', uid=request.cookies.get('uid'), fid=fid))

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
