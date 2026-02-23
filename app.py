from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from sqlalchemy import or_
from datetime import datetime
from flask import send_from_directory  #using this to serve/display the resume 
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

#ADMIN DASHBOARD
@app.route('/admin_dashboard')
def admin_dashboard():
    if 'admin_id' not in session:
        return redirect(url_for('login'))
    
    total_students = Student.query.count()
    total_companies = Company.query.filter(Company.company_approval_status == CompanyApprovalStatus.APPROVED).count()
    total_drives = PlacementDrive.query.count()
    total_applications = Application.query.count()

    return render_template('admin_dashboard.html', 
    total_students=total_students,
    total_companies=total_companies,
    total_applications=total_applications,
    total_drives=total_drives)

#admin: show list of all companies + search
@app.route('/admin_companies', methods=["GET"])
def admin_companies():
    if 'admin_id' not in session:
        return redirect(url_for('login'))
    
    search_query = request.args.get("p","").strip()
    message = None
    if search_query:

        if search_query.isdigit():
            companies = Company.query.filter(Company.company_id == int(search_query)).all()

        else:
            companies = Company.query.filter(or_(Company.company_name.ilike(f"%{search_query}%"),
            Company.company_industry.ilike(f"%{search_query}%"))).all()  #because ilike is case insensitive and like is not.          

        if not companies:
            message = "Does not exist."

    else:
        companies = Company.query.all()

    return render_template('admin_companies.html', 
    companies=companies, 
    search_query=search_query,
    message=message)  

#ADMIN: VIEW COMPANY DETAILS
@app.route('/admin_company_detail/<int:company_id>')
def admin_company_detail(company_id):
    if 'admin_id' not in session:
        return redirect(url_for('login'))
        
    company = Company.query.get(company_id)
    return render_template('admin_company_detail.html', company=company)

#admin: approve company
@app.route('/admin_approve_company/<int:company_id>', methods=['POST'])
def admin_approve_company(company_id):
    company = Company.query.get_or_404(company_id) #when a company_id doesnt exist in db, get_or_404 returns 404 instead of throwing attribute error.

    company.company_approval_status = CompanyApprovalStatus.APPROVED
    company.company_isactive = True

    db.session.commit()
    
    return redirect(url_for('admin_companies'))

#admin: reject company
@app.route('/admin_reject_company/<int:company_id>', methods=['POST'])
def admin_reject_company(company_id):
    company = Company.query.get_or_404(company_id)

    company.company_approval_status = CompanyApprovalStatus.REJECTED
    company.company_isactive = False

    db.session.commit()

    return redirect(url_for('admin_companies'))

#admin: blacklist/unblacklist company
@app.route('/admin_blacklist_company/<int:company_id>', methods=['POST'])
def admin_blacklist_company(company_id):
    company = Company.query.get_or_404(company_id)

    if company.company_isblacklisted:
        company.company_isblacklisted = False

    else:
        company.company_isblacklisted = True
        company.company_isactive = False

    db.session.commit()

    return redirect(url_for('admin_companies'))

#admin: activate/deactivate company
@app.route('/admin_activate_company/<int:company_id>', methods=['POST'])
def admin_activate_company(company_id):
    company = Company.query.get_or_404(company_id)

    if company.company_isblacklisted or company.company_approval_status != CompanyApprovalStatus.APPROVED:
        return redirect(url_for('admin_companies'))      

    company.company_isactive = not company.company_isactive

    db.session.commit()

    return redirect(url_for('admin_companies'))

#admin: show list of all students + search
@app.route('/admin_students', methods=['GET'])
def admin_students():
        if 'admin_id' not in session:
        return redirect(url_for('login'))
    
    search_query = request.args.get("p","").strip()
    message = None
    if search_query:

        if search_query.isdigit():
            students = Student.query.filter(Student.student_id == int(search_query)).all()

        else:
            students = Student.query.filter(or_(Student.student_name.ilike(f"%{search_query}%"),
            Student.student_phone.ilike(f"%{search_query}%")
            )).all()
            
        if not students:
            message = "Not found."

    else:
        students=Student.query.all()

    return render_template('admin_students.html', 
    students=students,
    message=message,
    search_query=search_query )    
 
#ADMIN: VIEW STUDENT DETAILS
@app.route('/admin_student_detail/<int:student_id>')
def admin_student_detail(student_id):
    if 'admin_id' not in session:
        return redirect(url_for('login'))

    student = Student.query.get_or_404(student_id)
    return render_template("admin_student_detail.html", student=student)

#admin: blacklist student
@app.route('/admin_blacklist_student/<int:student_id>', methods=['POST'])
def admin_blacklist_student(student_id):

    student = Student.query.get_or_404(student_id)

    if student.student_isblacklisted:
        student.student_isblacklisted = False
    
    else:
        student.student_isblacklisted = True
        student.student_isactive = False

    db.session.commit()
    return redirect(url_for("admin_students"))

#admin activate/deactivate student
@app.route('/admin_activate_student/<int:student_id>', methods=['POST'])
def admin_activate_student(student_id):

    student = Student.query.get_or_404(student_id)

    if student.student_isblacklisted:
            return redirect(url_for("admin_students"))
    
    student.student_isactive = not student.student_isactive
    db.session.commit()
    return redirect(url_for("admin_students"))

#ADMIN: DRIVES (VIEW ALL)
@app.route('/admin_drives')
def admin_drives():
    if 'admin_id' not in session:
        return redirect(url_for('login'))
    
    drives = PlacementDrive.query.all()
    return render_template('admin_drives.html', drives=drives)    

#admin: approve drives 
@app.route('/admin_approve_drive/<int:drive_id>', methods=['POST'])
def admin_approve_drive(drive_id):
    if 'admin_id' not in session:
        return redirect(url_for('login'))

    drive = PlacementDrive.query.get_or_404(drive_id)

    if drive.drive_status == DriveStatus.PENDING:
        drive.drive_status = DriveStatus.OPEN
        db.session.commit()
    return redirect(url_for('admin_drives'))

#admin: reject drives
@app.route('/admin_reject_drive/<int:drive_id>', methods=['POST'])
def admin_reject_drive(drive_id):
    if 'admin_id' not in session:
        return redirect(url_for('login'))

    drive = PlacementDrive.query.get_or_404(drive_id)

    if drive.drive_status == DriveStatus.PENDING:
        drive.drive_status = DriveStatus.CANCELLED
        db.session.commit()
    return redirect(url_for('admin_drives')) 

#ADMIN: VIEW DRIVE DETAILS
@app.route('/admin_drive_detail/<int:drive_id>')
def admin_drive_detail(drive_id):
    if 'admin_id' not in session:
        return redirect(url_for('login'))

    drive = PlacementDrive.query.get_or_404(drive_id)
    return render_template('admin_drive_detail.html', drive=drive)

#ADMIN:APPLICATIONS
@app.route('/admin_applications')
def admin_applications():
    if 'admin_id' not in session:
        return redirect(url_for('login'))
    
    status_filter = request.args.get('status')
    query = Application.query

    if status_filter:
        try:
            query = query.filter(Application.application_status == ApplicationStatus[status_filter])
        except KeyError:
            pass
        
    applications = query.all()
    return render_template('admin_applications.html', applications = applications, current_status = status_filter)    

#COMPANY DASHBOARD
@app.route('/company_dashboard')
def company_dashboard():
    company_id = session.get('company_id')
    company = Company.query.get(company_id)

    if not company:
        return redirect(url_for('login'))
        
    drives = PlacementDrive.query.filter_by(company_id=company_id).all()

    return render_template('company_dashboard.html', company=company, drives=drives)

#COMPANY: VIEW LIST OF APPLICATIONS FOR A CREATED DRIVE + SHORTLIST/ACCEPT/REJECT STUDENTS + FILTERBY APPLICATION STATUS
@app.route('/company_applications/<int:drive_id>')
def company_applications(drive_id):
    return render_template('company_applications.html', company=company, drives=drives)

#company: shortlist student 
@app.route('/shortlist_student/<int:application_id>', methods=['POST'])
def shortlist_student(application_id):
        return redirect(url_for('company_applications',drive_id=application.placement_drive_id))

#company: accept student
@app.route('/accept_student/<int:application_id>', methods=['POST'])
def accept_student(application_id):
        return redirect(url_for('company_applications',drive_id=application.placement_drive_id))

#company: reject students
@app.route('/reject_student/<int:application_id>', methods=['POST'])
def reject_student(application_id):
        return redirect(url_for('company_applications',drive_id=application.placement_drive_id))

#COMPANY: VIEW DETAILED STUDENT APPLICATION
@app.route('/application_detail/<int:application_id>')
def application_detail(application_id):
        return render_template('application_detail.html', application=application)

#company: view student resume in detailed student application
@app.route('/view_resume/<path:filename>')
def view_resume(filename):
    return render_template('company_dashboard.html', application=application)

#company: open/close drives
@app.route('/toggle_drive_status/<int:drive_id>', methods=['POST'])
def toggle_drive_status(drive_id):
        return redirect(url_for('company_dashboard'))

#company: cancel drive
@app.route('/cancel_drive/<int:drive_id>', methods=['POST'])
def cancel_drive(drive_id):
        return redirect(url_for('company_dashboard'))

#COMPANY: EDIT DRIVE
@app.route('/edit_drive/<int:drive_id>', methods=['GET','POST'])
def edit_drive(drive_id):
        return redirect(url_for('company_dashboard'))

#COMPANY: CREATRE DRIVE
@app.route('/create_drive', methods=['GET','POST'])
def create_drive():
        return render_template('create_drive.html')

#STUDENT DASHBOARD: show list of approved,applied drives + search (by company, jobpos, skills) 
@app.route('/student_dashboard')
def student_dashboard():
    #STUDENT DASHBOARD: show list of approved,applied drives + search (by company, jobpos, skills) 
@app.route('/student_dashboard')
def student_dashboard():
    if 'student_id' not in session:
        return redirect(url_for('login'))

    student_id = session.get('student_id')
    student = Student.query.get_or_404(student_id)

    search_query = request.args.get('q','').strip()

    #show all applied drives
    applications = Application.query.filter_by(student_id=student_id).all()

    applied_drives_ids = [application.placement_drive_id for application in applications]

    #show all approved drives
    drives_query = PlacementDrive.query.join(Company).join(JobPosition).filter(PlacementDrive.drive_status == DriveStatus.OPEN,
    PlacementDrive.application_deadline >= datetime.now(),
    Company.company_approval_status == CompanyApprovalStatus.APPROVED,
    Company.company_isactive == True,
    Company.company_isblacklisted == False)

    #show only drives searched for 
    if search_query:
        drives_query = drives_query.filter(or_(Company.company_name.ilike(f"%{search_query}%"),
        JobPosition.job_title.ilike(f"%{search_query}%"),
        JobPosition.required_skills.ilike(f"%{search_query}%")
        ))

    #removing already applied drives from approved drives list
    if applied_drives_ids:
        drives_query = drives_query.filter(~PlacementDrive.placement_drive_id.in_(applied_drives_ids))
    
    drives = drives_query.all()

    return render_template('student_dashboard.html', student=student, 
    drives = drives,
    applications = applications, 
    search_query = search_query)

#STUDENT: APPLY TO A DRIVE
@app.route('/student_drive/<int:drive_id>', methods=['GET', 'POST'])
def student_drive(drive_id):
        return redirect(url_for('student_dashboard'))

#STUDENT: EDIT PROFILE
@app.route('/student_profile',methods=['GET','POST'])
def student_profile():
        return redirect(url_for('student_dashboard'))

#STUDENT: VIEW PLACEMENT HISTORY
@app.route('/placement_history')
def placement_history():
        return render_template('placement_history.html', placements = placements)

#LOGOUT
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))     
#------------------------------------------------------

if __name__ == "__main__":
    initialize_db()
    app.run(debug=True)