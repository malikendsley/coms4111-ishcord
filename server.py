
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
import secrets
# accessible as a variable in index.html:
from sqlalchemy import *
from flask import Flask, flash, make_response, request, render_template, g, redirect

tmpl_dir = os.path.join(os.path.dirname(
	os.path.abspath(__file__)), 'templates')
app = Flask(__name__, template_folder=tmpl_dir, static_folder='static')
secret_key = secrets.token_hex(16)
app.config['SECRET_KEY'] = secret_key

DATABASEURI = "postgresql://mse2143:3607@34.75.94.195/proj1part2"

# This line creates a database engine that knows how to connect to the URI above.

engine = create_engine(DATABASEURI)

#
# Example of running queries in your database
# Note that this will probably not work if you already have a table named 'test' in your database, containing meaningful data. This is only an example showing you how to run queries in your database using SQLAlchemy.
#
engine.execute("""CREATE TABLE IF NOT EXISTS test (
  id serial,
  name text
);""")
engine.execute(
	"""INSERT INTO test(name) VALUES ('grace hopper'), ('alan turing'), ('ada lovelace');""")


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
		print("uh oh, problem connecting to database")
		import traceback
		traceback.print_exc()
		g.conn = None


@app.teardown_request
def teardown_request(exception):
	"""
	At the end of the web request, this makes sure to close the database connection.
	If you don't, the database could run out of memory!
	"""
	try:
		g.conn.close()
	except Exception as e:
		pass


# @app.route('/')
# def somethingelse():
#   """
#   request is a special object that Flask provides to access web request information:
#   request.method:   "GET" or "POST"
#   request.form:     if the browser submitted a form, this contains the data in the form
#   request.args:     dictionary of URL arguments, e.g., {a:1, b:2} for http://localhost?a=1&b=2
#   See is API: https://flask.palletsprojects.com/en/2.0.x/api/?highlight=incoming%20request%20data
#   """
#   # DEBUG: this is debugging code to see what request looks like
#   print(request.args)
#   # example of a database query
#   #
#   cursor = g.conn.execute("SELECT name FROM test")
#   names = []
#   for result in cursor:
#     names.append(result['name'])  # can also be accessed using result[0]
#   cursor.close()
#   #
#   # Flask uses Jinja templates, which is an extension to HTML where you can
#   # pass data to a template and dynamically generate HTML based on the data
#   # (you can think of it as simple PHP)
#   # documentation: https://realpython.com/primer-on-jinja-templating/
#   #
#   # You can see an example template in templates/index.html
#   #
#   # context are the variables that are passed to the template.
#   # for example, "data" key in the context variable defined below will be
#   # accessible as a variable in index.html:
#   #
#   #     # will print: [u'grace hopper', u'alan turing', u'ada lovelace']
#   #     <div>{{data}}</div>
#   #
#   #     # creates a <div> tag for each element in data
#   #     # will print:
#   #     #
#   #     #   <div>grace hopper</div>
#   #     #   <div>alan turing</div>
#   #     #   <div>ada lovelace</div>
#   #     #
#   #     {% for n in data %}
#   #     <div>{{n}}</div>
#   #     {% endfor %}
#   #
#   context = dict(data = names)
#   #
#   # render_template looks in the templates/ folder for files.
#   # for example, the below file reads template/index.html
#   #
#   return render_template("index.html", **context)


@app.route('/add', methods=['POST'])
def add():
	name = request.form['name']
	g.conn.execute('INSERT INTO test(name) VALUES (%s)', name)
	return redirect('/')


@app.route('/register', methods=['GET', 'POST'])
def register():
	# for POST, try to create a new user and redirect to the dashboard
	if request.method == 'POST':
		username = request.form['username']
		# check if user exists
		cursor = g.conn.execute(
			"SELECT name FROM users WHERE username = %s", username)
		if cursor.rowcount > 0:
			flash('User already exists')
			cursor.close()
			return redirect('/register')
		else:
			cursor.close()
			# TODO: set up command to insert new user into database
			# set uid cookie and redirect to dashboard
			resp = make_response(redirect('/dashboard'))
			resp.set_cookie('username', username)
			return resp
	# for GET, show the registration form
	elif request.method == 'GET':
		return render_template("register.html")
	# reject any other request method
	else:
		return "Invalid request method"


@app.route('/login', methods=['GET', 'POST'])
def login():
	print("User visited login page")
	# if GET request, render login page
	if request.method == 'GET':
		return render_template('login.html')
	# if POST request, check if user exists in SQL database, don't use a password for now
	else:
		username = request.form['username']
		if not username:
			flash('Please enter a username')
			return redirect('/login')
		# check if username exists in database
		cursor = g.conn.execute(
			"SELECT name FROM users WHERE name = %s", username)
		if cursor.rowcount == 0:
			flash('Username does not exist')
			cursor.close()
			return redirect('/login')
		else:
			print("Logging in as " + username)
			# store username in session
			resp = make_response(redirect('/dashboard'))
			resp.set_cookie('username', username)
			return resp


@app.route('/dashboard')
def index():
	print("User visited index page")
	print(request.args)
	# check cookies to see if user is logged in
	username = request.cookies.get('username')
	if username:
		print(username)
		return render_template('dashboard.html', username=username)
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
