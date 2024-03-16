from werkzeug.security import  generate_password_hash,check_password_hash
from flask_socketio import SocketIO
from flask import *
from flask_wtf import FlaskForm
from flask_login import *
from wtforms import StringField, IntegerField, TextAreaField,FileField, SelectField,DateField
from flask_mysqldb import MySQL
import MySQLdb.cursors
from wtforms.validators import DataRequired
import socket


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
#Path where the image is stored
app.config['UPLOAD_FOLDER'] = '/media/lenovo/Windows 10/Nursery-Management-System/Client/Product'
app.config['MYSQL_HOST'] = 'localhost'  # XAMPP MySQL server host
app.config['MYSQL_USER'] = 'root'       # XAMPP MySQL username
app.config['MYSQL_PASSWORD'] = ''       # XAMPP MySQL password
app.config['MYSQL_DB'] = 'plants'  # Name of your database in XAMPP MySQL
app.config['MYSQL_PORT'] = 3306
app.config['MYSQL_UNIX_SOCKET'] = '/opt/lampp/var/mysql/mysql.sock'
common_url=f'http://{get_ip_address()}:2802'
sockets = SocketIO(app)
#login Manger
mysql = MySQL()
mysql.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)


class AddProduct(FlaskForm):
    name = StringField('Name')
    price = IntegerField('Price')
    stock = IntegerField('Stock')
    description = TextAreaField('Description')
    image = FileField('Image', validators=[DataRequired()])

class EditProduct(FlaskForm):
    name = StringField('Name')
    price = IntegerField('Price')
    stock = IntegerField('Stock')
    description = TextAreaField('Description')
    image = FileField('Image')

class EditOrder(FlaskForm):
    status = SelectField('Status', choices=[('Delivered','Delivered'),('Shipment','Shipment'),('Shipped','Shipped')])
    date=DateField('Date')
def get_db():
    db = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    return db

# Initialize the database

# Define a Admin loader function
@login_manager.user_loader
def load_user(user_id):
    # Here, you'll load the user from your database based on the user_id
    # For demonstration purposes, let's assume your User class has a method `get_by_id`
    return Admin.get_by_id(user_id)


# Modify your Admin class to inherit from UserMixin
class Admin(UserMixin):
    def __init__(self, user_id, email):
        self.s_id = user_id
        self.email = email
    @staticmethod
    def get_by_id(user_id):
        db=get_db()
        db.execute("SELECT * FROM Supplier WHERE s_id = %s", (user_id,))
        user_data=db.fetchall()
        if user_data:
            return Admin(user_data[0]['s_id'], user_data[0]['s_email'])
        else:
            return None
    def get_id(self):
        return str(self.s_id)


@app.route('/delete_product/<pid>/<sid>')
def delete_product(pid,sid):
    db=get_db()
    db.execute("DELETE FROM  Product WHERE p_id = %s AND supplier_id= %s;",
               (pid,sid))

    mysql.connection.commit()
    return redirect(url_for('admin',index=sid))

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
    return redirect(url_for('admin',index=current_user.s_id))


@app.route('/edit_order/<order_id>',methods=['GET','POST'])
def edit_order(order_id):
    db=get_db()
    form=EditOrder()
    db.execute('SELECT * FROM Orders WHERE order_id = %s', (order_id,))
    product = [dict(row) for row in db.fetchall()]
    print(form.validate_on_submit())
    if form.validate_on_submit():
        db.execute("UPDATE Orders SET status = %s, delivery_date = %s WHERE order_id = %s;",
                   (form.status.data, form.date.data, order_id))
        mysql.connection.commit()
        return redirect(url_for('admin',index=current_user.s_id))
    return render_template('edit_order.html', product=product[0],form=form,user=current_user)


@app.route('/orders/<s_id>',methods=['GET','POST'])
def orders(s_id):
    db=get_db()
    db.execute("SELECT * FROM Orders o JOIN Product p WHERE p.supplier_id = %s ;",
               (s_id,))
    orders = [dict(row) for row in db.fetchall()]
    return render_template('orders.html',user=current_user,orders=orders)
# Define route for admin
@app.route('/admin/<index>')
@app.route('/')
@login_required
def admin(index):
    db = get_db()
    db.execute('SELECT * FROM Product WHERE supplier_id=%s',(index,))
    products = [dict(row) for row in db.fetchall()]
    db.execute("SELECT * FROM Product WHERE stock_available > 0;")
    products_in_stock = ([dict(row) for row in db.fetchall()])
    db.execute("SELECT * FROM Orders o JOIN Product p WHERE p.supplier_id = %s ;",
                               (index,))
    orders = [dict(row) for row in db.fetchall()]
    user=[]
    for order in orders:
        query=f"SELECT * FROM Users WHERE user_id = {order['user_id']};"
        db.execute(query)
        user_email=db.fetchall()
        user.append(user_email[0]['user_email'])
    order_information = []
    for order in orders:
        order_information.append({**order, 'user_email':user[orders.index(order)]})
    return render_template('index.html', admin=True, products=products, products_in_stock=len(products_in_stock), orders=order_information,admin_log=current_user,home=url_for('admin',index=index))


@app.route('/add', methods=['GET', 'POST'])
@login_required
def add():
    import os
    form = AddProduct()
    db=get_db()
    if form.validate_on_submit():
        user_id = None
        if isinstance(current_user, Admin):
            user_id = current_user.s_id
        image = form.image.data
        filename = image.filename
        image.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

        db.execute("INSERT INTO Product(p_name,price,stock_available,Description,supplier_id,image_url) VALUES(%s,%s,%s,%s,%s,%s);",(form.name.data, form.price.data, form.stock.data, form.description.data,user_id,filename))

        mysql.connection.commit()

        return redirect(url_for('admin',index=current_user.s_id))

    return render_template('add-product.html', admin=True, form=form,admin_log=current_user,home=url_for('admin',index=current_user.s_id))

# Route to edit an existing product
@app.route('/edit_product/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_product(id):
    conn = get_db()
    conn.execute('SELECT * FROM Product WHERE p_id = %s', (id,))
    product = [dict(row) for row in conn.fetchall()]
    form = EditProduct(obj=product[0])

    if  form.validate_on_submit():
        name = form.name.data
        price = form.price.data
        stock = form.stock.data
        description = form.description.data
        if name:
            conn.execute('UPDATE Product SET p_name = %s WHERE p_id = %s', (name, id))
        if price:
            conn.execute('UPDATE Product SET price = %s WHERE p_id = %s', (price, id))
        if stock:
            conn.execute('UPDATE Product SET stock_available = %s WHERE p_id = %s', (stock, id))
        if description:
            conn.execute('UPDATE Product SET description = %s WHERE p_id = %s', (description, id))

        mysql.connection.commit()
        return redirect(url_for('admin',index=current_user.s_id))

    return render_template('edit_product.html', form=form, product=product[0],user=current_user,home=url_for('admin',index=current_user.s_id))

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
        for key in ['order_id', 'status', 'reference','payment_type']:
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
    return render_template('view-order.html',product=products, order=orders_info[0], admin=True,order_total=order_totals,quantity_total=quantity_total,admin_log=current_user,home=current_user.s_id)



@app.route('/admin_login',methods=['GET','POST'])
def admin_login():
    db=get_db()
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        # Retrieve user information from the database
        db.execute("SELECT  * FROM Supplier WHERE s_email = %s", (email,))
        user = [dict(row) for row in db.fetchall()]
        if user and check_password_hash(user[0]['password_hash'],password):
            flash('Logged in successfully!', category='success')
            admin_login_c=Admin(user[0]['s_id'], user[0]['s_email'])
            login_user(admin_login_c, remember=True,force=True)
            return redirect(url_for('admin',index=user[0]['s_id']))
        else:
            # Invalid credentials
            flash('Invalid email or password. Please try again.', 'error')  # Error message

    return render_template('login.html',user=current_user,common_url=common_url)

@app.route('/admin_logout')
@login_required
def admin_logout():
    logout_user()
    return redirect(url_for('admin_login'))


@app.route("/admin_signup",methods=['GET','POST'])
def admin_signup():
    db=get_db()
    if request.method=="POST":
        email = request.form.get('email')
        cname = request.form.get('cname')
        password1 = request.form.get('password1')
        password2 = request.form.get('password2')
        address=request.form.get('address')
        contact=request.form.get('contact')
        db.execute("SELECT  * FROM Supplier WHERE s_email = %s", (email,))
        email_exits = [dict(row) for row in db.fetchall()]
        if email_exits:
            flash('Email already exists.', category='error')
        elif len(email) < 4:
            flash('Email must be greater than 3 characters.', category='error')
        elif len(cname) < 2:
            flash('Company Name must be greater than 1 character.', category='error')
        elif password1 != password2:
            flash('Passwords don\'t match.', category='error')
        elif len(password1) < 7:
            flash('Password must be at least 7 characters.', category='error')
        else:
            db.execute('INSERT INTO Supplier(company_name,s_email,password_hash,s_contact,s_address) VALUES(%s,%s,%s,%s,%s)',(cname,email,generate_password_hash(password1,method='scrypt'),contact,address))
            mysql.connection.commit()
            db.execute("SELECT  * FROM Supplier WHERE s_email = %s", (email,))
            user = [dict(row) for row in db.fetchall()]
            if user and check_password_hash(user[0]['password_hash'], password1):
                admin_signup=Admin(user[0]['s_id'], user[0]['s_email'])
                login_user(user=admin_signup, remember=True)
                return redirect(url_for('admin',index=user[0]['s_id']))
    return render_template("signup.html",user=current_user,common_url=common_url)

@app.errorhandler(401)
def unauthorized(error):
    return redirect(url_for('admin_login'))

if __name__=="__main__":
    sockets.run(app,host=get_ip_address(),port=2003,debug=True)