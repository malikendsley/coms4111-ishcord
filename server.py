
"""
Columbia's COMS W4111.001 Introduction to Databases
Example Webserver
To run locally:
	python3 server.py
Go to http://localhost:8111 in your browser.
A debugger such as "pdb" may be helpful for debugging.
Read about it online.
"""

import os

# accessible as a variable in index.html:
from sqlalchemy import *
from flask import Flask, flash, make_response, request, render_template, g, redirect

tmpl_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')
static_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static')
app = Flask(__name__, template_folder=tmpl_dir, static_folder=static_dir)


import secrets
secret_key = secrets.token_hex(16)
app.config['SECRET_KEY'] = secret_key

DATABASEURI = "postgresql://mse2143:3607@34.75.94.195/proj1part2"

# This line creates a database engine that knows how to connect to the URI above.
engine = create_engine(DATABASEURI)

@app.before_request
def before_request():
	"""
	This function is run at the beginning of every web request
	(every time you enter an address in the web browser).
	We use it to setup a database connection that can be used throughout the request.

	The variable g is globally accessible.
	"""
	try:
		g.conn = engine.connect()
	except:
		print("Problem connecting to database")
		import traceback
		traceback.print_exc()
		g.conn = None

@app.teardown_request
def teardown_request(exception):
	"""
	At the end of the web request, this makes sure to close the database connection.
	If you don't, the database could run out of memory!
	"""
	if exception:
		print("Teardown exception:", exception)
	try:
		g.conn.close()
	except Exception as e:
		print("Conncetion closure exception:", e)

@app.route('/register', methods=['GET', 'POST'])
def register():
	# for GET, show registration form
	if request.method == 'GET':
		print("User visited register page")
		return render_template("register.html")

	# for POST, create new user if username not taken
	elif request.method == 'POST':
		print("User registration request")
		username = request.form['username']
		# check if user exists
		cursor = g.conn.execute("SELECT name FROM users WHERE username = %s", username)
		if cursor.rowcount > 0:
			flash('User already exists')
			cursor.close()
			return redirect('/register')
		# create new user, then go to dashboard
		else:
			cursor.close()
			# TODO: set up command to insert new user into database
			resp = make_response(redirect('/dashboard'))
			resp.set_cookie('username', username)
			return resp



@app.route('/login', methods=['GET', 'POST'])
def login():
	# if GET, show login page
	if request.method == 'GET':
		# if logged in, go to dashboard
		if request.cookies.get('username'):
			return redirect('/dashboard')
		print("User visited login page")
		return render_template('login.html')
	# if POST, check db for user
	else:
		print("User login request")
		username = request.form['username']
		# require username
		if not username:
			flash('Please enter a username')
			return redirect('/login')
		# check if user exists
		cursor = g.conn.execute("SELECT name FROM users WHERE name = %s", username)
		if cursor.rowcount == 0:
			flash('Username does not exist')
			cursor.close()
			return redirect('/login')
		# log in user, go to dashboard
		else:
			print("Logging in as " + username)
			resp = make_response(redirect('/dashboard'))
			resp.set_cookie('username', username)
			return resp


@app.route('/dashboard')
def dashboard():
	print("User visited dashboard")
	# if logged in, show dashboard
	username = request.cookies.get('username')
	if username:
		print(username)
		return render_template('dashboard.html', username=username)
	# if not logged in, go to login page
	else:
		return redirect('/login')

@app.route('/')
def index():
	# if logged in, go to dashboard
	username = request.cookies.get('username')
	if username:
		return redirect('/dashboard')
	# if not logged in, go to login page
	else:
		return redirect('/login')

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
