import sys

from werkzeug.security import  generate_password_hash,check_password_hash
from flask_socketio import SocketIO
from flask import *
from flask_wtf import FlaskForm
from flask_login import *
from wtforms import StringField, IntegerField,  HiddenField, SelectField
from flask_mysqldb import MySQL
from datetime import date
import socket
import os
import MySQLdb.cursors


#if os.name == 'posix':
#    os.system("sudo apt-get install libmysqlclient-dev -s")


def get_ip_address():
    try:
        # Create a socket object
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        # Connect to any IP address and port (here, Google's public DNS server)
        s.connect(('8.8.8.8', 80))

        # Get the local IP address bound to the socket
        ip_address = s.getsockname()[0]

        return ip_address
    except Exception as e:
        print(f"Error: {e}")
        return "127.0.0.1"


app=Flask(__name__)
app.config['DEBUG'] = True
app.config['SECRET_KEY'] = 'mysecret'
app.config['UPLOAD_FOLDER'] = os.path.join(os.getcwd(),'Product')
app.config['MYSQL_HOST'] = 'localhost'  # XAMPP MySQL server host
app.config['MYSQL_USER'] = 'root'       # XAMPP MySQL username
app.config['MYSQL_PASSWORD'] = ''       # XAMPP MySQL password
app.config['MYSQL_DB'] = 'plants'  # Name of your database in XAMPP MySQL
app.config['MYSQL_PORT'] = 3306
if os.name=='posix':
    #If Xampp is installed and using MYSQL from Xampp
    app.config['MYSQL_UNIX_SOCKET'] = '/opt/lampp/var/mysql/mysql.sock'
common_url=f'http://{get_ip_address()}:2003'
sockets = SocketIO(app)
#login Manger
login_manager = LoginManager()
login_manager.init_app(app)
mysql = MySQL()
mysql.init_app(app)

class AddToCart(FlaskForm):
    quantity = IntegerField('Quantity')
    id = HiddenField('ID')

class Checkout(FlaskForm):
    first_name = StringField('First Name')
    last_name = StringField('Last Name')
    phone_number = StringField('Number')
    email = StringField('Email')
    address = StringField('Address')
    city = StringField('City')
    state = SelectField('State', choices=[('CA', 'California'), ('WA', 'Washington'), ('NV', 'Nevada')])
    country = SelectField('Country', choices=[('US', 'United States'), ('UK', 'United Kingdom'), ('FRA', 'France')])
    payment_type = SelectField('Payment Type',
                               choices=[('CK', 'Check'), ('WT', 'Wire Transfer'), ('UPI', 'Online Payment'),
                                        ('COD', 'Cash on Delivery')])

def get_db():
    try:
        db = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(0)
    return db

# Initialize the database



class User(UserMixin):
    def __init__(self, user_id, user_email):
        self.user_id = user_id
        self.user_email = user_email

    @staticmethod
    def get_by_id(user_id):
        db=mysql.connection.cursor(MySQLdb.cursors.DictCursor)

        db.execute("SELECT * FROM Users WHERE user_id = %s", (user_id,))
        user_data =db.fetchall()
        if user_data:
            return User(user_data[0]['user_id'], user_data[0]['user_email'])
        else:
            return None

    def get_id(self):
        return str(self.user_id)

# Define a user loader function
@login_manager.user_loader
def load_user(user_id):
    # Here, you'll load the user from your database based on the user_id
    # For demonstration purposes, let's assume your User class has a method `get_by_id`
    return User.get_by_id(user_id)
# Define route for index page
@app.route('/')
def index():
    db = get_db()
    db.execute('SELECT * FROM Product')
    products =  db.fetchall()
    db.close()
    return render_template('index.html', products=products,user=current_user)


@app.route('/product/image/<index>')
def product_image(index):
    import os
    # Assuming index is the position of the image in the list of product images
    # Retrieve the path to the image based on the index
    image_path = f"{os.path.join(app.config['UPLOAD_FOLDER'], index)}"  # Adjust the path based on your file naming convention
    image='image/png'
    if image_path.endswith(".jpeg"):
        image='image/jpeg'
    return send_file(image_path,mimetype=image)


# Define route for viewing a product
@app.route('/product/<int:id>')
def product(id):
    db = get_db()
    db.execute('SELECT * FROM Product WHERE p_id=%s',(id,))
    product = [{'id': row['p_id'], 'name': row['p_name'], 'price': row['price'], 'stock_available': row['stock_available'],
                 'description': row['description'], 'image': row['image_url']} for row in db.fetchall()]

    db.execute('SELECT s.s_contact, s.company_name, s.s_address FROM Supplier AS s JOIN Product AS p ON s.s_id = p.Supplier_id WHERE p.p_id = %s;',(id,))
    Supplier=db.fetchall()
    db.close()
    form=AddToCart()

    return render_template('view-product.html', product=product[0],form=form,supplier=Supplier[0],user=current_user)

@app.route('/order/<order_id>')
@login_required
def order(order_id):
    db=get_db()
    query=f"SELECT * FROM Orders WHERE order_id = {order_id};"
    db.execute(query)
    orders=[dict(row) for row in db.fetchall()]
    order_totals = []
    for order in orders:
        db.execute(
            "SELECT SUM(oi.quantity * p.price) AS order_total FROM Order_Item oi JOIN Product p ON oi.product_id = p.p_id WHERE oi.order_id = %s;",
            (order['order_id'],))
        order_total = [dict(row) for row in db.fetchall()]
        order_totals.append(order_total)
    order_totals=order_totals[0][0]['order_total']
    user = []
    for order in orders:
        db.execute('SELECT o.first_name, o.last_name,o.user_address,o.user_contact,user_email,o.state,o.city,o.country FROM Orders o ,Users  u WHERE o.user_id=%s AND u.user_id = o.user_id', (order['user_id'],))
        user.append([dict(row) for row in db.fetchall()])
    orders_info = []

    for order_dict, user_list in zip(orders, user):
        order_info = {}
        for key in ['order_id', 'status', 'reference','payment_type','order_date','delivery_date']:
            order_info[key] = order_dict[key]

        for key in ['first_name', 'last_name','user_address','user_contact','user_email','city','user_email','city','country','state']:
            order_info[key] = user_list[0][key]
        orders_info.append(order_info)
        # Fetch total quantity of items in the order
        db.execute("SELECT SUM(oi.quantity) FROM Order_Item oi WHERE oi.order_id = %s;", (order_id,))
        quantity_totals = db.fetchone()
        quantity_total =float( quantity_totals['SUM(oi.quantity)'] if quantity_totals['SUM(oi.quantity)'] is not None else 0)
    db.execute('SELECT p.p_id,p.p_name,p.price,oi.quantity,p.price FROM Product as p,Order_Item as oi WHERE p.p_id=oi.product_id AND oi.order_id=%s ;',(order_id,))
    products=[dict(row) for row in db.fetchall()]
    return render_template('view-order.html',product=products, order=orders_info[0], admin=False,user=current_user,order_total=order_totals,quantity_total=quantity_total,home=current_user.user_id)

@app.route('/delete_order/<order_id>')
def delete_order(order_id):
    db=get_db()
    db.execute('SELECT product_id,quantity FROM Order_Item WHERE order_id = %s;',(order_id,))
    products=[dict(row) for row in db.fetchall()]
    for product in products:
        db.execute('UPDATE Product SET stock_available = stock_available+%s WHERE p_id = %s;',(product['quantity'],product['product_id'],))
    db.execute("DELETE FROM  Orders WHERE order_id= %s;",
               (order_id,))
    mysql.connection.commit()
    return redirect(url_for('admin'))

@app.route('/orders/<s_id>',methods=['GET','POST'])
def orders(s_id):
    db=get_db()
    db.execute("SELECT * FROM Orders o JOIN Product p WHERE user_id = %s ;",
               (s_id,))
    orders = [dict(row) for row in db.fetchall()]
    return render_template('orders.html',user=current_user,orders=orders)

@app.route('/quick-add/<id>')
def quick_add(id):
    if 'cart' not in session:
        session['cart'] = []

    session['cart'].append({'id' : id, 'quantity' : 1})
    session.modified = True

    return redirect(url_for('index'))

# Define route for adding a product to cart
@app.route('/add-to-cart/<int:id>', methods=['POST'])
def add_to_cart(id):
    if 'cart' not in session:
        session['cart'] = []
    db=get_db()
    db.execute('SELECT * FROM Product WHERE p_id = %s', (id,))
    product = db.fetchone()
    if product['stock_available'] < int(request.form['quantity']):
        flash('Insufficient stock available',category='error')
        return redirect(url_for('product', id=id))
    session['cart'].append({'id' : id,"name":product['p_name'], 'quantity' : request.form['quantity']})
    session.modified = True

    return redirect(url_for('index'))

# Define route for viewing cart
@app.route('/cart')
def cart():
    cart_items = []
    total_price = 0
    quantity_total=0
    if 'cart' in session:
        db = get_db()
        for item in session['cart']:
            db.execute('SELECT * FROM Product WHERE p_id = %s', (item['id'],))
            product = db.fetchone()
            if product:
                cart_item = {
                    'product': product,
                    'id':product['p_id'],
                    'name': product['p_name'],
                    'quantity': item['quantity'],
                    'image': product['image_url'],
                    'total_price': float(product['price']) * float(item['quantity'])

                }
                total_price += cart_item['total_price']
                quantity_total+=float(item['quantity'])
                cart_items.append(cart_item)
        db.close()

    grand_total_plus_shipping = total_price + 10
    return render_template('cart.html', products=cart_items, grand_total=total_price, quantity_total=quantity_total,grand_total_plus_shipping=grand_total_plus_shipping,user=current_user)

@app.route('/remove-from-cart/<int:id>')
def remove_from_cart(id):
    del session['cart'][int(id)]
    session.modified = True
    return redirect(url_for('cart'))

def handle_cart():
    cart_items = []
    total_price = 0
    quantity_total = 0
    grand_total = 0
    db = get_db()
    for item in session['cart']:
        db.execute('SELECT * FROM Product WHERE p_id = %s', (item['id'],))
        product = db.fetchall()
        if product:
            cart_item = {
                'product': product,
                'id': product[0]['p_id'],
                'name':product[0]['p_name'],
                'quantity': item['quantity'],
                'total_price': float(product[0]['price']) * float(item['quantity'])

            }
            total = float(product[0]['price']) * float(item['quantity'])
            grand_total += total
            total_price += cart_item['total_price']
            quantity_total += float(item['quantity'])
            cart_items.append(cart_item)
    db.close()
    grand_total_plus_shipping = total_price + 10

    return cart_items, grand_total, grand_total_plus_shipping, quantity_total

@app.route('/search')
def search():
    query = request.args.get('query')
    db = get_db()
    db.execute('SELECT * FROM Product WHERE p_name LIKE %s', ('%' + query + '%',))
    products = db.fetchall()
    available=True
    if products:
        available=False
    return render_template('search.html', products=products, query=query,user=current_user,avaiable=available)

# Define route for checkout
@app.route('/checkout', methods=['GET', 'POST'])
@login_required
def checkout():
    import random
    form = Checkout()

    products, grand_total, grand_total_plus_shipping, quantity_total = handle_cart()
    if form.validate_on_submit():
        db = get_db()

        user_id = current_user.user_id

        # Insert order into Orders table
        reference = ''.join([random.choice('ABCDE') for _ in range(5)])
        db.execute(
            "INSERT INTO Orders (reference, user_id, order_date, status, total_amt, payment_type, First_Name, last_Name, country, state, city, user_contact, user_address) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);",
            (reference, user_id, date.today(), 'PENDING', grand_total_plus_shipping, form.payment_type.data,
             form.first_name.data, form.last_name.data, form.country.data, form.state.data, form.city.data,
             form.phone_number.data, form.address.data))
        mysql.connection.commit() 

        # Get the order_id of the newly inserted order
        db.execute("SELECT LAST_INSERT_ID();")
        order_id = db.fetchone()
        # Insert order items into order_item table
        for item in session['cart']:
            db.execute(" SELECT price FROM Product WHERE p_id = %s;",(item['id'],))
            product_id=db.fetchall()
            db.execute("INSERT INTO Order_Item (order_id,product_id,quantity,price) VALUES (%s, %s, %s, %s);",
                       (order_id['LAST_INSERT_ID()'], item['id'], item['quantity'],product_id[0]['price']))
            db.execute('UPDATE Product SET stock_available = stock_available - %s WHERE p_id = %s;', (item['quantity'], item['id']))
        mysql.connection.commit()

        session['cart'] = []
        session.modified = True
        flash('Ordered  successfully! reference: '+reference, category='success')
        return redirect(url_for('order', order_id=order_id['LAST_INSERT_ID()']))

    return render_template('checkout.html', user=current_user, form=form, grand_total=grand_total,
                           grand_total_plus_shipping=grand_total_plus_shipping, quantity_total=quantity_total)
@app.route('/user_logout')
@login_required
def luser_ogout():
    logout_user()
    return redirect(url_for('user_login'))

@app.route('/user_login',methods=['GET','POST'])
def user_login():
    db = get_db()
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        # Retrieve user information from the database
        db.execute("SELECT  * FROM Users WHERE user_email = %s", (email,))
        user = db.fetchall()
        if user and check_password_hash(user[0]['password_hash'], password):
            flash('Logged in successfully!', category='success')
            login_user(User(user[0]['user_id'], user[0]['user_email']), remember=True)
            return redirect(url_for('index'))
        else:
            # Invalid credentials
            flash('Invalid email or password. Please try again.', 'error')  # Error message

    return render_template('login.html',user=current_user,common_url=common_url)

@app.errorhandler(401)
def unauthorized(error):
    flash('Please login first.', category='error')
    return redirect(url_for('index'))

@app.route("/users_signup",methods=['GET','POST'])
def users_signup():
    db=get_db()
    if request.method=="POST":
        email = request.form.get('email')
        password1 = request.form.get('password1')
        password2 = request.form.get('password2')
        db.execute("SELECT  * FROM Users WHERE user_email = %s", (email,))
        email_exits =  db.fetchall()
        if email_exits:
            flash('Email already exists.', category='error')
            print("Email already exists.")
        elif len(email) < 4:
            flash('Email must be greater than 3 characters.', category='error')
        elif password1 != password2:
            flash('Passwords don\'t match.', category='error')
        elif len(password1) < 7:
            flash('Password must be at least 7 characters.', category='error')
        else:
            db.execute('INSERT INTO Users(user_email,password_hash) VALUES(%s,%s)',
                       (email,generate_password_hash(password1,method='scrypt')))
            mysql.connection.commit()
            db.execute("SELECT  * FROM Users WHERE user_email = %s", (email,))
            user = [dict(row) for row in db.fetchall()]
            if user and check_password_hash(user[0]['password_hash'], password1):
                login_user(User(user[0]['user_id'], user[0]['user_email']), remember=True)
                return redirect(url_for('index'))
    return render_template("signup.html",user=current_user,common_url=common_url)


if __name__=="__main__":
    sockets.run(app,host=get_ip_address(),port=2802,debug=True)
