from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import enum, os

#creating the Flask App
app = Flask(__name__)

#naming the db and turning off notifs for the changes made in app to db models 
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///placement.db' 
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

#making secret key
app.secret_key = "my_secret_is_i_love_my_dog_more_than_anyone_else"

#connecting flask app to database 
db = SQLAlchemy(app)

#defining enum classes
class CompanyApprovalStatus(enum.Enum):
    PENDING = "Pending"
    APPROVED = "Approved"
    REJECTED = "Rejected"

class DriveStatus(enum.Enum):
    PENDING = "Pending"
    OPEN = "Open"
    CLOSED = "Closed"
    CANCELLED = "Cancelled"

class ApplicationStatus(enum.Enum):
    APPLIED = "Applied"
    SHORTLISTED = "Shortlisted"
    REJECTED = "Rejected"
    ACCEPTED = "Accepted"

#Admin Model
class Admin(db.Model):
    __tablename__ = "admin"
    
    admin_id = db.Column(db.Integer, primary_key=True, autoincrement=True) 
    admin_username = db.Column(db.String, nullable=False, unique=True)
    admin_password_hash = db.Column(db.String, nullable=False)
    
#Company Model
class Company(db.Model):
    __tablename__ = "company"

    company_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    company_email = db.Column(db.String, unique=True, nullable=False)
    company_password_hash = db.Column(db.String, nullable=False)
    company_name = db.Column(db.String, nullable=False)
    company_industry = db.Column(db.String, nullable=True)
    company_description = db.Column(db.String, nullable=True)
    company_contact = db.Column(db.String, nullable=True)
    company_approval_status = db.Column(db.Enum(CompanyApprovalStatus), nullable=False, default=CompanyApprovalStatus.PENDING)
    company_isactive = db.Column(db.Boolean, default=True)
    company_isblacklisted = db.Column(db.Boolean, default=False)

    placement_drives = db.relationship("PlacementDrive", backref="company", lazy=True)

#Student Model
class Student(db.Model):
    __tablename__ = "student"

    student_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    student_email = db.Column(db.String, unique=True, nullable=False)
    student_password_hash = db.Column(db.String, nullable=False)
    student_name = db.Column(db.String, nullable=False)
    student_phone = db.Column(db.String, nullable=True)
    student_education = db.Column(db.String, nullable=True)
    student_skills = db.Column(db.String, nullable=True)
    student_resume_path = db.Column(db.String, nullable=True)
    student_isactive = db.Column(db.Boolean, default=True)
    student_isblacklisted = db.Column(db.Boolean, default=False)

    applications = db.relationship("Application", backref="student", lazy=True)

#JobPosition Model
class JobPosition(db.Model):
    __tablename__ = "job_position"

    job_position_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    job_title = db.Column(db.String, nullable=False)
    required_skills = db.Column(db.String, nullable=True)
    experience_required = db.Column(db.String, nullable=True)
    salary_min = db.Column(db.Float, nullable=True)
    salary_max = db.Column(db.Float, nullable=True)
    job_description = db.Column(db.String, nullable=True)

    placement_drives = db.relationship("PlacementDrive", backref="job_position", lazy=True)

#PlacementDrive Model
class PlacementDrive(db.Model):
    __tablename__ = "placement_drive"

    placement_drive_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    company_id = db.Column(db.Integer, db.ForeignKey("company.company_id"), nullable=False)
    job_position_id = db.Column(db.Integer, db.ForeignKey("job_position.job_position_id"), nullable=False)
    drive_status = db.Column(db.Enum(DriveStatus), nullable=False, default=DriveStatus.PENDING)
    application_deadline = db.Column(db.DateTime, nullable=True)
    eligibility_criteria = db.Column(db.String, nullable=True)

    applications = db.relationship("Application", backref="placement_drive", lazy=True)

#Application Model
class Application(db.Model):
    __tablename__ = "application"

    application_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    student_id = db.Column(db.Integer, db.ForeignKey("student.student_id"), nullable=False)
    placement_drive_id = db.Column(db.Integer, db.ForeignKey("placement_drive.placement_drive_id"), nullable=False)
    application_status = db.Column(db.Enum(ApplicationStatus), nullable=False, default=ApplicationStatus.APPLIED)
    application_date = db.Column(db.DateTime, nullable=False, default=db.func.now())

    #same student cannot apply to same drive twice. forces unique combination of drive id + st id
    __table_args__ = (db.UniqueConstraint("student_id", "placement_drive_id", name="unique_student_drive"),)

def initialize_db():
    #grant access to app settings+resources without live web request. 
    with app.app_context():
        db.create_all()
        
        admin_exists = Admin.query.first()

        if not admin_exists:
            pre_exist_admin = Admin(admin_username = "admin",
            admin_password_hash = generate_password_hash("admin123"))

            db.session.add(pre_exist_admin)
            db.session.commit()

#------------------------------------------------------

#HOME PAGE 
@app.route('/', methods=['GET'])
def home_page():
    return render_template('index.html')

#REGISTER: COMPANY
@app.route('/register_company', methods = ['GET', 'POST'])
def register_company():
    if request.method == 'POST':
        company_email = request.form.get("email")
        company_password = request.form.get("password")
        company_name = request.form.get("name")
        company_industry = request.form.get("industry")
        company_contact = request.form.get("contact")
        company_description = request.form.get("description")

        #checking if company already exists:
        exists = Company.query.filter_by(company_email=company_email).first()
        
        if not(exists):

            company_password_hash = generate_password_hash(company_password)

            new_company = Company( 
            company_email = company_email,
            company_password_hash = company_password_hash,
            company_name = company_name,
            company_industry = company_industry,
            company_contact = company_contact,
            company_description = company_description)

            db.session.add(new_company)
            db.session.commit()
            return render_template('login.html', message ="Successfully registered. Please wait for admin approval to login.")

        else:
            return render_template('register_company.html', message="Company already registered with this email!")
    else:
        return render_template('register_company.html')

#REGISTER: STUDENT 
@app.route('/register_student', methods = ['GET','POST'])
def register_student():
    UPLOAD_FOLDER = "uploads/resumes" #variable that stores the resume path
    if request.method == 'POST':
        student_email = request.form.get("email")
        student_password = request.form.get("password")
        student_name = request.form.get("name")
        student_phone = request.form.get("phone")
        student_education = request.form.get("education")
        student_skills = request.form.get("skills")
        resume = request.files.get("resume")
        resume_path = None

        exists = Student.query.filter_by(student_email = student_email).first()

        if not(exists):

            student_password_hash = generate_password_hash(student_password)
                        
            #checking if resume and filename are not empty
            if resume and resume.filename!="":
                #secure_filename turns the uploaded thing into a safe filename
                filename = secure_filename(resume.filename)
                #checking if path exists or not
                if not os.path.exists(UPLOAD_FOLDER):
                    #if path doesnt exist, then make it
                    os.makedirs(UPLOAD_FOLDER)

                #merging the folder name + uploaded file's name
                save_path = os.path.join(UPLOAD_FOLDER, filename)
                #this is how i am saving the file in the folder created
                resume.save(save_path)
                #storing only the filename to save it in db
                resume_path = filename

            new_student = Student(
                student_email = student_email,
                student_password_hash = student_password_hash,
                student_name = student_name,
                student_phone = student_phone,
                student_education = student_education,
                student_skills = student_skills,
                student_resume_path = resume_path  
            )

            db.session.add(new_student)
            db.session.commit()
            return render_template('login.html')

        else:
            return render_template('register_student.html', message='Student already exists. Please use a different email.')

    else:
        return render_template('register_student.html')      

#LOGIN: ADMIN, COMPANY, STUDENT
@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        email = request.form.get("email")
        password = request.form.get("password")
        
        admin = Admin.query.filter_by(admin_username = email).first()
        company = Company.query.filter_by(company_email = email).first()
        student = Student.query.filter_by(student_email = email).first()

        if admin:
            if(check_password_hash(admin.admin_password_hash, password)):
                session['admin_id'] = admin.admin_id
                return redirect(url_for('admin_dashboard'))
            else:
                return render_template('login.html', message="Incorrect password.")

        elif company:
            if not (check_password_hash(company.company_password_hash, password)):
                return render_template('login.html', message="Incorrect password.")
            
            #Checking admin approval using .name and .value because 
            #in enum, .name -> identifier, .value -> human readable val
            #not using .value because it is display text and can change
            if company.company_approval_status.name == "PENDING":
                return render_template('login.html',message = "Account is pending admin approval.")

            elif company.company_approval_status.name == "REJECTED":
                return render_template('login.html',message = "Registration was rejected by admin.")

            elif company.company_isblacklisted == True:
                return render_template('login.html',message = "You have been blacklisted.")

            elif company.company_isactive == False:
                return render_template('login.html',message = "Your account has been deactivated.")
            else:
                session['company_id'] = company.company_id
                return redirect(url_for('company_dashboard'))
            
        elif student:
            if not (check_password_hash(student.student_password_hash, password)):
                return render_template('login.html', message="Incorrect password.")

            elif student.student_isblacklisted:
                return render_template('login.html', message="You have been blacklisted.")    

            elif student.student_isactive == False:
                return render_template('login.html', message="Your account has been deactivated.")   
        
            else:
                session['student_id'] = student.student_id
                return redirect(url_for('student_dashboard'))
            
        else:
            return render_template('login.html', message='Incorrect username/User does not exist.')

    else:
        return render_template('login.html')  

#LOGOUT
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))     
#------------------------------------------------------

if __name__ == "__main__":
    initialize_db()
    app.run(debug=True)