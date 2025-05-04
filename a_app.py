from flask import Flask, render_template, request, redirect, url_for, session, flash 
from flask_wtf import FlaskForm
from flask_wtf.file import FileRequired, FileAllowed
from wtforms import StringField, PasswordField, SubmitField, DateField, FileField
from wtforms.validators import DataRequired, Email, ValidationError
from werkzeug.utils import secure_filename
import bcrypt
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
    address = StringField("Address",validators=[DataRequired()])
    dob = DateField("Date of Birth", format='%Y-%m-%d', validators=[DataRequired()])
    bg = StringField("Blood Group",validators=[DataRequired()])
    profile_picture = FileField("Profile Picture", validators=[FileRequired(), FileAllowed(['jpg', 'jpeg'], 'Images only (.jpg, .jpeg)')])
    submit = SubmitField("Register")
    
class InstructorRegisterForm(FlaskForm):
    name = StringField("Name",validators=[DataRequired()])
    phone = StringField("Phone No",validators=[DataRequired()])
    email = StringField("Email",validators=[DataRequired(), Email()])
    password = PasswordField("Password",validators=[DataRequired()])
    course_name = StringField("Course Name",validators=[DataRequired()])
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
    return render_template('a_index.html')

@app.route('/a_register', methods=['GET', 'POST'])
def a_register():
    form = RegisterForm()

    if form.validate_on_submit():
        name = form.name.data
        phone = form.phone.data
        email = form.email.data
        password = form.password.data
        address = form.address.data
        dob = form.dob.data
        bg = form.bg.data
        profile_picture = form.profile_picture.data  

        # Handle the profile picture file upload
        if profile_picture:
            filename = secure_filename(profile_picture.filename)  
            file_path = os.path.join('static/uploads', filename) 
            file_path = file_path.replace("\\", "/")

            profile_picture.save(file_path)
            
        else:
            file_path = None  

        # Store the user data in the database
        cursor = mysql.connection.cursor()
        cursor.execute("INSERT INTO admin (name, phone_no, email, password, address, date_of_birth, blood_group, profile_picture) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)", 
                       (name, phone, email, password, address, dob, bg, file_path))
        mysql.connection.commit()
        cursor.close()

        return redirect(url_for('a_login'))  # Redirect to login after successful registration

    return render_template('a_register.html', form=form)

@app.route('/i_register', methods=['GET', 'POST'])
def i_register():
    form = InstructorRegisterForm()

    if form.validate_on_submit():
        name = form.name.data
        phone = form.phone.data
        email = form.email.data
        password = form.password.data
        course_name = form.course_name.data
        address = form.address.data
        dob = form.dob.data
        bg = form.bg.data
        profile_picture = form.profile_picture.data  

        # Handle the profile picture file upload
        if profile_picture:
            filename = secure_filename(profile_picture.filename)  
            file_path = os.path.join('static/uploads', filename) 
            file_path = file_path.replace("\\", "/")

            profile_picture.save(file_path)
            
        else:
            file_path = None  

        # Store the user data in the database
        cursor = mysql.connection.cursor()
        cursor.execute("INSERT INTO instructors (name, phone_no, email, password, course_name, address, date_of_birth, blood_group, profile_picture) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)", 
                       (name, phone, email, password, course_name, address, dob, bg, file_path))
        mysql.connection.commit()
        cursor.close()

        return redirect(url_for('admin_dashboard'))  # Redirect to login after successful registration

    return render_template('i_register.html', form=form)

@app.route('/a_login', methods=['GET', 'POST'])
def a_login():
    form = LoginForm()
    if form.validate_on_submit():
        email = form.email.data
        password = form.password.data

        # Fetch student from the database using email
        cursor = mysql.connection.cursor()
        cursor.execute("SELECT * FROM admin WHERE email=%s", (email,))
        admin = cursor.fetchone()
        cursor.close()

        # Check if student exists and if the password matches directly (without bcrypt)
        if admin and password == admin[4]:  # instructor[4] is the password field in the database
            session['admin_id'] = admin[1]  # Store instructor_id in session
            session['admin_name'] = admin[0]
            return redirect(url_for('admin_dashboard'))
        else:
            flash("Login failed. Please check your email and password")
            return redirect(url_for('a_login'))

    return render_template('a_login.html', form=form)

@app.route('/admin_dashboard')
def admin_dashboard():
    
    if 'admin_id' in session:
        admin_id = session['admin_id']

        cursor = mysql.connection.cursor()
        cursor.execute("SELECT * FROM admin where admin_id=%s", (admin_id,))
        admin = cursor.fetchone()
        cursor.close()

        if admin:
            admin_name = admin[0]
            return render_template('admin_dashboard.html',admin=admin, admin_name=admin_name)
                   
    return redirect(url_for('a_login'))


@app.route('/get_courses', methods=['POST'])
def get_courses():
    data = request.get_json()
    query = data.get('query', None)
    filter_category = data.get('filter', None)

    cursor = mysql.connection.cursor()
    if query and filter_category:
        cursor.execute(
        "SELECT c.course_code, c.course_name, c.course_picture, i.name AS instructor_name "
        "FROM courses c "
        "JOIN instructors i ON c.instructor_id = i.instructor_id "
        "WHERE c.course_name LIKE %s AND c.category = %s",
        (f"%{query}%", filter_category,)
    )
    elif query:
        cursor.execute(
            "SELECT c.course_code, c.course_name, c.course_picture, i.name AS instructor_name "
            "FROM courses c "
            "JOIN instructors i ON c.instructor_id = i.instructor_id "
            "WHERE c.course_name LIKE %s",
            (f"%{query}%",)
        )
    elif filter_category:
        cursor.execute(
            "SELECT c.course_code, c.course_name, c.course_picture, i.name AS instructor_name "
            "FROM courses c "
            "JOIN instructors i ON c.instructor_id = i.instructor_id "
            "WHERE c.category = %s",
            (filter_category,)
        )
    else:
        cursor.execute(
            "SELECT c.course_code, c.course_name, c.course_picture, i.name AS instructor_name "
            "FROM courses c "
            "JOIN instructors i ON c.instructor_id = i.instructor_id"
        )

    courses = cursor.fetchall()
    cursor.close()

    course_list = []
    for course in courses:
        course_list.append({
            'course_code': course[0],
            'course_name': course[1],
            'course_picture': course[2],
            'instructor_name': course[3],
            'description': "In order to extract knowledge and insights from both organized and unstructured data, data science is an interdisciplinary profession."
        })

    return {'data': course_list}

@app.route('/view_course/<int:course_code>')
def view_course(course_code):
    cursor = mysql.connection.cursor()

    # Fetch num_of_module from courses table
    cursor.execute("""
        SELECT num_of_module, num_of_students
        FROM courses
        WHERE course_code = %s
    """, (course_code,))
    course = cursor.fetchone()  # (num_of_module, num_of_students)

    if not course:
        cursor.close()
        return "Course not found", 404

    num_of_module, num_of_students = course

    # Calculate threshold
    value = (num_of_module * 10) + 20
    threshold = value * 0.8

    # Fetch all total_point from enrollment_status for the course
    cursor.execute("""
        SELECT student_id, total_point
        FROM enrollment_status
        WHERE course_code = %s
    """, (course_code,))
    enrollment_data = cursor.fetchall()  # List of tuples (student_id, total_point)

    # Update status based on threshold
    for student_id, total_point in enrollment_data:
        if total_point >= threshold:
            cursor.execute("""
                UPDATE enrollment_status
                SET status = 'completed'
                WHERE course_code = %s AND student_id = %s
            """, (course_code, student_id))
    mysql.connection.commit()

    # Count students with status='completed'
    cursor.execute("""
        SELECT COUNT(*)
        FROM enrollment_status
        WHERE course_code = %s AND status = 'completed'
    """, (course_code,))
    N = cursor.fetchone()[0]  # Number of students with 'completed' status

    # Calculate completion rate
    if num_of_students > 0:
        rate = round((N / num_of_students) * 100, 2)
    else:
        rate = 0.00

    # Update completion_rate in courses table
    cursor.execute("""
        UPDATE courses
        SET completation_rate = %s
        WHERE course_code = %s
    """, (rate, course_code))
    mysql.connection.commit()
    
    cursor.close()

    # Fetch course details from courses table
    cursor = mysql.connection.cursor()
    course_query = """
        SELECT course_name, category, num_of_students, completation_rate
        FROM courses
        WHERE course_code = %s
    """
    cursor.execute(course_query, (course_code,))
    course = cursor.fetchone()  # (course_name, category, num_of_students, completion_rate)

    if not course:
        cursor.close()
        return "Course not found", 404

    # Fetch content details from content table
    content_query = """
        SELECT module_no, outline_pdf, pdf_file, module_video, assignment, deadline
        FROM content
        WHERE course_code = %s
        ORDER BY module_no ASC
    """
    cursor.execute(content_query, (course_code,))
    content = cursor.fetchall()  # List of content for the course
    
    # Fetch feedback for the course (Students)
    feedback_query = """
        SELECT s.name, sf.feedback
        FROM student_feedback sf
        INNER JOIN students s ON sf.student_id = s.student_id
        WHERE sf.course_code = %s
        ORDER BY sf.f_no DESC
    """
    cursor.execute(feedback_query, (course_code,))
    feedbacks = cursor.fetchall()
    
    # Fetch feedback for the course (Instructors)
    ifeedback_query = """
        SELECT i.name, f.feedback
        FROM instructor_feedback f
        INNER JOIN instructors i ON f.instructor_id = i.instructor_id
        WHERE f.course_code = %s
        ORDER BY f.f_no DESC
    """
    cursor.execute(ifeedback_query, (course_code,))
    ifeedbacks = cursor.fetchall()
    
    cursor.close()

    return render_template(
        'a_view_course.html',
        course_code=course_code,
        course_name=course[0],
        course_category=course[1],
        num_of_students=course[2],
        completion_rate=course[3],
        content=content if content else [],  # Pass empty list if no modules
        feedbacks=feedbacks,
        ifeedbacks=ifeedbacks
    )

# Profile Page Route
@app.route('/a_profile', methods=['GET', 'POST'])
def a_profile():
    if 'admin_id' not in session:
        flash("You need to login first!", 'danger')
        return redirect(url_for('a_login'))
    
    admin_id = session['admin_id']
    cursor = mysql.connection.cursor()
    
    # If the form is submitted (POST request), update the admin's information
    if request.method == 'POST':
        # Get updated data from the form
        new_name = request.form['name']
        new_password = request.form['password']
        new_address = request.form['address']
        new_dob = request.form['date_of_birth']
        new_blood_group = request.form['blood_group']
        new_picture = request.files['profile_picture']
        
        # Fetch admin data from the database
        cursor = mysql.connection.cursor()
        cursor.execute("SELECT * FROM admin WHERE admin_id = %s", (admin_id,))
        admin = cursor.fetchone()  # Fetch the admin's record
        cursor.close()
        
        if not admin:
            flash("Admin not found", 'danger')
            return redirect(url_for('a_login'))
                
        # Handle profile picture upload
        if new_picture and new_picture.filename.strip():
            filename = secure_filename(new_picture.filename)
            file_path = os.path.join('static/uploads', filename)
            file_path = file_path.replace("\\", "/")
            new_picture.save(file_path)
        else:
            file_path = admin[8]  # Keep old picture if no new one

        # Update the student's information in the database (except for student_id, phone_no, and email)
        cursor = mysql.connection.cursor()
        
        update_query = """
            UPDATE admin
            SET name = %s, password = %s, address = %s,
                date_of_birth = %s, blood_group = %s, profile_picture = %s
            WHERE admin_id = %s
        """
        cursor.execute(update_query, (new_name, new_password, new_address, new_dob, new_blood_group, file_path, admin_id))
        mysql.connection.commit()
        cursor.close()

        flash('Profile updated successfully!', 'success')
        return redirect(url_for('a_profile'))

    # Fetch admin data from the database
    cursor.execute("SELECT * FROM admin WHERE admin_id = %s", (admin_id,))
    admin = cursor.fetchone()  # Fetch the admin's record
    cursor.close()

    if admin:  # Ensure admin exists
        # Assign fetched data to variables
        admin_id = admin[1]  
        admin_name = admin[0]  
        phone_no = admin[2]  
        email = admin[3] 
        password = admin[4]   
        address = admin[5]  
        date_of_birth = admin[6] 
        blood_group = admin[7]  
        profile_picture = admin[8] 
        
        return render_template('a_profile.html', admin=admin, 
                               admin_id=admin_id, 
                               admin_name=admin_name, 
                               phone_no=phone_no,
                               email=email,
                               password=password,
                               address=address,
                               date_of_birth=date_of_birth,
                               blood_group=blood_group,
                               profile_picture=profile_picture)
    
    else:
        flash("Admin not found", 'danger')
        return redirect(url_for('a_login'))    
        

    # Render the profile template with admin data
    return render_template('a_profile.html', admin=admin)

@app.route('/all_students')
def all_students():
    if 'admin_id' in session:
        admin_id = session['admin_id']

        # Fetch student data from the database
        cursor = mysql.connection.cursor()
        query = "SELECT student_id, name, email, address FROM students"
        cursor.execute(query)
        students = cursor.fetchall()  # Fetch all rows
        cursor.close()

        # Convert the fetched data into a list of dictionaries
        students_list = [
            {
                'student_id': student[0],
                'name': student[1],
                'email': student[2],
                'address': student[3]
            } for student in students
        ]

        return render_template('all_students.html', students=students_list)

    return redirect(url_for('a_login'))

import matplotlib
matplotlib.use('Agg')  # Set the backend to 'Agg'

import matplotlib.pyplot as plt
import os

@app.route('/student_info/<int:student_id>', methods=['GET', 'POST'])
def student_info(student_id):
    if 'admin_id' in session:
        admin_id = session['admin_id']

        # Fetch student data from the database
        cursor = mysql.connection.cursor()
        query = "SELECT student_id, name, phone_no, email, password, current_institute, address, date_of_birth, blood_group, profile_picture FROM students WHERE student_id = %s"
        cursor.execute(query, (student_id,))
        student = cursor.fetchone()
        

        # Fetch enrolled courses info
        query_courses = """SELECT courses.course_name, courses.course_code, enrollment_status.status 
                           FROM enrollment_status 
                           JOIN courses ON enrollment_status.course_code = courses.course_code
                           WHERE enrollment_status.student_id = %s"""
        cursor.execute(query_courses, (student_id,))
        enrolled_courses = cursor.fetchall()
        cursor.close()

        if request.method == 'POST':
            # Update student info
            name = request.form['name']
            phone_no = request.form['phone_no']
            email = request.form['email']
            password = request.form['password']
            current_institute = request.form['current_institute']
            address = request.form['address']
            date_of_birth = request.form['date_of_birth']
            blood_group = request.form['blood_group']

            cursor = mysql.connection.cursor()
            update_query = """UPDATE students SET name = %s, phone_no = %s, email = %s, password = %s, 
                              current_institute = %s, address = %s, date_of_birth = %s, blood_group = %s 
                              WHERE student_id = %s"""
            cursor.execute(update_query, (name, phone_no, email, password, current_institute, address, date_of_birth, blood_group, student_id))
            mysql.connection.commit()
            cursor.close()
            
            return redirect(url_for('student_info', student_id=student_id))
            
        # Fetch course details and calculate completion status
        cursor = mysql.connection.cursor()
        cursor.execute("""
            SELECT e.course_code, e.status, e.total_point, c.course_name, c.num_of_module
            FROM enrollment_status e
            JOIN courses c ON e.course_code = c.course_code
            WHERE e.student_id = %s
        """, (student_id,))
        courses = cursor.fetchall()

        completion_status = []
        course_names = []
        for course in courses:
            course_code, status, total_point, course_name, num_of_module = course
            full_marks = (num_of_module * 10) + 20
            complete_status = (total_point / full_marks) * 100
            completion_status.append(round(complete_status, 2))
            course_names.append(course_name)
            
        # Generate the bar chart and save it as a file
        chart_path = os.path.join('static', 'charts', f'student_{student_id}_chart.png')
        os.makedirs(os.path.dirname(chart_path), exist_ok=True)  # Ensure the directory exists

        plt.figure(figsize=(10, 6))
        plt.bar(course_names, completion_status, color='green')
        plt.xlabel('Course Name')
        plt.ylabel('Completion Status (%)')
        plt.title('Course Completion Status')
        for i, status in enumerate(completion_status):
            plt.text(i, status + 1, f"{status:.2f}%", ha='center', fontsize=10)
        plt.savefig(chart_path)
        plt.close()

        cursor.close()
        
        # Return the relative path of the chart image
        chart_url = f'charts/student_{student_id}_chart.png'

        return render_template('student_details.html', 
                                student=student, 
                                enrolled_courses=enrolled_courses,
                                courses=courses,
                                course_names=course_names,
                                completion_status=completion_status,
                                chart_url=chart_url
                                )

    return redirect(url_for('a_login'))

@app.route('/delete_student/<int:student_id>', methods=['POST'])
def delete_student(student_id):
    if 'admin_id' in session:
        # Delete the student and all related data using cascading delete
        cursor = mysql.connection.cursor()

        # Delete from students table (cascading delete will handle related data in other tables)
        query = "DELETE FROM students WHERE student_id = %s"
        cursor.execute(query, (student_id,))
        
        mysql.connection.commit()
        cursor.close()

        return redirect(url_for('all_students'))

    return redirect(url_for('a_login'))

@app.route('/all_instructors')
def all_instructors():
    if 'admin_id' in session:
        admin_id = session['admin_id']

        # Fetch student data from the database
        cursor = mysql.connection.cursor()
        query = "SELECT instructor_id, name, email, address FROM instructors"
        cursor.execute(query)
        instructors = cursor.fetchall()  # Fetch all rows
        cursor.close()

        # Convert the fetched data into a list of dictionaries
        instructors_list = [
            {
                'instructor_id': instructor[0],
                'name': instructor[1],
                'email': instructor[2],
                'address': instructor[3]
            } for instructor in instructors
        ]

        return render_template('all_instructors.html', instructors=instructors_list)

    return redirect(url_for('a_login'))

@app.route('/instructor_info/<int:instructor_id>')
def instructor_info(instructor_id):
    cursor = mysql.connection.cursor()
    
    # Fetch instructor details
    query_instructor = """
    SELECT name, instructor_id, phone_no, email, password, course_name, address, date_of_birth, blood_group 
    FROM instructors WHERE instructor_id = %s
    """
    cursor.execute(query_instructor, (instructor_id,))
    instructor = cursor.fetchone()
    
    # Fetch courses created by instructor
    query_courses = """
    SELECT course_name, course_code, category, num_of_module, num_of_students, completation_rate 
    FROM courses WHERE instructor_id = %s
    """
    cursor.execute(query_courses, (instructor_id,))
    courses = cursor.fetchall()
    cursor.close()

    if instructor:
        instructor_data = {
            "name": instructor[0],
            "instructor_id": instructor[1],
            "phone_no": instructor[2],
            "email": instructor[3],
            "password": instructor[4],
            "course_name": instructor[5],
            "address": instructor[6],
            "date_of_birth": instructor[7],
            "blood_group": instructor[8],
        }
        course_data = [
            {
                "course_name": course[0],
                "course_code": course[1],
                "category": course[2],
                "num_of_module": course[3],
                "num_of_students": course[4],
                "completation_rate": course[5],
            }
            for course in courses
        ]
        return render_template('instructor_details.html', **instructor_data, courses=course_data)
    return redirect(url_for('all_instructors'))

@app.route('/update_instructor', methods=['POST'])
def update_instructor():
    if 'admin_id' in session:  # Ensure only logged-in admins can update
        instructor_id = request.form.get('instructor_id')  # Extract instructor_id from the form
        name = request.form.get('name')
        phone_no = request.form.get('phone_no')
        email = request.form.get('email')
        password = request.form.get('password')
        course_name = request.form.get('course_name')
        address = request.form.get('address')
        date_of_birth = request.form.get('date_of_birth')
        blood_group = request.form.get('blood_group')

        cursor = mysql.connection.cursor()

        # Update query
        query = """
        UPDATE instructors
        SET name = %s, phone_no = %s, email = %s, password = %s,
            course_name = %s, address = %s, date_of_birth = %s, blood_group = %s
        WHERE instructor_id = %s
        """
        cursor.execute(query, (name, phone_no, email, password, course_name, address, date_of_birth, blood_group, instructor_id))
        mysql.connection.commit()
        cursor.close()

        flash("Instructor information updated successfully!", "success")
        return redirect(url_for('instructor_info', instructor_id=instructor_id))

    flash("You need to log in to access this page.", "danger")
    return redirect(url_for('a_login'))


@app.route('/a_logout')
def a_logout():
    session.pop('admin_name', None)  # Remove the admin's name from the session
    return redirect(url_for('a_login'))

if __name__ == '__main__':
    app.run(debug=True, port=1717)
