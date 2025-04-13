from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify 
from flask_wtf import FlaskForm
from flask_wtf.file import FileRequired, FileAllowed
from wtforms import StringField, PasswordField, SubmitField, DateField, FileField
from wtforms.validators import DataRequired, Email, ValidationError
from werkzeug.utils import secure_filename
import bcrypt
from datetime import datetime
from datetime import date
import os
from flask_mysqldb import MySQL

# Create an instance of the Flask class
app = Flask(__name__)

# MySQL Configuration
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = ''
app.config['MYSQL_DB'] = 'project_ols'
app.secret_key = 'your_secret_key_here'

mysql = MySQL(app)

class RegisterForm(FlaskForm):
    name = StringField("Name",validators=[DataRequired()])
    phone = StringField("Phone No",validators=[DataRequired()])
    email = StringField("Email",validators=[DataRequired(), Email()])
    password = PasswordField("Password",validators=[DataRequired()])
    current_institute = StringField("Current Institute",validators=[DataRequired()])
    address = StringField("Address",validators=[DataRequired()])
    dob = DateField("Date of Birth", format='%Y-%m-%d', validators=[DataRequired()])
    bg = StringField("Blood Group",validators=[DataRequired()])
    profile_picture = FileField("Profile Picture", validators=[FileRequired(), FileAllowed(['jpg', 'jpeg'], 'Images only (.jpg, .jpeg)')])
    submit = SubmitField("Register")
    
class LoginForm(FlaskForm):
    email = StringField("Email", validators=[DataRequired(), Email()])
    password = PasswordField("Password", validators=[DataRequired()])
    submit = SubmitField("Login")

# Home route 
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/s_register', methods=['GET', 'POST'])
def register():
    form = RegisterForm()

    if form.validate_on_submit():
        name = form.name.data
        phone = form.phone.data
        email = form.email.data
        password = form.password.data
        current_institute = form.current_institute.data
        address = form.address.data
        dob = form.dob.data
        bg = form.bg.data
        profile_picture = form.profile_picture.data  

        # Handle the profile picture file upload
        if profile_picture:
            filename = secure_filename(profile_picture.filename)  # Secure the file name
            file_path = os.path.join('static/uploads', filename)  # Define the file path
            file_path = file_path.replace("\\", "/")

            # Save the profile picture
            profile_picture.save(file_path)
        else:
            file_path = None  # If no picture is uploaded, set file_path to None

        # Store the user data in the database
        cursor = mysql.connection.cursor()
        cursor.execute("INSERT INTO students (name, phone_no, email, password, current_institute, address, date_of_birth, blood_group, profile_picture) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)", 
                       (name, phone, email, password, current_institute, address, dob, bg, file_path))
        mysql.connection.commit()
        cursor.close()

        return redirect(url_for('login'))  # Redirect to login after successful registration

    return render_template('s_register.html', form=form)

@app.route('/s_login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        email = form.email.data
        password = form.password.data

        # Fetch student from the database using email
        cursor = mysql.connection.cursor()
        cursor.execute("SELECT * FROM students WHERE email=%s", (email,))
        student = cursor.fetchone()
        cursor.close()

        # Check if student exists and if the password matches directly (without bcrypt)
        if student and password == student[4]:  # student[4] is the password field in the database
            session['student_id'] = student[1]  # Store student_id in session
            session['student_name'] = student[0]
            return redirect(url_for('student_dashboard'))
        else:
            flash("Login failed. Please check your email and password")
            return redirect(url_for('login'))

    return render_template('s_login.html', form=form)

@app.route('/student_dashboard', methods=['GET'])
def student_dashboard():
    
    if 'student_id' in session:
        student_id = session['student_id']
        
        cursor = mysql.connection.cursor()
        
        # Fetch student details
        cursor.execute("SELECT name FROM students WHERE student_id=%s", (student_id,))
        student = cursor.fetchone()
        
        if not student:
            return redirect(url_for('login'))  # Redirect if student not found
        
        student_name = student[0]
        
        # Fetch enrolled courses for the student
        cursor.execute("""
            SELECT c.course_code, c.course_name, c.course_picture
            FROM courses c
            INNER JOIN enrollment_status e ON c.course_code = e.course_code
            WHERE e.student_id = %s
        """, (student_id,))
        
        enrolled_courses = cursor.fetchall()
        
        # Count courses with status 'completed'
        cursor.execute("""
            SELECT COUNT(*)
            FROM enrollment_status
            WHERE student_id = %s AND status = 'completed'
        """, (student_id,))
        completed_courses_count = cursor.fetchone()[0]
        
        cursor.close()
        
        if student:
            student_name = student[0]
            no_courses = len(enrolled_courses) == 0
        
            return render_template('student_dashboard.html', 
                                student_name=student_name, 
                                enrolled_courses=enrolled_courses,
                                no_courses=no_courses,
                                completed_courses_count=completed_courses_count
                            )
    
    return redirect(url_for('login'))

@app.route('/logout')
def logout():
    session.pop('student_name', None)  # Remove the student's name from the session
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True, port=2525) 