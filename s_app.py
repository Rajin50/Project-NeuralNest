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

@app.route('/get_courses', methods=['GET', 'POST'])
def get_courses():
    if request.method == 'POST':
        data = request.get_json()
        query = data.get('query', None)
        filter_category = data.get('filter', None)
    else:
        # Handle GET request (optional)
        query = None
        filter_category = None

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

    # For GET request, you may render an HTML page if needed
    if request.method == 'GET':
        return render_template('s_browse_courses.html', courses=course_list)
    
    return {'data': course_list}


@app.route('/enroll_course/<course_code>')
def enroll_course(course_code):
    student_id = session.get('student_id')
    cursor = mysql.connection.cursor()
    
    # Fetch course details
    cursor.execute('SELECT course_name FROM courses WHERE course_code = %s', (course_code,))
    course = cursor.fetchone()
    if not course:
        return "Course not found", 404
    
    # Check if student is already enrolled in the course
    cursor.execute("""
        SELECT 1 FROM enrollment_status WHERE student_id = %s AND course_code = %s
    """, (student_id, course_code))
    existing_enrollment = cursor.fetchone()
    if existing_enrollment:
        return render_template('enroll.html', message="You've already enrolled in this course!", course_name=course[0], course_code=course_code)

    # Insert into enrollment_status table
    enroll_date = date.today()
    cursor.execute(
        'INSERT INTO enrollment_status (course_code, student_id, enroll_date, status, total_point) VALUES (%s, %s, %s, %s, %s)',
        (course_code, student_id, enroll_date, 'incomplete', 0)
    )
    
    # Update num_of_students in the courses table
    cursor.execute(
        'UPDATE courses SET num_of_students = num_of_students + 1 WHERE course_code = %s',
        (course_code,)
    )
    
    mysql.connection.commit()
    cursor.close()

    # Redirect to enroll.html with course name
    return render_template('enroll.html', course_name=course[0], course_code=course_code)  # Use index 0 since fetchone() returns a tuple

# Profile Page Route
@app.route('/profile', methods=['GET', 'POST'])
def profile():
    if 'student_id' not in session:
        flash("You need to login first!", 'danger')
        return redirect(url_for('login'))
    
    student_id = session['student_id']
    cursor = mysql.connection.cursor()
    
    # If the form is submitted (POST request), update the student's information
    if request.method == 'POST':
        # Get updated data from the form
        new_name = request.form['name']
        new_password = request.form['password']
        new_institute = request.form['current_institute']
        new_address = request.form['address']
        new_dob = request.form['date_of_birth']
        new_blood_group = request.form['blood_group']
        new_picture = request.files['profile_picture'] 
        
        # Fetch current student data for fallback values
        cursor = mysql.connection.cursor()
        cursor.execute("SELECT * FROM students WHERE student_id = %s", (student_id,))
        student = cursor.fetchone()  # Fetch the student's record
        cursor.close()

        if not student:
            flash("Student not found!", "danger")
            return redirect(url_for('login'))
                
        # Handle profile picture upload
        if new_picture and new_picture.filename.strip():
            filename = secure_filename(new_picture.filename)
            file_path = os.path.join('static/uploads', filename)
            file_path = file_path.replace("\\", "/")
            new_picture.save(file_path)
        else:
            file_path = student[9]   # Keep old picture if no new one
            
        # Update the student's information in the database (except for student_id, phone_no, and email)
        cursor = mysql.connection.cursor()
        
        update_query = """
            UPDATE students
            SET name = %s, password = %s, current_institute = %s, address = %s,
                date_of_birth = %s, blood_group = %s, profile_picture = %s
            WHERE student_id = %s
        """
        cursor.execute(update_query, (new_name, new_password, new_institute, new_address, new_dob, new_blood_group, file_path, student_id))
        mysql.connection.commit()
        cursor.close()

        flash('Profile updated successfully!', 'success')
        return redirect(url_for('profile'))

    # Fetch student data from the database
    cursor.execute("SELECT * FROM students WHERE student_id = %s", (student_id,))
    student = cursor.fetchone()  # Fetch the student's record
    cursor.close()

    if student and request.method == 'GET':  # Ensure student exists
        # Assign fetched data to variables
        student_id = student[1]  
        student_name = student[0]  
        phone_no = student[2]  
        email = student[3] 
        password = student[4] 
        current_institute = student[5]  
        address = student[6]  
        date_of_birth = student[7] 
        blood_group = student[8]  
        profile_picture = student[9] 
        
        return render_template('s_profile.html', student=student, 
                               student_id=student_id, 
                               student_name=student_name, 
                               phone_no=phone_no,
                               email=email,
                               password=password,
                               current_institute=current_institute,
                               address=address,
                               date_of_birth=date_of_birth,
                               blood_group=blood_group,
                               profile_picture=profile_picture)
    
    else:
        flash("Student not found", 'danger')
        return redirect(url_for('login'))    

    # Render the profile template with student data
    return render_template('s_profile.html', student=student)

@app.route('/view_course/<int:course_code>')
def view_course(course_code):
    cursor = mysql.connection.cursor()
    # Fetch num_of_module from the courses table for the given course_code
    cursor.execute("""
        SELECT num_of_module
        FROM courses
        WHERE course_code = %s
    """, (course_code,))
    result = cursor.fetchone()
    
    if not result:
        cursor.close()
        return "Course not found", 404
    
    num_of_module = result[0]
    # Calculate the threshold
    value = (num_of_module * 10) + 20
    threshold = value * 0.8

    # Fetch total_point from the enrollment_status table and update status if needed
    student_id = session.get('student_id')  
    if student_id:
        cursor.execute("""
            SELECT total_point
            FROM enrollment_status
            WHERE course_code = %s AND student_id = %s
        """, (course_code, student_id))
        result = cursor.fetchone()
        
        if result:
            total_point = result[0]
            # Compare total_point with threshold
            if total_point >= threshold:
                cursor.execute("""
                    UPDATE enrollment_status
                    SET status = 'completed'
                    WHERE course_code = %s AND student_id = %s
                """, (course_code, student_id))
                mysql.connection.commit()

    # Update leaderboard table based on total_point of all students
    cursor.execute("""
        SELECT student_id, total_point
        FROM enrollment_status
        WHERE course_code = %s
        ORDER BY total_point DESC
        LIMIT 5
    """, (course_code,))
    top_students = cursor.fetchall()  # List of tuples (student_id, total_point)

    # Prepare leaderboard values
    leaderboard_values = [None] * 5
    for i, student in enumerate(top_students):
        leaderboard_values[i] = student[0]  # Assign student_id to appropriate position
    
    # Update leaderboard table
    cursor.execute("""
        INSERT INTO leaderboard (course_code, p1, p2, p3, p4, p5)
        VALUES (%s, %s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
        p1 = VALUES(p1), p2 = VALUES(p2), p3 = VALUES(p3),
        p4 = VALUES(p4), p5 = VALUES(p5)
    """, (course_code, *leaderboard_values))
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
    
    # Fetch leaderboard for the course
    leaderboard_query = """
        SELECT p1, p2, p3, p4, p5
        FROM leaderboard
        WHERE course_code = %s
    """
    cursor.execute(leaderboard_query, (course_code,))
    leaderboard = cursor.fetchone()  # (p1, p2, p3, p4, p5)

    # Fetch student names for the leaderboard positions
    student_names = []
    if leaderboard:
        for position in leaderboard:
            if position:  # Check if the position is not None
                cursor.execute("SELECT name FROM students WHERE student_id = %s", (position,))
                student = cursor.fetchone()
                if student:
                    student_names.append(student[0])
                    
    # Fetch feedback for the course
    feedback_query = """
        SELECT s.name, sf.feedback
        FROM student_feedback sf
        INNER JOIN students s ON sf.student_id = s.student_id
        WHERE sf.course_code = %s
        ORDER BY sf.f_no DESC
    """
    cursor.execute(feedback_query, (course_code,))
    feedbacks = cursor.fetchall()
    
    # Check if the student has already taken the exam
    student_id = session.get('student_id')  # Assuming student_id is stored in session
    exam_attempted = False
    total_mark = None
    if student_id:
        exam_query = """
            SELECT total_mark
            FROM exams
            WHERE course_code = %s AND student_id = %s
        """
        cursor.execute(exam_query, (course_code, student_id))
        exam_result = cursor.fetchone()
        if exam_result:
            exam_attempted = True
            total_mark = exam_result[0]
            
    student_id = session.get('student_id')
    assignment_status = {}

    if student_id:
        for module in content:
            module_no = module[0]
            
            # Check if the student has submitted an assignment
            cursor.execute("""
                SELECT submitted_assignments, submission_date, marks
                FROM assignments
                WHERE student_id = %s AND course_code = %s AND module_no = %s
            """, (student_id, course_code, module_no))
            submission = cursor.fetchone()
            
            if submission:
                submitted = True
                submission_date = submission[1]
                late = submission_date > module[5]  # Compare with deadline
                marks = submission[2]
            else:
                submitted = False
                submission_date = None
                late = False
                marks = None
            
            assignment_status[module_no] = {
                "submitted": submitted,
                "submission_date": submission_date,
                "late": late,
                "marks": marks
            }

    cursor.close()

    return render_template(
        's_view_course.html',
        course_code=course_code,
        course_name=course[0],
        course_category=course[1],
        num_of_students=course[2],
        completion_rate=course[3],
        content=content if content else [],  # Pass empty list if no modules
        leaderboard=student_names,
        feedbacks=feedbacks,
        exam_attempted=exam_attempted,
        total_mark=total_mark,
        assignment_status=assignment_status
    )
    
@app.route('/certifications', methods=['GET'])

def certifications():
    if 'student_id' in session:
        student_id = session['student_id']
        
        cursor = mysql.connection.cursor()
        # Fetch completed courses
        cursor.execute("""
            SELECT c.course_code, c.course_name, c.course_picture
            FROM courses c
            INNER JOIN enrollment_status e ON c.course_code = e.course_code
            WHERE e.student_id = %s AND e.status = 'completed'
        """, (student_id,))
        certifications = cursor.fetchall()
        
        cert_data = [{'course_code': cert[0], 'course_name': cert[1], 'course_picture': cert[2]} for cert in certifications]
        cursor.close()
        
        return render_template('s_certifications.html', certifications=cert_data)
    return redirect(url_for('login'))

@app.route('/get_certificate/<int:course_code>')
def get_certificate(course_code):
    if 'student_id' in session:
        student_id = session['student_id']
        cursor = mysql.connection.cursor()

        # Fetch student's name
        cursor.execute("SELECT name FROM students WHERE student_id = %s", (student_id,))
        student = cursor.fetchone()
        student_name = student[0] if student else "Unknown Student"

        # Fetch course name
        cursor.execute("SELECT course_name FROM courses WHERE course_code = %s", (course_code,))
        course = cursor.fetchone()
        course_name = course[0] if course else "Unknown Course"

        # Generate current date
        current_date = datetime.now().strftime("%Y-%m-%d")

        # Generate certificate ID
        cursor.execute("SELECT MAX(certificate_id) FROM certificates")
        last_id = cursor.fetchone()[0] or 42000000
        certificate_id = last_id + 1

        # Insert certificate record
        cursor.execute("""
            INSERT INTO certificates (certificate_id, student_id, course_code, issue_date)
            VALUES (%s, %s, %s, %s)
        """, (certificate_id, student_id, course_code, current_date))
        mysql.connection.commit()

        cursor.close()

        return render_template(
            'certificate_page.html',
            student_name=student_name,
            course_name=course_name,
            current_date=current_date,
            certificate_id=certificate_id
        )
    return redirect(url_for('login'))


@app.route('/submit_assignment/<int:course_code>/<int:module_no>', methods=['POST'])
def submit_assignment(course_code, module_no):
    if 'student_id' not in session:
        return redirect(url_for('login'))  # Redirect to login if not logged in

    student_id = session['student_id']
    assignment_file = request.files.get('assignment_file')
    
    if assignment_file and assignment_file.filename.endswith('.pdf'):
        filename = f"assignment_{student_id}_{course_code}_{module_no}.pdf"
        filepath = os.path.join('static/uploads', filename)
        assignment_file.save(filepath)
        
        submission_date = datetime.now().strftime('%Y-%m-%d')
        cursor = mysql.connection.cursor()
        
        # Check if the student has already submitted
        cursor.execute("""
            SELECT * FROM assignments
            WHERE student_id = %s AND course_code = %s AND module_no = %s
        """, (student_id, course_code, module_no))
        
        if cursor.fetchone():
            cursor.close()
            return redirect(url_for('view_course', course_code=course_code, module_no=module_no))

        # Insert assignment details
        cursor.execute("""
            INSERT INTO assignments (student_id, course_code, module_no, submitted_assignments, submission_date)
            VALUES (%s, %s, %s, %s, %s)
        """, (student_id, course_code, module_no, filename, submission_date))
        mysql.connection.commit()
        
        # Check if submission is late
        cursor.execute("""
            SELECT deadline
            FROM content
            WHERE course_code = %s AND module_no = %s
        """, (course_code, module_no))
        deadline = cursor.fetchone()[0]
        cursor.close()
        
        submission_date_obj = datetime.strptime(submission_date, '%Y-%m-%d').date()
        
        if submission_date_obj > deadline:
            flash("You've submitted a late assignment!", "warning")
        else:
            flash("Assignment submitted successfully!", "success")

    else:
        flash("Invalid file. Please upload a PDF.", "danger")
    
    return redirect(url_for('view_course', course_code=course_code))
    
    
@app.route('/submit_feedback/<int:course_code>', methods=['POST'])
def submit_feedback(course_code):
    if 'student_id' not in session:
        return redirect(url_for('login'))  # Redirect if the student is not logged in

    student_id = session['student_id']
    feedback = request.form['feedback']

    # Insert the feedback into the database
    cursor = mysql.connection.cursor()
    insert_query = """
        INSERT INTO student_feedback (course_code, student_id, feedback)
        VALUES (%s, %s, %s)
    """
    cursor.execute(insert_query, (course_code, student_id, feedback))
    mysql.connection.commit()
    cursor.close()

    flash("Your feedback has been submitted successfully.", "success")
    return redirect(url_for('view_course', course_code=course_code))


@app.route('/get_exam_page/<int:course_code>', methods=['GET'])
def get_exam_page(course_code):
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT course_exam FROM courses WHERE course_code = %s", (course_code,))
    result = cursor.fetchone()
    cursor.close()
    if result:
        return jsonify({"exam_page": result[0]})  # Return the `course_exam` field
    else:
        return jsonify({"exam_page": None}), 404  # Return a 404 if no exam page is found
    
#=========================ds_exam_part==========================================================================================

@app.route('/ds_exam/<int:course_code>')
def ds_exam(course_code):
    cursor = mysql.connection.cursor()

    # Fetch student information
    student_id = session.get('student_id')
    if not student_id:
        return redirect('/login')

    cursor.execute("SELECT name FROM students WHERE student_id = %s", (student_id,))
    student = cursor.fetchone()
    student_name = student[0]
    # Fetch questions (predefined in this example)
    questions = [
        {"id": 1, "question": "What is data science primarily concerned with?", 
        "options": ["Analyzing data", "Designing websites", "Hardware engineering", "Writing novels"], 
        "answer": "a"},
        {"id": 2, "question": "Which of the following is a common programming language used in data science?", 
        "options": ["HTML", "Python", "CSS", "PHP"], 
        "answer": "b"},
        {"id": 3, "question": "What is the purpose of data visualization?", 
        "options": ["To clean the data", "To represent data graphically", "To store data in databases", "To perform mathematical calculations"], 
        "answer": "b"},
        {"id": 4, "question": "Which library in Python is widely used for data manipulation?", 
        "options": ["NumPy", "Pandas", "TensorFlow", "Matplotlib"], 
        "answer": "b"},
        {"id": 5, "question": "What does the term 'Big Data' refer to?", 
        "options": ["A type of data structure", "Large and complex data sets", "An algorithm for sorting data", "A file format for storing data"], 
        "answer": "b"},
        {"id": 6, "question": "What is the first step in the data science process?", 
        "options": ["Data cleaning", "Data collection", "Data visualization", "Model deployment"], 
        "answer": "b"},
        {"id": 7, "question": "Which of the following best describes machine learning?", 
        "options": ["A subset of artificial intelligence", "A database query language", "A type of data visualization", "A programming paradigm"], 
        "answer": "a"},
        {"id": 8, "question": "What is a 'dataset' in data science?", 
        "options": ["A collection of related data points", "A tool for analyzing data", "A programming library", "A database management system"], 
        "answer": "a"},
        {"id": 9, "question": "What does 'EDA' stand for in data science?", 
        "options": ["Extensive Data Analysis", "Exploratory Data Analysis", "Experimental Data Algorithm", "Exact Data Approach"], 
        "answer": "b"},
        {"id": 10, "question": "Which of the following is a type of supervised learning algorithm?", 
        "options": ["K-Means", "Linear Regression", "DBSCAN", "Apriori"], 
        "answer": "b"}
    ]

    cursor.close()
    return render_template('ds_exam.html', student_name=student_name, course_code=course_code, questions=questions)

# Define the function to generate HTML content for results
def generate_results_html(answers, correct_answers):
    results_html = ""
    for question_id, selected_option in answers.items():
        if question_id == "course_code":
            output = question_id
        else:
            question_number = question_id[1:]  # Extract question number (e.g., 'q1' -> '1')
            correct_answer = correct_answers.get(f'q{question_number}')
            is_correct = selected_option == correct_answer
            
            # Apply different styles based on correctness
            color = "green" if is_correct else "red"
            results_html += f'<p style="color:{color}">Question {question_number}: {"Correct" if is_correct else "Incorrect"}</p>'

    return results_html


@app.route('/submit_exam/<int:course_code>', methods=['POST'])
def submit_exam(course_code):
    cursor = mysql.connection.cursor()
    student_id = session.get('student_id')
    answers = request.form.to_dict()  # This will get all the form data as a dictionary
    
    # Define correct answers
    correct_answers = {
        "q1": "a",
        "q2": "b",
        "q3": "b",
        "q4": "b",
        "q5": "b",
        "q6": "b",
        "q7": "a",
        "q8": "a",
        "q9": "b",
        "q10": "b"
    }
    
    # Insert default marks for the student
    cursor.execute("INSERT INTO exams (course_code, student_id, q1_mark, q2_mark, q3_mark, q4_mark, q5_mark, q6_mark, q7_mark, q8_mark, q9_mark, q10_mark) VALUES (%s, %s, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)", 
                   (course_code, student_id))
    
    total_marks = 0
    # Logic to calculate marks and update exam table
    for i in range(1, 11):
        question_id = f'q{i}'
        selected_option = answers.get(question_id)
        if selected_option == correct_answers[question_id]:
            total_marks += 2
            cursor.execute(f"UPDATE exams SET q{i}_mark = 2 WHERE course_code = %s AND student_id = %s", (course_code, student_id))
        else:
            cursor.execute(f"UPDATE exams SET q{i}_mark = 0 WHERE course_code = %s AND student_id = %s", (course_code, student_id))

    # Update total marks
    cursor.execute("UPDATE exams SET total_mark = %s WHERE course_code = %s AND student_id = %s", (total_marks, course_code, student_id))
    cursor.execute("UPDATE enrollment_status SET total_point = total_point + %s WHERE course_code = %s AND student_id = %s", (total_marks, course_code, student_id))
    mysql.connection.commit()
    cursor.close()

    # Generate HTML for results to be displayed
    results_html = generate_results_html(answers, correct_answers)

    return jsonify({"total_points": total_marks, "results_html": results_html})

#====================================python_exam_part====================================================================================================

@app.route('/python_exam/<int:course_code>')
def python_exam(course_code):
    cursor = mysql.connection.cursor()

    # Fetch student information
    student_id = session.get('student_id')
    if not student_id:
        return redirect('/login')

    cursor.execute("SELECT name FROM students WHERE student_id = %s", (student_id,))
    student = cursor.fetchone()
    student_name = student[0]
    
    # Fetch questions (predefined in this example)
    questions = [
        {"id": 1, "question": "Which of the following is a key feature of Python?", 
        "options": ["Statically typed", "Interpreted", "Complex syntax", "Limited to web development"], 
        "answer": "b"},
        {"id": 2, "question": "What is the correct extension for a Python file?", 
        "options": [".pyth", ".py", ".pt", ".p"], 
        "answer": "b"},
        {"id": 3, "question": "Which keyword is used to define a function in Python?", 
        "options": ["func", "function", "def", "define"], 
        "answer": "c"},
        {"id": 4, "question": "How do you print a message in Python?", 
        "options": ["echo 'Hello'", "print('Hello')", "printf('Hello')", "println('Hello')"], 
        "answer": "b"},
        {"id": 5, "question": "Which of the following data types is immutable in Python?", 
        "options": ["List", "Set", "Dictionary", "Tuple"], 
        "answer": "d"},
        {"id": 6, "question": "What does 'PEP' stand for in the Python community?", 
        "options": ["Python Enhanced Proposal", "Python Enhancement Process", "Python Enhancement Proposal", "Programming Easy Protocol"], 
        "answer": "c"},
        {"id": 7, "question": "Which built-in Python function can be used to get the length of a list?", 
        "options": ["size()", "len()", "length()", "get_length()"], 
        "answer": "b"},
        {"id": 8, "question": "What is the output of the following code: print(type(5))?", 
        "options": ["<class 'int'>", "<type 'integer'>", "int", "integer"], 
        "answer": "a"},
        {"id": 9, "question": "Which symbol is used for comments in Python?", 
        "options": ["//", "#", "/* */", "%%"], 
        "answer": "b"},
        {"id": 10, "question": "What does the 'pass' statement do in Python?", 
        "options": ["Exits a loop", "Does nothing", "Breaks a function", "Continues the program with an error"], 
        "answer": "b"}
    ]

    cursor.close()
    return render_template('python_exam.html', student_name=student_name, course_code=course_code, questions=questions)

# Define the function to generate HTML content for results
def generate_results_html(answers, correct_answers):
    results_html = ""
    for question_id, selected_option in answers.items():
        if question_id == "course_code":
            output = question_id
        else:
            question_number = question_id[1:]  # Extract question number (e.g., 'q1' -> '1')
            correct_answer = correct_answers.get(f'q{question_number}')
            is_correct = selected_option == correct_answer
            
            # Apply different styles based on correctness
            color = "green" if is_correct else "red"
            results_html += f'<p style="color:{color}">Question {question_number}: {"Correct" if is_correct else "Incorrect"}</p>'

    return results_html

@app.route('/submit_python_exam/<int:course_code>', methods=['POST'])
def submit_python_exam(course_code):
    cursor = mysql.connection.cursor()
    student_id = session.get('student_id')
    answers = request.form.to_dict()  # This will get all the form data as a dictionary
    
    # Define correct answers
    correct_answers = {
        "q1": "b",
        "q2": "b",
        "q3": "c",
        "q4": "b",
        "q5": "d",
        "q6": "c",
        "q7": "b",
        "q8": "a",
        "q9": "b",
        "q10": "b"
    }
    
    # Insert default marks for the student
    cursor.execute("INSERT INTO exams (course_code, student_id, q1_mark, q2_mark, q3_mark, q4_mark, q5_mark, q6_mark, q7_mark, q8_mark, q9_mark, q10_mark) VALUES (%s, %s, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)", 
                   (course_code, student_id))
    
    total_marks = 0
    # Logic to calculate marks and update exam table
    for i in range(1, 11):
        question_id = f'q{i}'
        selected_option = answers.get(question_id)
        if selected_option == correct_answers[question_id]:
            total_marks += 2
            cursor.execute(f"UPDATE exams SET q{i}_mark = 2 WHERE course_code = %s AND student_id = %s", (course_code, student_id))
        else:
            cursor.execute(f"UPDATE exams SET q{i}_mark = 0 WHERE course_code = %s AND student_id = %s", (course_code, student_id))
    
    # Update total marks
    cursor.execute("UPDATE exams SET total_mark = %s WHERE course_code = %s AND student_id = %s", (total_marks, course_code, student_id))
    cursor.execute("UPDATE enrollment_status SET total_point = total_point + %s WHERE course_code = %s AND student_id = %s", (total_marks, course_code, student_id))
    mysql.connection.commit()
    cursor.close()

    # Generate HTML for results to be displayed
    results_html = generate_results_html(answers, correct_answers)

    return jsonify({"total_points": total_marks, "results_html": results_html})

#==================================stat_exam_part=======================================================================================================================

@app.route('/stat_exam/<int:course_code>')
def stat_exam(course_code):
    cursor = mysql.connection.cursor()

    # Fetch student information
    student_id = session.get('student_id')
    if not student_id:
        return redirect('/login')

    cursor.execute("SELECT name FROM students WHERE student_id = %s", (student_id,))
    student = cursor.fetchone()
    student_name = student[0]
    
    # Fetch Statistics questions (predefined in this example)
    questions = [
        {"id": 1, "question": "What is the mean of the numbers 2, 4, 6, 8, 10?", 
        "options": ["4", "6", "8", "10"], 
        "answer": "b"},
        {"id": 2, "question": "What does the median represent in a dataset?", 
        "options": ["The average value", "The middle value", "The most frequent value", "The range"], 
        "answer": "b"},
        {"id": 3, "question": "Which of the following measures dispersion in a dataset?", 
        "options": ["Mean", "Median", "Standard Deviation", "Mode"], 
        "answer": "c"},
        {"id": 4, "question": "What does a histogram primarily display?", 
        "options": ["Relationships between variables", "Data distribution", "Time series data", "Categorical data"], 
        "answer": "b"},
        {"id": 5, "question": "What is a p-value used for in statistics?", 
        "options": ["To measure dispersion", "To test hypotheses", "To calculate averages", "To determine sample size"], 
        "answer": "b"},
        {"id": 6, "question": "Which of the following is an example of a continuous variable?", 
        "options": ["Number of cars", "Temperature", "Type of fruit", "Gender"], 
        "answer": "b"},
        {"id": 7, "question": "What is the purpose of regression analysis?", 
        "options": ["To find the mean", "To analyze relationships between variables", "To calculate probabilities", "To visualize data"], 
        "answer": "b"},
        {"id": 8, "question": "Which term describes the most frequent value in a dataset?", 
        "options": ["Mean", "Median", "Mode", "Variance"], 
        "answer": "c"},
        {"id": 9, "question": "What is the range of a dataset?", 
        "options": ["The average value", "The difference between the maximum and minimum values", "The middle value", "The variance"], 
        "answer": "b"},
        {"id": 10, "question": "What does correlation measure?", 
        "options": ["Causation between variables", "Strength and direction of a relationship between variables", "Average of variables", "Variation in data"], 
        "answer": "b"}
    ]

    cursor.close()
    return render_template('stat_exam.html', student_name=student_name, course_code=course_code, questions=questions)

# Define the function to generate HTML content for results
def generate_results_html(answers, correct_answers):
    results_html = ""
    for question_id, selected_option in answers.items():
        if question_id == "course_code":
            output = question_id
        else:
            question_number = question_id[1:]  # Extract question number (e.g., 'q1' -> '1')
            correct_answer = correct_answers.get(f'q{question_number}')
            is_correct = selected_option == correct_answer
            
            # Apply different styles based on correctness
            color = "green" if is_correct else "red"
            results_html += f'<p style="color:{color}">Question {question_number}: {"Correct" if is_correct else "Incorrect"}</p>'

    return results_html

@app.route('/submit_stat_exam/<int:course_code>', methods=['POST'])
def submit_stat_exam(course_code):
    cursor = mysql.connection.cursor()
    student_id = session.get('student_id')
    answers = request.form.to_dict()  # This will get all the form data as a dictionary
    
    # Define correct answers
    correct_answers = {
        "q1": "b",
        "q2": "b",
        "q3": "c",
        "q4": "b",
        "q5": "b",
        "q6": "b",
        "q7": "b",
        "q8": "c",
        "q9": "b",
        "q10": "b"
    }
    
    # Insert default marks for the student
    cursor.execute("INSERT INTO exams (course_code, student_id, q1_mark, q2_mark, q3_mark, q4_mark, q5_mark, q6_mark, q7_mark, q8_mark, q9_mark, q10_mark) VALUES (%s, %s, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)", 
                   (course_code, student_id))
    
    total_marks = 0
    # Logic to calculate marks and update exam table
    for i in range(1, 11):
        question_id = f'q{i}'
        selected_option = answers.get(question_id)
        if selected_option == correct_answers[question_id]:
            total_marks += 2
            cursor.execute(f"UPDATE exams SET q{i}_mark = 2 WHERE course_code = %s AND student_id = %s", (course_code, student_id))
        else:
            cursor.execute(f"UPDATE exams SET q{i}_mark = 0 WHERE course_code = %s AND student_id = %s", (course_code, student_id))
    
    # Update total marks
    cursor.execute("UPDATE exams SET total_mark = %s WHERE course_code = %s AND student_id = %s", (total_marks, course_code, student_id))
    cursor.execute("UPDATE enrollment_status SET total_point = total_point + %s WHERE course_code = %s AND student_id = %s", (total_marks, course_code, student_id))
    mysql.connection.commit()
    cursor.close()

    # Generate HTML for results to be displayed
    results_html = generate_results_html(answers, correct_answers)

    return jsonify({"total_points": total_marks, "results_html": results_html})

#=====================================cyber_security_exam_part===================================================================================================================

@app.route('/cyber_security_exam/<int:course_code>')
def cyber_security_exam(course_code):
    cursor = mysql.connection.cursor()

    # Fetch student information
    student_id = session.get('student_id')
    if not student_id:
        return redirect('/login')

    cursor.execute("SELECT name FROM students WHERE student_id = %s", (student_id,))
    student = cursor.fetchone()
    student_name = student[0]
    
   # Cyber Security Fundamentals questions
    questions = [
        {"id": 1, "question": "What is the main purpose of a firewall?", 
        "options": ["To detect viruses", "To block unauthorized access", "To encrypt data", "To monitor bandwidth"], 
        "answer": "b"},
        {"id": 2, "question": "Which of the following is an example of two-factor authentication?", 
        "options": ["Username and password", "Password and security question", "Password and OTP", "Biometric scan only"], 
        "answer": "c"},
        {"id": 3, "question": "What does the term 'phishing' refer to?", 
        "options": ["Hacking into a system", "Tricking someone into sharing sensitive information", "Scanning networks for vulnerabilities", "Encrypting files for ransom"], 
        "answer": "b"},
        {"id": 4, "question": "Which protocol is used to securely transfer data over the internet?", 
        "options": ["HTTP", "FTP", "HTTPS", "SMTP"], 
        "answer": "c"},
        {"id": 5, "question": "What is the role of encryption in cybersecurity?", 
        "options": ["To detect malware", "To hide data", "To ensure data confidentiality", "To block network traffic"], 
        "answer": "c"},
        {"id": 6, "question": "What is the primary purpose of a VPN?", 
        "options": ["To enhance internet speed", "To secure online communications", "To block advertisements", "To detect threats"], 
        "answer": "b"},
        {"id": 7, "question": "Which of the following is an example of malware?", 
        "options": ["Firewall", "Antivirus software", "Ransomware", "Encryption"], 
        "answer": "c"},
        {"id": 8, "question": "What is a 'zero-day vulnerability'?", 
        "options": ["A bug in software discovered after a patch", "A newly discovered vulnerability with no fix", "An outdated software feature", "A failed cybersecurity audit"], 
        "answer": "b"},
        {"id": 9, "question": "What does 'DoS' stand for in cybersecurity?", 
        "options": ["Data on Security", "Denial of Service", "Domain of Servers", "Deployment of Security"], 
        "answer": "b"},
        {"id": 10, "question": "Which of these is an example of social engineering?", 
        "options": ["Installing spyware", "Creating a strong password", "Impersonating someone to gain access", "Using a VPN for secure access"], 
        "answer": "c"}
    ]

    cursor.close()
    return render_template('cyber_security_exam.html', student_name=student_name, course_code=course_code, questions=questions)

# Define the function to generate HTML content for results
def generate_results_html(answers, correct_answers):
    results_html = ""
    for question_id, selected_option in answers.items():
        if question_id == "course_code":
            output = question_id
        else:
            question_number = question_id[1:]  # Extract question number (e.g., 'q1' -> '1')
            correct_answer = correct_answers.get(f'q{question_number}')
            is_correct = selected_option == correct_answer
            
            # Apply different styles based on correctness
            color = "green" if is_correct else "red"
            results_html += f'<p style="color:{color}">Question {question_number}: {"Correct" if is_correct else "Incorrect"}</p>'

    return results_html

@app.route('/submit_cyber_security_exam/<int:course_code>', methods=['POST'])
def submit_cyber_security_exam(course_code):
    cursor = mysql.connection.cursor()
    student_id = session.get('student_id')
    answers = request.form.to_dict()  # This will get all the form data as a dictionary
    
   # Define correct answers
    correct_answers = {
        "q1": "b",
        "q2": "c",
        "q3": "b",
        "q4": "c",
        "q5": "c",
        "q6": "b",
        "q7": "c",
        "q8": "b",
        "q9": "b",
        "q10": "c"
    }
    
    # Insert default marks for the student
    cursor.execute("INSERT INTO exams (course_code, student_id, q1_mark, q2_mark, q3_mark, q4_mark, q5_mark, q6_mark, q7_mark, q8_mark, q9_mark, q10_mark) VALUES (%s, %s, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)", 
                   (course_code, student_id))
    
    total_marks = 0
    # Logic to calculate marks and update exam table
    for i in range(1, 11):
        question_id = f'q{i}'
        selected_option = answers.get(question_id)
        if selected_option == correct_answers[question_id]:
            total_marks += 2
            cursor.execute(f"UPDATE exams SET q{i}_mark = 2 WHERE course_code = %s AND student_id = %s", (course_code, student_id))
        else:
            cursor.execute(f"UPDATE exams SET q{i}_mark = 0 WHERE course_code = %s AND student_id = %s", (course_code, student_id))
    
    # Update total marks
    cursor.execute("UPDATE exams SET total_mark = %s WHERE course_code = %s AND student_id = %s", (total_marks, course_code, student_id))
    cursor.execute("UPDATE enrollment_status SET total_point = total_point + %s WHERE course_code = %s AND student_id = %s", (total_marks, course_code, student_id))
    mysql.connection.commit()
    cursor.close()

    # Generate HTML for results to be displayed
    results_html = generate_results_html(answers, correct_answers)

    return jsonify({"total_points": total_marks, "results_html": results_html})


@app.route('/logout')
def logout():
    session.pop('student_name', None)  # Remove the student's name from the session
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True, port=2525) 
