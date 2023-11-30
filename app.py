from flask import Flask, redirect, url_for, render_template, request, send_from_directory, session ,flash , Response
from flask_sqlalchemy import SQLAlchemy 
import json
from werkzeug.utils import secure_filename
import os
from datetime import datetime
from flask_bcrypt import Bcrypt
from slugify import slugify
# from sqlalchemy import text

with open('config.json', 'r') as c:
    data = json.load(c)["data"]

local_server=True    

app = Flask(__name__)
app.secret_key = 'secret-key'
app.config['UPLOAD_FOLDER'] = data['upload_location']

bcrypt=Bcrypt(app)


if(local_server):
    app.config["SQLALCHEMY_DATABASE_URI"] = data['local_uri']
else:
    app.config["SQLALCHEMY_DATABASE_URI"] = data['prod_uri']
       
db = SQLAlchemy()
db.init_app(app)


# Function that initializes the db and creates the tables
def db_init(app):
    db.init_app(app)

    # Creates the logs tables if the db doesnt already exist
    with app.app_context():
        db.create_all()


#MODELS
class Details(db.Model):
    sno = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=False, nullable=False)
    address = db.Column(db.String(100), nullable=False)
    contact = db.Column(db.String(14), nullable=False)
    password = db.Column(db.String(20), nullable=False)
    confirm = db.Column(db.String(20), nullable=False)
    email = db.Column(db.String(40), nullable=False)
    services = db.Column(db.String, nullable=False)
    date = db.Column(db.String(10), nullable=True)
    slug = db.Column(db.String(80), nullable=True)
    file = db.Column(db.Text, nullable=True)


    @staticmethod
    def slugify(target, value, oldvalue, initiator):
        if value and (not target.slug or value != oldvalue):
            target.slug = slugify(value)

db.event.listen(Details.name, 'set', Details.slugify, retval=False)
        
class Accept(db.Model):
    sno = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=False, nullable=False)
    address = db.Column(db.String(100), nullable=False)
    contact = db.Column(db.String(14), nullable=False)
    password = db.Column(db.String(20), nullable=False)
    confirm = db.Column(db.String(20), nullable=False)
    email = db.Column(db.String(40), nullable=False)
    services = db.Column(db.String, nullable=False)
    date = db.Column(db.String(10), nullable=True)
    slug = db.Column(db.String(80), nullable=True)
    file = db.Column(db.Text , nullable=True)


class Places(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=False, nullable=False)
    description = db.Column(db.String, nullable=False)
    img1 = db.Column(db.Text , nullable=True)
    img2 = db.Column(db.Text , nullable=True)
    img3 = db.Column(db.Text , nullable=True)
    img4 = db.Column(db.Text , nullable=True)
    img5 = db.Column(db.Text , nullable=True)
    map =  db.Column(db.String , nullable=True)



#ROUTES
@app.route('/')
def index():
    return render_template("index.html")

@app.route('/home')
def home():
    return render_template("index.html")


@app.route('/view')
def view():
    return render_template('view.html')

def authenticate_user(contact, password):
    list = Accept.query.filter_by(contact=contact).first()
    if list and list.password == password:
        return True, list.sno
    else:
        return False, None

@app.route('/signin', methods=['GET', 'POST'])
def signin():
    if request.method == 'POST':
        user_contact = request.form.get('contact')
        user_password = request.form.get('password')

        result, sno = authenticate_user(user_contact, user_password)

        if result:
            return redirect(url_for('user_dash', sno=sno))  
        else:
            flash('Invalid credentials. Please try again.')
            return redirect(url_for('signin'))  

    list = Accept.query.all()
    return render_template('signin.html', list=list)

@app.route('/user_dash/<int:sno>', methods=['GET', 'POST'])
def user_dash(sno):
    list = Accept.query.filter_by(sno=sno).all()
    return render_template('user_dash.html', list = list)


@app.route('/register', methods = ['GET', 'POST'])
def register():
    if(request.method == 'POST'):
        name = request.form.get('name')
        address = request.form.get('address')
        contact = request.form.get('contact')
        password = request.form.get('password')
        confirm = request.form.get('confirm')
        if confirm != password:
            flash("passwords doesn't match")
            redirect(url_for('register'))
        email = request.form.get('email')
        services = request.form.get('services')

        pic = request.files['file1']
        if not pic:
            return 'No image uploaded!', 400

        filename = secure_filename(pic.filename)
     
        entry = Details(name=name, address=address, contact=contact , password=password, confirm=confirm, email=email, services=services ,date=datetime.now() , file=filename)
        
        db.session.add(entry)
        db.session.commit()
        
        if (request.method == 'POST'):    
            pic.save(os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(pic.filename)))
    
        return render_template('confirm.html')
                
    return render_template('register.html')


@app.route("/admin",  methods = ['GET', 'POST'])
def admin():
    error = None
    
    if "user" in session and session['user']==data['admin_username']:
        return render_template('admin_dash.html', data=data )
    
    if request.method=="POST":
        username = request.form.get("username")       
        userpass = request.form.get("password")
        if ( username == data['admin_username'] and userpass == data['admin_password'] ):
            session['user'] = username
            return render_template('admin_dash.html', data=data )
        else:
            error=data['error']
    return render_template('admin.html', data=data , error=error)


@app.route('/logout')
def logout():
    session.pop('user')
    return redirect('/admin')


@app.route('/admin_view/<int:sno>/<string:slug>' , methods = ["GET" , "POST"])
def admin_view(sno ,slug):
    list = Details.query.filter_by(sno = sno ,slug=slug ).first()                
    return render_template('admin_view.html' , list=list )


@app.route('/admin_dash')
def admin_dash():
    return render_template('admin_dash.html')

@app.route('/admin_accept', methods=['POST'])
def admin_accept():
    # Get the row id from the request
    row_id = request.form.get('row_id')

    # Query the row to be moved from Table1
    row = Details.query.get(row_id)

    if row:
        # Create a new row in Table2 with the same data
        new_row = Accept(name=row.name, address=row.address, contact=row.contact , password=row.password, confirm=row.confirm, email=row.email, services=row.services ,date=datetime.now(), slug=row.slug , file = row.file )  # Modify this based on your table columns
        # Add the new row to Table2
        db.session.add(new_row)
        # Delete the row from Table1
        db.session.delete(row)
        # Commit the changes to the database
        db.session.commit()
        return render_template('admin_accept.html')
    else:
        return 'Row not found'

@app.route('/admin_reject', methods=['POST'])    
def admin_reject():
    row_id2 = request.form.get('row_id2')
    row2 = Details.query.get(row_id2)
    if row2:
        db.session.delete(row2)
        db.session.commit()     
    return render_template('admin_reject.html')


@app.route('/requests', methods=["GET" ,"POST"])
def requests():
    list = Details.query.filter_by().all()
    return render_template('requests.html', list=list)


@app.route('/approved_app', methods=["GET" ,"POST"])
def approved_app():
    list = Accept.query.filter_by().all()
    return render_template('approved_app.html', list=list)


@app.route('/approved_view/<int:sno>/<string:slug>' , methods = ["GET" , "POST"])
def approved_view(sno ,slug):
    list = Accept.query.filter_by(sno = sno ,slug=slug ).first()                
    return render_template('approved_view.html' , list=list )

@app.route('/edit_pages' , methods=["GET" ,"POST"])
def edit_pages():
    if(request.method == 'POST'):
        name = request.form.get('name')
        description = request.form.get('desc')
        map = request.form.get('map')

        if 'files[]' not in request.files:
            flash('No file selected')
            return redirect(request.url)
        files = request.files.getlist('files[]')
        num = len(files)
        file_names = []
        for file in files:
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                file_names.append(filename)
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

        if(num == 1):
            entry = Places(name=name, description = description ,  map = map , img1 = file_names[0] )
        elif(num == 2):
            entry = Places(name=name, description = description ,  map = map , img1 = file_names[0] ,img2 = file_names[1] )
        elif(num == 3):
            entry = Places(name=name, description = description ,  map = map ,img1 = file_names[0] ,img2 = file_names[1], img3 = file_names[2] )
        elif(num == 4):
            entry = Places(name=name, description = description ,  map = map ,img1 = file_names[0] ,img2 = file_names[1], img3 = file_names[2], img4 = file_names[3] )
        elif(num == 5):
            entry = Places(name=name, description = description ,  map = map ,img1 = file_names[0] ,img2 = file_names[1], img3 = file_names[2], img4 = file_names[3] ,img5 = file_names[4])
        # elif(num > 5):
        #       

        if(num<=5):
            db.session.add(entry)
        else:
            flash('only a maximum of 5 should be uploaded!')
        db.session.commit()
            
    return render_template('edit_pages.html' )

@app.route('/confirm')
def confirm():
    return render_template('confirm.html')

ALLOWED_EXTENSIONS = set(['png', 'jpg', 'jpeg', 'gif'])

def allowed_file(filename):
	return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# def upload_image():
# 	if 'files[]' not in request.files:
# 		flash('No file part')
# 		return redirect(request.url)
# 	files = request.files.getlist('files[]')
# 	file_names = []
# 	for file in files:
# 		if file and allowed_file(file.filename):
# 			filename = secure_filename(file.filename)
# 			file_names.append(filename)
# 			file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

# 	return render_template('upload.html', filenames=file_names)


@app.route('/tour')
def tour():
    list = Places.query.filter_by().all()
    num = 3
    return render_template('tour.html' , list = list , num = num)

@app.route('/place')
def place():
    return render_template('place.html')


@app.route('/dormitories')
def dormitories():
    return render_template('dormitories.html')


@app.route('/home_stay')
def home_stay():
    return render_template('home_stay.html')


@app.route('/local_workforce')
def local_workforce():
    list = Accept.query.filter_by().all()
    return render_template('local_workforce.html' , list = list)

@app.route('/view_localworkforce/<int:sno>', methods=['GET', 'POST'])
def view_localworkforce(sno):
    list = Accept.query.filter_by(sno = sno )  
    return render_template('view_localworkforce.html' , list = list)


@app.route('/plantation_crops')
def plantation_crops():
    return render_template('plantation _crops.html')

@app.route('/spices')
def spices():
    return render_template('spices.html')

@app.route('/spices_view')
def spices_view():
    return render_template('spices_view.html')


@app.route('/resorts')
def resorts():
    return render_template('resorts.html')


@app.route('/tent_camping')
def tent_camping():
    return render_template('tent_camping.html')


@app.route('/transport')
def transport():
    list = Accept.query.filter_by().all()
    return render_template('transport.html', list = list)

@app.route('/transport_view/<string:services>', methods=["GET" ,"POST"])
def transport_view(services):
    list = Accept.query.filter_by(services = services )
    return render_template('transport_view.html', list=list)

# @app.route('/taxiservices')
# def taxiservices():
#     list = Accept.query.filter_by().all()
#     for item in list:
#         if item.services=='Taxi Services':
#             x=x.append(item)    
#     return render_template('transport_view.html', list = x)


# @app.route('/taxiservices/<string:services>', methods=["GET" ,"POST"])
# def taxiservices(services):
#     list = Accept.query.filter_by(services=services)   
#     return render_template('transport_view.html', list = list)


# @app.route('/CarRental')
# def CarRental():
#     list = Accept.query.filter_by(services='Car Rental')
#     return render_template('transport_view.html', list = list)



@app.route('/where_to_stay')
def where_to_stay():
    return render_template('where_to_stay.html')

@app.route('/<text>', methods=['GET', 'POST'])
def all_routes(text):
    return redirect(url_for('index'))


if __name__ == ("__main__"):
    app.run(debug=True)
