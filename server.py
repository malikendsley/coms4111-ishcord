import secrets
import os
import urllib
# accessible as a variable in index.html:
from sqlalchemy import *
from flask import Flask, flash, jsonify, make_response, request, render_template, g, redirect, url_for
from functools import wraps

tmpl_dir = os.path.join(os.path.dirname(
    os.path.abspath(__file__)), 'templates')
static_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static')
app = Flask(__name__, template_folder=tmpl_dir, static_folder=static_dir)

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
        # check if user cookie is set
        if not authd(request):
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function


def forum_selection_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        print("User hit forum guard:", request.url)
        # check if a forum and channel are selected
        if not forum_selected(request):
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function


def authd(request):
    return request.cookies.get('uid') is not None and request.cookies.get('name') is not None


def forum_selected(request):
    return request.cookies.get('forum') is not None and request.cookies.get('channel') is not None


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
            cursor = g.conn.execute(
                "SELECT (uid) FROM users WHERE name = %s", name)
            uid = cursor.fetchone()[0]
            resp = make_response(redirect('/dashboard'))
            resp.set_cookie('name', urllib.parse.quote(name))
            resp.set_cookie('uid', urllib.parse.quote(str(uid)))
            return resp

@app.route('/dashboard', methods=['GET'], defaults={'forum': None, 'channel': None})
@app.route('/dashboard/<forum>/', methods=['GET'], defaults={'channel': None})
@app.route('/dashboard/<forum>/<channel>', methods=['GET'])
@login_required
def dashboard(forum, channel):
    prefs = retrieve_prefs(request.cookies.get('uid'))
    if not prefs:
        flash("Error retrieving preferences")

    print("User visited dashboard")
    print(f"Forum: {forum}, Channel: {channel}")
    # if forum and channel are specified, set cookies
    if forum and not channel:
        resp = make_response(render_template('dashboard.html', name=request.cookies.get(
            'name'), forum=forum, channel="general", uid=request.cookies.get('uid'), prefs=prefs))
        resp.set_cookie('forum', urllib.parse.quote(forum))
        resp.set_cookie('channel', "general")
        return resp
    if forum and channel:
        resp = make_response(render_template('dashboard.html', name=request.cookies.get(
            'name'), forum=forum, channel=channel, uid=request.cookies.get('uid'), prefs=prefs))
        resp.set_cookie('forum', forum)
        print(f"Setting channel cookie to {channel}")
        # url encode channel name
        resp.set_cookie('channel', urllib.parse.quote(channel))
        return resp
    # if not, just show dashboard
    else:
        print("No forum or channel specified")
        return render_template('dashboard.html', name=request.cookies.get('name'), forum=forum, channel=channel, uid=request.cookies.get('uid'), prefs=prefs)

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
    resp.set_cookie('forum', '', expires=0)
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

    return render_template('profile.html', name=request.cookies.get('name'), uid=uid, prefs=prefs)

@app.route('/profiles/<uid>/themes', methods=['GET', 'POST'])
@login_required
def themes(uid):
    # get themes for user
    if request.method == 'GET':
        print("User visited themes page")
        cursor = g.conn.execute(
            "SELECT name, text_size, primary_color, accent_color, line_spacing FROM theme_profiles_creates WHERE uid = %s", uid)
        themes = []
        for row in cursor:
            themes.append({'name': row[0], 'text_size': row[1], 'primary_color': row[2],
                          'accent_color': row[3], 'line_spacing': row[4]})
        prefs = retrieve_prefs(request.cookies.get('uid'))
        if not prefs:
            flash("Error retrieving user preferences")
            return redirect(url_for('dashboard'))

        return render_template('themes.html', name=request.cookies.get('name'), uid=request.cookies.get('uid'), prefs=prefs, themes=themes)
    elif request.method == 'POST':
        # update current_theme in users table
        print(f"User try change theme to {request.form['theme']}")
        try:
            theme = request.form['theme']
            g.conn.execute(
                "UPDATE users SET current_theme = %s WHERE uid = %s", (theme, uid))
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
            g.conn.execute("UPDATE theme_profiles_creates SET name = %s, text_size = %s, primary_color = %s, accent_color = %s, line_spacing = %s WHERE uid = %s AND name = %s",
                           theme_name, text_size, primary_color, accent_color, line_spacing, uid, theme_name)
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
    # get list of forums user is admin of
    try:
        cursor = g.conn.execute("""
			SELECT fid, name, created, description FROM forums_administrates WHERE uid = %s
  			""", uid)
        forums = []
        for row in cursor:
            forums.append(
                {'fid': row[0], 'name': row[1], 'created': row[2], 'description': row[3]})
    except Exception as e:
        print(f"Error retrieving forums user {uid}")
        flash("Error retrieving forums")
        return redirect(url_for('dashboard', uid=uid))
    if not prefs:
        flash("Error retrieving user preferences")
        return redirect(url_for('dashboard'))

    return render_template('moderation.html', name=request.cookies.get('name'), uid=request.cookies.get('uid'), prefs=prefs, forums=forums)

@app.route('/profiles/<uid>/moderation/<fid>', methods=['GET'])
@login_required
def moderate_forum(uid, fid):
    data = {}
    # check that the user is an admin of the forum
    if request.cookies.get('uid') != uid:
        flash("You are not authorized to view this page")
        return redirect(url_for('dashboard', uid=uid))

    # get forum info
    forum = []
    try:
        cursor = g.conn.execute("""
			SELECT fid, name, created, description FROM forums_administrates WHERE fid = %s;
        	""", fid)
        for row in cursor:
            forum.append({'fid': row[0], 'name': row[1],
                         'created': row[2], 'description': row[3]})
    except Exception as e:
        print(f"Error retrieving forum info: {e}")
        flash("Error retrieving forum info")
        return redirect(url_for('moderation_landing', uid=uid))
    # get list of users in forum
    users = []
    try:
        cursor = g.conn.execute("""
			SELECT name, uid FROM member_of NATURAL JOIN users WHERE fid = %s;
   			""", fid)
        for row in cursor:
            users.append({'name': row[0], 'uid': row[1]})
    except Exception as e:
        print(f"Error retrieving users in forum: {e}")
        flash("Error retrieving users in forum")
        return redirect(url_for('moderation_landing', uid=uid))

    # get list of channels in forum
    channels = []
    try:
        cursor = g.conn.execute("""
			SELECT cname, topic FROM channels_contains WHERE fid = %s;
        """, fid)
        for row in cursor:
            channels.append({'cname': row[0], 'topic': row[1]})
    except Exception as e:
        print(f"Error retrieving channels in forum: {e}")
        flash("Error retrieving channels in forum")
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
    data['forum'] = forum
    data['users'] = users
    data['channels'] = channels
    data['users_posts'] = users_posts
    data['users_avg_post_length'] = users_avg_post_length

    print("User visited moderation page")
    prefs = retrieve_prefs(request.cookies.get('uid'))
    if not prefs:
        flash("Error retrieving user preferences")
        return redirect(url_for('dashboard'))

    return render_template('moderation-forum.html', name=request.cookies.get('name'), uid=request.cookies.get('uid'), forum=fid, prefs=prefs, data=data)

@app.route('/profiles/<uid>/friends', methods=['GET'])
def friends(uid):
    print("User visited friends page")
    data = {}
    # get list of friends
    friends = []
    try:
        cursor = g.conn.execute("""
			select uid, name
   			from users U left join friends_with F on U.uid = F.uid_sender 
      		where F.uid_receiver = %s and status = 'accepted' 
			union 
   			select uid, name 
      		from users U left join friends_with F on U.uid = F.uid_receiver 
        	where  F.uid_sender = %s and status = 'accepted';
  		""", uid, uid)
        for row in cursor:
            friends.append({'uid': row[0], 'name': row[1]})
    except Exception as e:
        print(f"Error retrieving friends: {e}")
        flash("Error retrieving friends")
        return redirect(url_for('dashboard'))

    # get list of forum invites
    invites = []
    try:
        cursor = g.conn.execute("""
			select forums_administrates.name, forums_administrates.fid
   			from invites_to left join users on invites_to.uid_invitee = users.uid 
      		left join forums_administrates on invites_to.fid = forums_administrates.fid 
        	where users.uid = %s;
   			""", uid)
        for row in cursor:
            invites.append({'forum_name': row[0], 'uid': row[1]})
    except Exception as e:
        print(f"Error retrieving invites: {e}")
        flash("Error retrieving invites")
        return redirect(url_for('dashboard'))

    # get list of friend requests
    requests = []
    try:
        cursor = g.conn.execute("""
			select uid_sender, name 
   			from friends_with left join users on uid_sender = uid 
      		where uid_receiver = %s and status = 'pending';
   			""", uid)
        for row in cursor:
            requests.append({'uid': row[0], 'name': row[1]})
    except Exception as e:
        print(f"Error retrieving friend requests: {e}")
        flash("Error retrieving friend requests")
        return redirect(url_for('dashboard'))

    # assemble lists into data dictionary
    data['friends'] = friends
    data['invites'] = invites
    data['requests'] = requests

    prefs = retrieve_prefs(request.cookies.get('uid'))
    if not prefs:
        flash("Error retrieving user preferences")
        return redirect(url_for('dashboard'))

    return render_template('friends.html', name=request.cookies.get('name'), uid=request.cookies.get('uid'), prefs=prefs, data=data)

@app.route('/profiles/<fid>/add-users', methods=['GET'])
def invite_to_forum(fid):
    print("User visited invite to forum page")

    uid = request.cookies.get('uid')
    data = {}

    # get list of friends of the user
    users = []
    try:
        cursor = g.conn.execute("""
			select uid, name
   			from users U left join friends_with F on U.uid = F.uid_sender 
	  		where F.uid_receiver = %s and status = 'accepted' 
			union 
   			select uid, name 
	  		from users U left join friends_with F on U.uid = F.uid_receiver 
			where  F.uid_sender = %s and status = 'accepted';
  		""", uid, uid)
        for row in cursor:
            users.append({'uid': row[0], 'name': row[1]})
    except Exception as e:
        print(f"Error retrieving users: {e}")
        flash("Error retrieving users")
        return redirect(url_for('dashboard'))

    # get forum details
    forum = []
    try:
        cursor = g.conn.execute("""
			select name, description from forums_administrates where fid = %s; 
   		""", fid)
        for row in cursor:
            forum.append({'name': row[0], 'description': row[1]})
    except Exception as e:
        print(f"Error retrieving forum: {e}")
        flash("Error retrieving forum")
        return redirect(url_for('dashboard'))

    # assemble lists into data dictionary
    data['users'] = users
    data['forum'] = forum

    prefs = retrieve_prefs(request.cookies.get('uid'))
    if not prefs:
        flash("Error retrieving user preferences")
        return redirect(url_for('dashboard'))

    return render_template('invite-users.html', name=request.cookies.get('name'), uid=request.cookies.get('uid'), forum=fid, prefs=prefs, data=data)

@app.errorhandler(404)
def page_not_found(e):
    print("User hit 404:", request.url)
    return render_template('404.html'), 404

# ============= These functions are API endpoints ============= #

# post a new message
@app.route('/api/<forum>/<channel>/post', methods=['POST'])
@login_required
def post(forum, channel):
    # get message
    body = request.form['message']
    # get uid
    uid = request.cookies.get('uid')
    # get forum and channel
    fid = forum
    cname = channel
    # insert into db
    print("User posted message:", body, "to", fid, cname)
    try:

        g.conn.execute(
            "INSERT INTO messages_sends_appears_in (body, uid, fid, cname) VALUES (%s, %s, %s, %s)", body, uid, fid, cname)
        print(
            f"Message {body} posted successfully in {fid} / {cname} by {uid}")
        return redirect(url_for('dashboard', forum=forum, channel=channel))
    except Exception as e:
        print("Error posting message:", e)
        flash("Error posting message")
        return redirect(url_for('dashboard', forum=forum, channel=channel))

# create a new forum
@app.route('/api/<uid>/create_forum', methods=['POST'])
def create_forum(uid):
    # get details
    forum_name = request.form['forum-name']
    forum_desc = request.form['forum-description']
    is_private = True if 'private' in request.form else False

    print(f"User {uid} try create forum:", forum_name, forum_desc)
    # insert into db
    try:
        # check if forum exists
        cursor = g.conn.execute(
            "SELECT name FROM forums_administrates WHERE name = %s", forum_name)
        if cursor.rowcount > 0:
            raise Exception("Forum already exists")
        # try to setup forum
        else:
            # if forum is private, run this query
            if not is_private:
                print("Private forum")
                permalink = request.form['permalink']

                # check that permalink is unique
                cursor = g.conn.execute(
                    "SELECT permalink FROM public_forums WHERE permalink = %s", permalink)
                if cursor.rowcount > 0:
                    raise Exception("Permalink already exists")
                # insert into db
                print(f"Permalink {permalink}")
                g.conn.execute("""
					BEGIN;
					INSERT INTO forums_administrates (name, description, uid) VALUES (%s, %s, %s);
					INSERT INTO channels_contains (cname, topic, fid) VALUES ('general', 'general chat goes here', currval('forums_administrates_fid_seq'));
					INSERT INTO public_forums (fid, permalink) VALUES (currval('forums_administrates_fid_seq'), %s);
     				INSERT INTO member_of (uid, fid) VALUES (%s, currval('forums_administrates_fid_seq'));
					COMMIT;
					""",
                               forum_name, forum_desc, uid, permalink, uid)
                print(
                    f"Public forum named {forum_name} created, general channel created, user {uid} added to forum")
            else:
                print("Public forum")
                capacity = request.form['capacity']
                if not capacity.isdigit():
                    raise Exception("Capacity must be a number")
                if int(capacity) < 1:
                    raise Exception("Capacity must be greater than 0")
                print(f"Capacity: {capacity}")
                # if forum is public, run this query
                g.conn.execute("""
					BEGIN;
					INSERT INTO forums_administrates (name, description, uid) VALUES (%s, %s, %s);
					INSERT INTO channels_contains (cname, topic, fid) VALUES ('general', 'general chat goes here', currval('forums_administrates_fid_seq'));
					INSERT INTO private_forums (fid, capacity) VALUES (currval('forums_administrates_fid_seq'), %s);
					INSERT INTO member_of (uid, fid) VALUES (%s, currval('forums_administrates_fid_seq'));
					COMMIT;
					""",
                               forum_name, forum_desc, uid, capacity, uid)
                print(
                    f"Private forum named {forum_name} created, general channel created, user {uid} added to forum")
    except Exception as e:
        print("Error creating forum:", str(e.args))
        flash(f"Error creating forum: {str(e)}")
        return redirect('/dashboard')

    flash("Forum created successfully")
    return redirect('/dashboard')

# create a new channel
@app.route('/api/<fid>/create_channel', methods=['POST'])
def create_channel(fid):
    # get details
    name = request.form['channel-name']
    topic = request.form['channel-topic']

    print(f"New channel {name} created in forum {fid}")
    try:
        # check if channel exists
        cursor = g.conn.execute(
            "SELECT cname FROM channels_contains WHERE cname = %s AND fid = %s", name, fid)
        if cursor.rowcount > 0:
            raise Exception("Channel already exists")
        # create channel
        else:
            g.conn.execute(
                "INSERT INTO channels_contains (cname, topic, fid) VALUES (%s, %s, %s)", name, topic, fid)
            print("New channel created")
        # get cname of new channel
        cursor = g.conn.execute(
            "SELECT cname FROM channels_contains WHERE cname = %s AND fid = %s", name, fid)
        cname = cursor.fetchone()[0]
    except Exception as e:
        print(f"Error creating channel: {e}")
        flash(f"Error creating channel: {str(e)}")
        return redirect(f'/dashboard/{fid}')

    flash("Channel created successfully")
    return redirect(f'/dashboard/{fid}/{cname}')

# get all messages in a channel
@app.route('/api/<forum>/<channel>/<last>', methods=['GET'])
def get_messages(forum, channel, last):

    print(
        f"User {request.cookies.get('uid')} requested messages in {forum}/{channel} since {last}")
    try:
        # get all messages since last_id3
        cursor = g.conn.execute(
            "SELECT name, color, body, timestamp, mid FROM messages_sends_appears_in NATURAL JOIN users WHERE fid = %s AND cname = %s AND mid > %s ORDER BY timestamp DESC", forum, channel, last)
        # if there are new messages, return them
        if cursor.rowcount > 0:
            print("Sending new messages")
            messages = []
            for row in cursor:
                messages.append(
                    {'name': row[0], 'color': row[1], 'body': row[2], 'timestamp': row[3], 'mid': row[4]})
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
    print(f"User {uid} try create theme:", theme_name,
          theme_color, theme_accent, line_spacing)

    try:
        # check if theme exists
        cursor = g.conn.execute(
            "SELECT name FROM theme_profiles_creates WHERE name = %s AND uid = %s", theme_name, uid)
        if cursor.rowcount > 0:
            raise Exception("Theme already exists")
        # create theme
        else:
            g.conn.execute("INSERT INTO theme_profiles_creates (name, text_size, accent_color, primary_color, line_spacing, uid) VALUES (%s, %s, %s, %s, %s, %s)",
                           theme_name, text_size, theme_color, theme_accent, line_spacing, uid)
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
        cursor = g.conn.execute(
            "SELECT name FROM theme_profiles_creates WHERE name = %s AND uid = %s", theme_name, uid)
        if cursor.rowcount == 0:
            raise Exception("Theme does not exist")
        # delete theme
        else:
            g.conn.execute(
                "DELETE FROM theme_profiles_creates WHERE name = %s AND uid = %s", theme_name, uid)
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
        cursor = g.conn.execute(
            "SELECT cname FROM channels_contains WHERE cname = %s AND fid = %s", cname, fid)
        if cursor.rowcount == 0:
            raise Exception("Channel does not exist")
        # delete channel
        else:
            g.conn.execute(
                "DELETE FROM channels_contains WHERE cname = %s AND fid = %s", cname, fid)
            print("Channel deleted")
    except Exception as e:
        print(f"Error deleting channel: {e}")
        flash(f"Error deleting channel: {str(e)}")
        return redirect(f'/dashboard/{fid}')

    print(f"Channel {cname} deleted")
    flash("Channel deleted successfully")
    return redirect(url_for('moderate_forum', uid=request.cookies.get('uid'), fid=fid))

# remove a user from a forum
@app.route('/api/<fid>/remove_user', methods=['POST'])
def remove_user(fid):
    # get form data
    uid = request.form['uid']

    print(
        f"User {request.cookies.get('uid')} try remove user {uid} from forum {fid}")

    try:
        # check if user is in channel
        cursor = g.conn.execute(
            "SELECT uid FROM member_of WHERE uid = %s AND fid = %s", uid, fid)
        if cursor.rowcount == 0:
            raise Exception("User is not in forum")

        # check if user is owner
        cursor = g.conn.execute(
            "SELECT uid FROM forums_administrates WHERE uid = %s AND fid = %s", uid, fid)
        if cursor.rowcount > 0:
            raise Exception("User is owner of forum")

        # remove user
        else:
            g.conn.execute(
                "DELETE FROM member_of WHERE uid = %s AND fid = %s", uid, fid)
            print("User removed")

    except Exception as e:
        print(f"Error removing user from forum: {e}")
        flash(f"Error removing user from forum: {str(e)}")
        return redirect(url_for('moderate_forum', uid=request.cookies.get('uid'), fid=fid))

    print(f"User {uid} removed from forum {fid}")
    flash("User removed from forum successfully")
    return redirect(url_for('moderate_forum', uid=request.cookies.get('uid'), fid=fid))

# delete a forum
@app.route('/api/<fid>/delete_forum', methods=['POST'])
def delete_forum(fid):
    print(f"User {request.cookies.get('uid')} try delete forum {fid}")

    try:
        # check if forum exists
        cursor = g.conn.execute(
            "SELECT fid FROM forums_administrates WHERE fid = %s", fid)
        if cursor.rowcount == 0:
            raise Exception("Forum does not exist")

        # delete forum
        else:
            g.conn.execute(
                "DELETE FROM forums_administrates WHERE fid = %s", fid)
            print("Forum deleted")

    except Exception as e:
        print(f"Error deleting forum: {e}")
        flash(f"Error deleting forum: {str(e)}")
        return redirect(url_for('dashboard', uid=request.cookies.get('uid')))

    print(f"Forum {fid} deleted")
    flash("Forum deleted successfully")
    return redirect(url_for('dashboard', uid=request.cookies.get('uid')))

# accept a request to join a forum
@app.route('/api/<fid>/accept_request', methods=['POST'])
def join_forum_private(fid):
    # get form data
    uid = request.form['uid']

    try:
        # check if forum exists
        cursor = g.conn.execute(
            "SELECT fid FROM forums_administrates WHERE fid = %s", fid)
        if cursor.rowcount == 0:
            raise Exception("Forum does not exist")

        # check if user is already in forum
        cursor = g.conn.execute(
            "SELECT uid FROM member_of WHERE uid = %s AND fid = %s", uid, fid)
        if cursor.rowcount > 0:
            raise Exception("User is already in forum")

        # check that the forum is not full
        cursor = g.conn.execute(
            "SELECT COUNT(uid) FROM member_of WHERE fid = %s", fid)
        cur_members = cursor.fetchone()[0]

        cursor = g.conn.execute(
            "SELECT capacity FROM private_forums WHERE fid = %s", fid)
        capacity = cursor.fetchone()[0]

        if cur_members >= capacity:

            raise Exception("Forum is full")

        # accept request
        else:
            g.conn.execute("""
				BEGIN;
				INSERT INTO member_of VALUES (%s, %s)
				DELETE FROM invites_to WHERE uid_invitee = %s AND fid = %s
				COMMIT;
       			""", uid, fid, uid, fid)
            # delete request
            print("User accepted")

    except Exception as e:
        print(f"Error accepting user: {e}")
        flash(f"Error accepting user: {str(e)}")
        return redirect(url_for('friends', uid=request.cookies.get('uid'), fid=fid))

    print(f"User {uid} accepted")
    flash("User accepted successfully")
    return redirect(url_for('friends', uid=request.cookies.get('uid'), fid=fid))

# reject a request to join a forum
@app.route('/api/<fid>/reject_request', methods=['POST'])
def reject_forum(fid):
    # get form data
    uid = request.form['uid']

    try:

        g.conn.execute(
            "DELETE FROM invites_to WHERE uid_invitee = %s AND fid = %s", uid, fid)
        print("User rejected")

    except Exception as e:
        print(f"Error rejecting forum: {e}")
        flash(f"Error rejecting forum: {str(e)}")
        return redirect(url_for('friends', uid=request.cookies.get('uid'), fid=fid))

    print(f"Forum {fid} rejected")
    flash("Forum request deleted successfully")
    return redirect(url_for('friends', uid=request.cookies.get('uid'), fid=fid))

# send a friend request
@app.route('/api/<uid>/send_request', methods=['POST'])
def send_request(uid):
    # get form data
    username = request.form['username']
    our_uid = request.cookies.get('uid')
    if username == "":
        flash("Please enter a username")
        return redirect(url_for('friends', uid=our_uid))
    if request.cookies.get('name') == username:
        flash("You can't send a friend request to yourself")
        return redirect(url_for('friends', uid=our_uid))
    try:
        # check if user exists
        cursor = g.conn.execute(
            "SELECT uid FROM users WHERE name = %s", username)
        if cursor.rowcount == 0:
            raise Exception("User does not exist")

        # check if user is already friends
        cursor = g.conn.execute("""
			select uid from users where uid in (select uid
   			from users U left join friends_with F on U.uid = F.uid_sender 
      		where F.uid_receiver = %s and status = 'accepted' 
			union 
   			select uid 
      		from users U left join friends_with F on U.uid = F.uid_receiver 
        	where  F.uid_sender = %s and status = 'accepted')
			and name = %s;
   			""", our_uid, uid, username)

        if cursor.rowcount > 0:
            raise Exception("User is already friends")

        # check if a request already exists
        cursor = g.conn.execute("""
			select uid from users where uid in (
			select uid_sender from friends_with where uid_receiver = %s and status = 'pending'
			union
			select uid_receiver from friends_with where uid_sender = %s and status = 'pending')
			and name = %s
   			""", uid, uid, username)
        if cursor.rowcount > 0:
            raise Exception("Request already exists")

        # send request
        else:
            # get uid of user to send request to
            cursor = g.conn.execute(
                "SELECT uid FROM users WHERE name = %s", username)
            uid_invitee = cursor.fetchone()[0]
            g.conn.execute(
                "INSERT INTO friends_with (uid_sender, uid_receiver) VALUES (%s, %s)", our_uid, uid_invitee)
            print("Request sent")

    except Exception as e:
        print(f"Error sending request: {e}")
        flash(f"Error sending request: {str(e)}")
        return redirect(url_for('friends', uid=our_uid, username=username))

    print(f"Request sent to {username}")
    flash("Request sent successfully")
    return redirect(url_for('friends', uid=our_uid, username=username))

# accept a friend request
@app.route('/api/<uid>/accept_friend', methods=['POST'])
def accept_friend(uid):
    # get form data
    uid_inviter = request.form['uid_invitee']

    try:
        # check if user exists
        cursor = g.conn.execute("SELECT uid FROM users WHERE uid = %s", uid)
        if cursor.rowcount == 0:
            raise Exception("User does not exist")

        # add friend
        else:
            g.conn.execute("""
				UPDATE friends_with SET status = 'accepted' WHERE uid_sender = %s AND uid_receiver = %s
				""", uid_inviter, uid)

    except Exception as e:
        print(f"Error accepting friend: {e}")
        flash(f"Error accepting friend: {str(e)}")
        return redirect(url_for('friends', uid=request.cookies.get('uid')))

    print(f"User {uid_inviter} accepted")
    flash("User accepted successfully")
    return redirect(url_for('friends', uid=request.cookies.get('uid')))

# reject a friend request
@app.route('/api/<uid>/reject_friend', methods=['POST'])
def reject_friend(uid):
    # get form data
    uid_inviter = request.form['uid_invitee']

    try:
        # check if user exists
        cursor = g.conn.execute("SELECT uid FROM users WHERE uid = %s", uid)
        if cursor.rowcount == 0:
            raise Exception("User does not exist")

        # delete friend
        else:
            g.conn.execute("""
				DELETE FROM friends_with WHERE uid_sender = %s AND uid_receiver = %s
				""", uid_inviter, uid)

    except Exception as e:
        print(f"Error rejecting friend: {e}")
        flash(f"Error rejecting friend: {str(e)}")
        return redirect(url_for('friends', uid=request.cookies.get('uid')))

    print(f"User {uid_inviter} rejected")
    flash("User rejected successfully")
    return redirect(url_for('friends', uid=request.cookies.get('uid')))

# delete a friend
@app.route('/api/<uid>/delete_friend', methods=['POST'])
def delete_friend(uid):
    # get form data
    uid_friend = request.form['uid_friend']

    try:
        # check if user exists
        cursor = g.conn.execute("SELECT uid FROM users WHERE uid = %s", uid)
        if cursor.rowcount == 0:
            raise Exception("User does not exist")

        # delete friend
        else:
            g.conn.execute("""
                BEGIN;
				DELETE FROM friends_with WHERE uid_sender = %s AND uid_receiver = %s;
				DELETE FROM friends_with WHERE uid_sender = %s AND uid_receiver = %s;
				COMMIT;
				""", uid_friend, uid, uid, uid_friend)

    except Exception as e:
        print(f"Error deleting friend: {e}")
        flash(f"Error deleting friend: {str(e)}")
        return redirect(url_for('friends', uid=request.cookies.get('uid')))

    print(f"User {uid_friend} deleted")
    flash("User deleted successfully")
    return redirect(url_for('friends', uid=request.cookies.get('uid')))

# join a public forum by permalink
@app.route('/api/<uid>/join_forum', methods=['POST'])
def join_forum_public(uid):
    # get form data
    permalink = request.form['permalink']
    try:
        # check if permalink exists
        cursor = g.conn.execute(
            "SELECT fid FROM public_forums WHERE permalink = %s", permalink)
        if cursor.rowcount == 0:
            raise Exception("Forum does not exist")

		# get the fid of the forum the user wants to join
        fid = cursor.fetchone()[0]
        # check if user is already in forum
        cursor = g.conn.execute(
            "SELECT uid FROM member_of WHERE uid = %s AND fid = %s", uid, fid)
        if cursor.rowcount > 0:
            raise Exception("User is already in forum")

        # join forum
        else:
            # get fid of forum to join
            cursor = g.conn.execute(
                "SELECT fid FROM public_forums WHERE permalink = %s", permalink)
            fid = cursor.fetchone()[0]
            g.conn.execute(
                "INSERT INTO member_of (uid, fid) VALUES (%s, %s)", uid, fid)
            print("Forum joined")

    except Exception as e:
        print(f"Error joining forum: {e}")
        flash(f"Error joining forum: {str(e)}")
        return redirect(url_for('friends', uid=request.cookies.get('uid')))

    print(f"Forum {fid} joined")
    flash("Forum joined successfully")
    return redirect(url_for('friends', uid=request.cookies.get('uid')))

# invite a user to a public forum
@app.route('/api/<fid>/invite_user', methods=['POST'])
def invite_user_public(fid):
    # get form data
    uid_invitee = request.form['uid']
    uid_inviter = request.cookies.get('uid')
    try:
        # check if user exists
        cursor = g.conn.execute(
            "SELECT uid FROM users WHERE uid = %s", uid_invitee)
        if cursor.rowcount == 0:
            raise Exception("User does not exist")

        # check if request already exists in either direction
        cursor = g.conn.execute("""
            select uid from users where uid in (
			select uid_invitee from invites_to where uid_inviter = %s and fid = %s
			union
			select uid_inviter from invites_to where uid_invitee = %s and fid = %s
			)
            """, uid_inviter, fid, uid_inviter, fid)
        if cursor.rowcount > 0:
            raise Exception("Request already exists")

        # check if user is already in forum
        cursor = g.conn.execute(
            "SELECT uid FROM member_of WHERE uid = %s AND fid = %s", uid_invitee, fid)
        if cursor.rowcount > 0:
            raise Exception("User is already in forum")

        # check that forum is public
        cursor = g.conn.execute(
            "SELECT fid FROM public_forums WHERE fid = %s", fid)
        if cursor.rowcount == 0:
            raise Exception("Forum is not public")

        # invite user
        else:
            g.conn.execute("""
				INSERT INTO invites_to (uid_inviter, uid_invitee, fid) VALUES (%s, %s, %s)
    			""", uid_inviter, uid_invitee, fid)
            print("User invited")

    except Exception as e:
        print(f"Error inviting user: {e}")
        flash(f"Error inviting user: {str(e)}")
        return redirect(url_for('invite_to_forum', uid=request.cookies.get('uid'), fid=fid))

    print(f"User {uid_invitee} invited")
    flash("User invited successfully")
    return redirect(url_for('invite_to_forum', uid=request.cookies.get('uid'), fid=fid))

# delete a user account
@app.route('/api/<uid>/delete', methods=['POST'])
def delete_account(uid):
	try:
		# check if user exists
		cursor = g.conn.execute("SELECT uid FROM users WHERE uid = %s", uid)
		if cursor.rowcount == 0:
			raise Exception("User does not exist")

		# delete account
		else:
			g.conn.execute("""
				BEGIN;
				DELETE FROM users WHERE uid = %s;
				DELETE FROM invites_to WHERE uid_inviter = %s OR uid_invitee = %s;
				COMMIT;
				""", uid, uid, uid)

	except Exception as e:
		print(f"Error deleting account: {e}")
		flash(f"Error deleting account: {str(e)}")
		return redirect(url_for('friends', uid=request.cookies.get('uid')))

	print(f"User {uid} deleted")
	flash("User deleted successfully")
	return redirect(url_for('logout'))

# leave a forum
@app.route('/api/<uid>/leave', methods=['POST'])
def leave_forum(uid):
	# get form data
	fid = request.form['fid']
	try:
		# check if user is in forum
		cursor = g.conn.execute(
			"SELECT uid FROM member_of WHERE uid = %s AND fid = %s", uid, fid)
		if cursor.rowcount == 0:
			raise Exception("User is not in forum")

		# leave forum
		else:
			g.conn.execute(
				"DELETE FROM member_of WHERE uid = %s AND fid = %s", uid, fid)

	except Exception as e:
		print(f"Error leaving forum: {e}")
		flash(f"Error leaving forum: {str(e)}")
		return redirect(url_for('dashboard', uid=request.cookies.get('uid')))

	print(f"Forum {fid} left")
	flash("Forum left successfully")
	return redirect(url_for('dashboard', uid=request.cookies.get('uid')))
if __name__ == "__main__":
    import click

    @click.command()
    @click.option('--debug', is_flag=True)
    @click.option('--threaded', is_flag=True)
    @click.argument('HOST', default='0.0.0.0')
    @click.argument('PORT', default=8111, type=int)
    def run(debug, threaded, host, port):

        HOST, PORT = host, port
        print("running on %s:%d" % (HOST, PORT))
        app.run(host=HOST, port=PORT, debug=debug, threaded=threaded)

    run()
