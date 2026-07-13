from flask import Flask, request, jsonify, render_template, session, redirect, url_for
from flask_cors import CORS
from functools import wraps
from config import Config
from models import db, User, Semester, Course, Assessment, CalendarEvent, CourseOutline, Post, PostLike, PostComment, Attendance, CourseReview, Timetable
from ai_service import get_ai_response, analyze_performance, predict_grade, get_study_tips, extract_pdf_text, parse_assessments_from_pdf, ai_edit_assessments, ai_parse_calendar_events, ai_parse_pdf_calendar, ai_read_image
from course_catalog import UTP_PROGRAMS

app = Flask(__name__)
app.config.from_object(Config)
CORS(app)
db.init_app(app)

with app.app_context():
    # Ensure all tables exist
    db.create_all()
    # Add missing columns to existing tables (for upgrades)
    import sqlalchemy
    with db.engine.connect() as conn:
        try:
            conn.execute(sqlalchemy.text("SELECT is_admin FROM users LIMIT 1"))
        except Exception:
            conn.execute(sqlalchemy.text("ALTER TABLE users ADD COLUMN is_admin BOOLEAN DEFAULT 0"))
            conn.execute(sqlalchemy.text("ALTER TABLE users ADD COLUMN bio VARCHAR(200) DEFAULT ''"))
            conn.execute(sqlalchemy.text("ALTER TABLE users ADD COLUMN profile_pic TEXT"))
            conn.execute(sqlalchemy.text("ALTER TABLE users ADD COLUMN dark_mode BOOLEAN DEFAULT 0"))
            conn.execute(sqlalchemy.text("ALTER TABLE users ADD COLUMN target_cgpa FLOAT DEFAULT 3.5"))
            conn.commit()


# ============ AUTH HELPER ============

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'error': 'Login required'}), 401
        return f(*args, **kwargs)
    return decorated


def get_current_user():
    return User.query.get(session.get('user_id'))


# ============ PAGE ROUTES ============

@app.route('/')
def index():
    if 'user_id' not in session:
        return redirect(url_for('login_page'))
    return render_template('index.html')


@app.route('/login')
def login_page():
    return render_template('login.html')


@app.route('/calendar')
def calendar_page():
    if 'user_id' not in session:
        return redirect(url_for('login_page'))
    return render_template('calendar.html')


@app.route('/outlines')
def outlines_page():
    if 'user_id' not in session:
        return redirect(url_for('login_page'))
    return render_template('outlines.html')


@app.route('/feed')
def feed_page():
    if 'user_id' not in session:
        return redirect(url_for('login_page'))
    return render_template('feed.html')


@app.route('/admin')
def admin_page():
    if 'user_id' not in session:
        return redirect(url_for('login_page'))
    user = User.query.get(session['user_id'])
    if not user or not user.is_admin:
        return redirect(url_for('index'))
    return render_template('admin.html')


@app.route('/profile')
def profile_page():
    if 'user_id' not in session:
        return redirect(url_for('login_page'))
    return render_template('profile.html')


@app.route('/timetable')
def timetable_page():
    if 'user_id' not in session:
        return redirect(url_for('login_page'))
    return render_template('timetable.html')


@app.route('/reviews')
def reviews_page():
    if 'user_id' not in session:
        return redirect(url_for('login_page'))
    return render_template('reviews.html')


@app.route('/attendance')
def attendance_page():
    if 'user_id' not in session:
        return redirect(url_for('login_page'))
    return render_template('attendance.html')


# ============ AUTH ROUTES ============

@app.route('/api/auth/register', methods=['POST'])
def register():
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400

    required = ['username', 'password', 'full_name', 'program_id', 'current_semester']
    for field in required:
        if not data.get(field):
            return jsonify({'error': f'{field} is required'}), 400

    if data['program_id'] not in UTP_PROGRAMS:
        return jsonify({'error': 'Invalid programme'}), 400

    if User.query.filter_by(username=data['username']).first():
        return jsonify({'error': 'Username already taken'}), 400

    user = User(
        username=data['username'],
        full_name=data['full_name'],
        program_id=data['program_id'],
        current_semester=int(data['current_semester'])
    )
    user.set_password(data['password'])
    # Make 'iskandar' the admin
    if data['username'].lower() == 'iskandar':
        user.is_admin = True
    db.session.add(user)
    db.session.commit()

    # Auto-create semester and import courses
    sem_num = int(data['current_semester'])
    sem_name = f"Semester {sem_num}"
    program = UTP_PROGRAMS[data['program_id']]

    semester = Semester(
        name=sem_name,
        year=2025,
        user_id=user.id
    )
    db.session.add(semester)
    db.session.commit()

    # Import courses for current semester
    if sem_name in program['semesters']:
        for course_data in program['semesters'][sem_name]:
            course = Course(
                code=course_data['code'],
                name=course_data['name'],
                credit_hours=course_data['credits'],
                semester_id=semester.id
            )
            db.session.add(course)
        db.session.commit()

    session['user_id'] = user.id
    return jsonify({'message': 'Registered successfully', 'user': user.to_dict()}), 201


@app.route('/api/auth/login', methods=['POST'])
def login():
    data = request.get_json()
    if not data or not data.get('username') or not data.get('password'):
        return jsonify({'error': 'Username and password are required'}), 400

    user = User.query.filter_by(username=data['username']).first()
    if not user or not user.check_password(data['password']):
        return jsonify({'error': 'Invalid username or password'}), 401

    session['user_id'] = user.id
    return jsonify({'message': 'Logged in', 'user': user.to_dict()})


@app.route('/api/auth/logout', methods=['POST'])
def logout():
    session.pop('user_id', None)
    return jsonify({'message': 'Logged out'})


@app.route('/api/auth/me', methods=['GET'])
@login_required
def get_me():
    user = get_current_user()
    return jsonify(user.to_dict())


# ============ CATALOG ROUTES ============

@app.route('/api/catalog/programs', methods=['GET'])
def get_programs():
    programs = []
    for key, prog in UTP_PROGRAMS.items():
        programs.append({'id': key, 'name': prog['name']})
    return jsonify(programs)


@app.route('/api/catalog/programs/<program_id>/semesters', methods=['GET'])
def get_program_semesters(program_id):
    if program_id not in UTP_PROGRAMS:
        return jsonify({'error': 'Programme not found'}), 404
    program = UTP_PROGRAMS[program_id]
    return jsonify({
        'id': program_id,
        'name': program['name'],
        'semesters': program['semesters']
    })


@app.route('/api/catalog/import', methods=['POST'])
@login_required
def import_from_catalog():
    data = request.get_json()
    if not data or not data.get('program_id') or not data.get('semester_name') or not data.get('semester_id'):
        return jsonify({'error': 'program_id, semester_name, and semester_id are required'}), 400

    program_id = data['program_id']
    semester_name = data['semester_name']
    semester_id = data['semester_id']

    if program_id not in UTP_PROGRAMS:
        return jsonify({'error': 'Programme not found'}), 404

    program = UTP_PROGRAMS[program_id]
    if semester_name not in program['semesters']:
        return jsonify({'error': 'Semester not found in programme'}), 404

    semester = Semester.query.get_or_404(semester_id)
    courses_added = []

    for course_data in program['semesters'][semester_name]:
        existing = Course.query.filter_by(semester_id=semester_id, code=course_data['code']).first()
        if not existing:
            course = Course(
                code=course_data['code'],
                name=course_data['name'],
                credit_hours=course_data['credits'],
                semester_id=semester_id
            )
            db.session.add(course)
            courses_added.append(course_data)

    db.session.commit()
    return jsonify({'message': f'{len(courses_added)} courses imported', 'courses_added': courses_added}), 201


# ============ SEMESTER ROUTES ============

@app.route('/api/semesters', methods=['GET'])
@login_required
def get_semesters():
    user = get_current_user()
    semesters = Semester.query.filter_by(user_id=user.id).order_by(Semester.year.desc(), Semester.id.desc()).all()
    return jsonify([s.to_dict() for s in semesters])


@app.route('/api/semesters', methods=['POST'])
@login_required
def create_semester():
    user = get_current_user()
    data = request.get_json()
    if not data or not data.get('name') or not data.get('year'):
        return jsonify({'error': 'Name and year are required'}), 400

    semester = Semester(name=data['name'], year=data['year'], user_id=user.id)
    db.session.add(semester)
    db.session.commit()
    return jsonify(semester.to_dict()), 201


@app.route('/api/semesters/<int:semester_id>', methods=['DELETE'])
@login_required
def delete_semester(semester_id):
    semester = Semester.query.get_or_404(semester_id)
    db.session.delete(semester)
    db.session.commit()
    return jsonify({'message': 'Semester deleted'}), 200


# ============ COURSE ROUTES ============

@app.route('/api/semesters/<int:semester_id>/courses', methods=['GET'])
@login_required
def get_courses(semester_id):
    courses = Course.query.filter_by(semester_id=semester_id).all()
    return jsonify([c.to_dict() for c in courses])


@app.route('/api/semesters/<int:semester_id>/courses', methods=['POST'])
@login_required
def create_course(semester_id):
    Semester.query.get_or_404(semester_id)
    data = request.get_json()
    if not data or not data.get('code') or not data.get('name'):
        return jsonify({'error': 'Course code and name are required'}), 400

    course = Course(
        code=data['code'].upper(),
        name=data['name'],
        credit_hours=data.get('credit_hours', 3),
        semester_id=semester_id
    )
    db.session.add(course)
    db.session.commit()
    return jsonify(course.to_dict()), 201


@app.route('/api/courses/<int:course_id>', methods=['GET'])
@login_required
def get_course(course_id):
    course = Course.query.get_or_404(course_id)
    return jsonify(course.to_dict())


@app.route('/api/courses/<int:course_id>', methods=['PUT'])
@login_required
def update_course(course_id):
    course = Course.query.get_or_404(course_id)
    data = request.get_json()

    if 'code' in data:
        course.code = data['code'].upper()
    if 'name' in data:
        course.name = data['name']
    if 'credit_hours' in data:
        course.credit_hours = int(data['credit_hours'])

    db.session.commit()
    return jsonify(course.to_dict())


@app.route('/api/courses/<int:course_id>', methods=['DELETE'])
@login_required
def delete_course(course_id):
    course = Course.query.get_or_404(course_id)
    db.session.delete(course)
    db.session.commit()
    return jsonify({'message': 'Course deleted'}), 200


# ============ ASSESSMENT ROUTES ============

@app.route('/api/courses/<int:course_id>/assessments', methods=['POST'])
@login_required
def create_assessment(course_id):
    Course.query.get_or_404(course_id)
    data = request.get_json()

    if not data or not data.get('name') or not data.get('category'):
        return jsonify({'error': 'Assessment name and category are required'}), 400

    valid_categories = ['test', 'quiz', 'assignment', 'lab', 'midterm', 'final_exam', 'project', 'presentation', 'tutorial', 'other']
    if data['category'] not in valid_categories:
        return jsonify({'error': f'Invalid category. Must be one of: {valid_categories}'}), 400

    assessment = Assessment(
        name=data['name'],
        category=data['category'],
        marks_obtained=data.get('marks_obtained', 0),
        total_marks=data.get('total_marks', 100),
        weightage=data.get('weightage', 0),
        course_id=course_id
    )
    db.session.add(assessment)
    db.session.commit()
    return jsonify(assessment.to_dict()), 201


@app.route('/api/assessments/<int:assessment_id>', methods=['PUT'])
@login_required
def update_assessment(assessment_id):
    assessment = Assessment.query.get_or_404(assessment_id)
    data = request.get_json()

    if 'marks_obtained' in data:
        assessment.marks_obtained = data['marks_obtained']
    if 'total_marks' in data:
        assessment.total_marks = data['total_marks']
    if 'weightage' in data:
        assessment.weightage = data['weightage']
    if 'name' in data:
        assessment.name = data['name']
    if 'category' in data:
        assessment.category = data['category']

    db.session.commit()
    return jsonify(assessment.to_dict())


@app.route('/api/assessments/<int:assessment_id>', methods=['DELETE'])
@login_required
def delete_assessment(assessment_id):
    assessment = Assessment.query.get_or_404(assessment_id)
    db.session.delete(assessment)
    db.session.commit()
    return jsonify({'message': 'Assessment deleted'}), 200


# ============ CALCULATION ROUTES ============

@app.route('/api/semesters/<int:semester_id>/gpa', methods=['GET'])
@login_required
def calculate_gpa(semester_id):
    courses = Course.query.filter_by(semester_id=semester_id).all()
    if not courses:
        return jsonify({'gpa': 0, 'total_credits': 0, 'courses': []})

    total_points = 0
    total_credits = 0
    course_results = []

    for course in courses:
        points = course.grade_point * course.credit_hours
        total_points += points
        total_credits += course.credit_hours
        course_results.append({
            'code': course.code,
            'name': course.name,
            'credit_hours': course.credit_hours,
            'carry_mark': course.carry_mark,
            'final_exam_mark': course.final_exam_mark,
            'total_mark': course.total_mark,
            'grade': course.grade,
            'grade_point': course.grade_point
        })

    gpa = round(total_points / total_credits, 2) if total_credits > 0 else 0
    return jsonify({
        'gpa': gpa,
        'total_credits': total_credits,
        'total_points': round(total_points, 2),
        'courses': course_results
    })


# ============ CALENDAR ROUTES ============

@app.route('/api/calendar/events', methods=['GET'])
@login_required
def get_events():
    user = get_current_user()
    month = request.args.get('month', type=int)
    year = request.args.get('year', type=int)

    query = CalendarEvent.query.filter_by(user_id=user.id)
    if month and year:
        from sqlalchemy import extract
        query = query.filter(
            extract('month', CalendarEvent.date) == month,
            extract('year', CalendarEvent.date) == year
        )

    events = query.order_by(CalendarEvent.date).all()
    return jsonify([e.to_dict() for e in events])


@app.route('/api/calendar/events', methods=['POST'])
@login_required
def create_event():
    user = get_current_user()
    data = request.get_json()

    if not data or not data.get('title') or not data.get('date') or not data.get('event_type'):
        return jsonify({'error': 'title, date, and event_type are required'}), 400

    from datetime import date as date_type
    try:
        event_date = date_type.fromisoformat(data['date'])
    except ValueError:
        return jsonify({'error': 'Invalid date format. Use YYYY-MM-DD'}), 400

    event = CalendarEvent(
        title=data['title'],
        description=data.get('description', ''),
        event_type=data['event_type'],
        course_code=data.get('course_code', ''),
        date=event_date,
        time=data.get('time', ''),
        user_id=user.id
    )
    db.session.add(event)
    db.session.commit()
    return jsonify(event.to_dict()), 201


@app.route('/api/calendar/events/<int:event_id>', methods=['DELETE'])
@login_required
def delete_event(event_id):
    event = CalendarEvent.query.get_or_404(event_id)
    db.session.delete(event)
    db.session.commit()
    return jsonify({'message': 'Event deleted'}), 200


@app.route('/api/calendar/import-ics', methods=['POST'])
@login_required
def import_ics():
    """Import events from .ics calendar file."""
    user = get_current_user()

    if 'ics' not in request.files:
        return jsonify({'error': 'No .ics file uploaded'}), 400

    ics_file = request.files['ics']
    if not ics_file.filename.lower().endswith('.ics'):
        return jsonify({'error': 'File must be .ics'}), 400

    try:
        content = ics_file.read().decode('utf-8')
        from datetime import date as date_type, datetime as dt_type
        import re as re_mod

        events_added = 0
        # Parse VEVENT blocks
        vevent_pattern = r'BEGIN:VEVENT(.*?)END:VEVENT'
        vevents = re_mod.findall(vevent_pattern, content, re_mod.DOTALL)

        for vevent in vevents:
            # Extract fields
            summary_match = re_mod.search(r'SUMMARY:(.*?)(?:\r?\n)', vevent)
            dtstart_match = re_mod.search(r'DTSTART[^:]*:(.*?)(?:\r?\n)', vevent)
            description_match = re_mod.search(r'DESCRIPTION:(.*?)(?:\r?\n)', vevent)

            if not summary_match or not dtstart_match:
                continue

            title = summary_match.group(1).strip()
            dtstart_raw = dtstart_match.group(1).strip()
            description = description_match.group(1).strip() if description_match else ''

            # Parse date (handles YYYYMMDD and YYYYMMDDTHHmmss formats)
            event_date = None
            event_time = ''
            try:
                if 'T' in dtstart_raw:
                    dt = dt_type.strptime(dtstart_raw[:15], '%Y%m%dT%H%M%S')
                    event_date = dt.date()
                    event_time = dt.strftime('%H:%M')
                else:
                    event_date = date_type(int(dtstart_raw[:4]), int(dtstart_raw[4:6]), int(dtstart_raw[6:8]))
            except (ValueError, IndexError):
                continue

            # Determine event type from title
            title_lower = title.lower()
            event_type = 'other'
            if 'test' in title_lower or 'exam' in title_lower:
                event_type = 'test'
            elif 'quiz' in title_lower:
                event_type = 'quiz'
            elif 'assignment' in title_lower or 'due' in title_lower:
                event_type = 'assignment'
            elif 'lab' in title_lower:
                event_type = 'lab'
            elif 'final' in title_lower:
                event_type = 'exam'

            # Extract course code if present
            course_code = ''
            code_match = re_mod.search(r'[A-Z]{2,3}\d{4}', title)
            if code_match:
                course_code = code_match.group(0)

            event = CalendarEvent(
                title=title,
                description=description,
                event_type=event_type,
                course_code=course_code,
                date=event_date,
                time=event_time,
                user_id=user.id
            )
            db.session.add(event)
            events_added += 1

        db.session.commit()
        return jsonify({'message': f'{events_added} events imported from .ics file'})

    except Exception as e:
        return jsonify({'error': f'Error parsing .ics: {str(e)}'}), 500


# ============ ADMIN ROUTES ============

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'error': 'Login required'}), 401
        user = User.query.get(session['user_id'])
        if not user or not user.is_admin:
            return jsonify({'error': 'Admin access required'}), 403
        return f(*args, **kwargs)
    return decorated


@app.route('/api/admin/users', methods=['GET'])
@admin_required
def admin_get_users():
    users = User.query.order_by(User.created_at.desc()).all()
    return jsonify([u.to_dict() for u in users])


@app.route('/api/admin/users/<int:user_id>', methods=['DELETE'])
@admin_required
def admin_delete_user(user_id):
    user = User.query.get_or_404(user_id)
    if user.is_admin:
        return jsonify({'error': 'Cannot delete admin'}), 400
    db.session.delete(user)
    db.session.commit()
    return jsonify({'message': f'User {user.username} deleted'})


@app.route('/api/admin/posts', methods=['GET'])
@admin_required
def admin_get_posts():
    posts = Post.query.order_by(Post.created_at.desc()).all()
    return jsonify([p.to_dict() for p in posts])


@app.route('/api/admin/posts/<int:post_id>', methods=['DELETE'])
@admin_required
def admin_delete_post(post_id):
    post = Post.query.get_or_404(post_id)
    db.session.delete(post)
    db.session.commit()
    return jsonify({'message': 'Post deleted'})


@app.route('/api/admin/stats', methods=['GET'])
@admin_required
def admin_stats():
    return jsonify({
        'total_users': User.query.count(),
        'total_posts': Post.query.count(),
        'total_courses': Course.query.count(),
        'total_events': CalendarEvent.query.count()
    })


# ============ FEED/POSTS ROUTES ============

@app.route('/api/posts', methods=['GET'])
@login_required
def get_posts():
    user = get_current_user()
    posts = Post.query.order_by(Post.created_at.desc()).limit(50).all()
    return jsonify([p.to_dict(current_user_id=user.id) for p in posts])


@app.route('/api/posts', methods=['POST'])
@login_required
def create_post():
    user = get_current_user()

    if 'image' not in request.files:
        return jsonify({'error': 'Image is required'}), 400

    image_file = request.files['image']
    caption = request.form.get('caption', '')
    post_type = request.form.get('post_type', 'general')

    import base64
    image_data = base64.b64encode(image_file.read()).decode('utf-8')
    ext = image_file.filename.rsplit('.', 1)[-1].lower() if '.' in image_file.filename else 'jpeg'
    mime = f"image/{ext}" if ext in ['png', 'gif', 'webp'] else "image/jpeg"
    image_b64 = f"data:{mime};base64,{image_data}"

    post = Post(
        caption=caption,
        image_data=image_b64,
        post_type=post_type,
        user_id=user.id
    )
    db.session.add(post)
    db.session.commit()
    return jsonify(post.to_dict(current_user_id=user.id)), 201


@app.route('/api/posts/<int:post_id>', methods=['DELETE'])
@login_required
def delete_post(post_id):
    user = get_current_user()
    post = Post.query.get_or_404(post_id)
    if post.user_id != user.id:
        return jsonify({'error': 'Not your post'}), 403
    db.session.delete(post)
    db.session.commit()
    return jsonify({'message': 'Post deleted'})


@app.route('/api/posts/<int:post_id>/like', methods=['POST'])
@login_required
def toggle_like(post_id):
    user = get_current_user()
    Post.query.get_or_404(post_id)

    existing = PostLike.query.filter_by(post_id=post_id, user_id=user.id).first()
    if existing:
        db.session.delete(existing)
        db.session.commit()
        return jsonify({'liked': False})
    else:
        like = PostLike(post_id=post_id, user_id=user.id)
        db.session.add(like)
        db.session.commit()
        return jsonify({'liked': True})


@app.route('/api/posts/<int:post_id>/comments', methods=['POST'])
@login_required
def add_comment(post_id):
    user = get_current_user()
    Post.query.get_or_404(post_id)
    data = request.get_json()

    if not data or not data.get('text'):
        return jsonify({'error': 'Comment text is required'}), 400

    comment = PostComment(text=data['text'], post_id=post_id, user_id=user.id)
    db.session.add(comment)
    db.session.commit()
    return jsonify(comment.to_dict()), 201


# ============ PROFILE ROUTES ============

@app.route('/api/profile', methods=['GET'])
@login_required
def get_profile():
    user = get_current_user()
    return jsonify(user.to_dict())


@app.route('/api/profile', methods=['PUT'])
@login_required
def update_profile():
    user = get_current_user()
    data = request.get_json()
    if 'full_name' in data:
        user.full_name = data['full_name']
    if 'bio' in data:
        user.bio = data['bio']
    if 'dark_mode' in data:
        user.dark_mode = data['dark_mode']
    if 'target_cgpa' in data:
        user.target_cgpa = float(data['target_cgpa'])
    if 'profile_pic' in data:
        user.profile_pic = data['profile_pic']
    db.session.commit()
    return jsonify(user.to_dict())


# ============ CGPA ROUTES ============

@app.route('/api/cgpa', methods=['GET'])
@login_required
def calculate_cgpa():
    """Calculate cumulative GPA across all semesters."""
    user = get_current_user()
    semesters = Semester.query.filter_by(user_id=user.id).all()

    total_points = 0
    total_credits = 0
    semester_gpas = []

    for sem in semesters:
        sem_points = 0
        sem_credits = 0
        for course in sem.courses:
            points = course.grade_point * course.credit_hours
            sem_points += points
            sem_credits += course.credit_hours
        sem_gpa = round(sem_points / sem_credits, 2) if sem_credits > 0 else 0
        total_points += sem_points
        total_credits += sem_credits
        semester_gpas.append({'name': sem.name, 'gpa': sem_gpa, 'credits': sem_credits})

    cgpa = round(total_points / total_credits, 2) if total_credits > 0 else 0
    return jsonify({
        'cgpa': cgpa,
        'total_credits': total_credits,
        'semesters': semester_gpas,
        'target_cgpa': user.target_cgpa
    })


@app.route('/api/target-gpa', methods=['POST'])
@login_required
def target_gpa_calculator():
    """Calculate what GPA needed this semester to reach target CGPA."""
    user = get_current_user()
    data = request.get_json() or {}
    target = float(data.get('target_cgpa', user.target_cgpa or 3.5))

    semesters = Semester.query.filter_by(user_id=user.id).all()
    total_points = 0
    total_credits = 0
    for sem in semesters:
        for course in sem.courses:
            total_points += course.grade_point * course.credit_hours
            total_credits += course.credit_hours

    # Estimate next semester credits (assume 15)
    next_credits = int(data.get('next_credits', 15))
    needed_points = (target * (total_credits + next_credits)) - total_points
    needed_gpa = round(needed_points / next_credits, 2) if next_credits > 0 else 0

    return jsonify({
        'current_cgpa': round(total_points / total_credits, 2) if total_credits > 0 else 0,
        'target_cgpa': target,
        'credits_completed': total_credits,
        'next_sem_credits': next_credits,
        'needed_gpa': needed_gpa,
        'achievable': needed_gpa <= 4.0
    })


# ============ ATTENDANCE ROUTES ============

@app.route('/api/attendance', methods=['GET'])
@login_required
def get_attendance():
    user = get_current_user()
    records = Attendance.query.filter_by(user_id=user.id).order_by(Attendance.date.desc()).all()
    return jsonify([a.to_dict() for a in records])


@app.route('/api/attendance', methods=['POST'])
@login_required
def add_attendance():
    user = get_current_user()
    data = request.get_json()
    if not data or not data.get('course_code') or not data.get('date'):
        return jsonify({'error': 'course_code and date required'}), 400

    from datetime import date as date_type
    record = Attendance(
        course_code=data['course_code'],
        date=date_type.fromisoformat(data['date']),
        status=data.get('status', 'present'),
        user_id=user.id
    )
    db.session.add(record)
    db.session.commit()
    return jsonify(record.to_dict()), 201


@app.route('/api/attendance/summary', methods=['GET'])
@login_required
def attendance_summary():
    user = get_current_user()
    records = Attendance.query.filter_by(user_id=user.id).all()
    summary = {}
    for r in records:
        if r.course_code not in summary:
            summary[r.course_code] = {'present': 0, 'absent': 0, 'late': 0, 'total': 0}
        summary[r.course_code][r.status] += 1
        summary[r.course_code]['total'] += 1
    # Calculate percentage
    for code in summary:
        total = summary[code]['total']
        summary[code]['percentage'] = round((summary[code]['present'] + summary[code]['late']) / total * 100, 1) if total > 0 else 0
    return jsonify(summary)


# ============ TIMETABLE ROUTES ============

@app.route('/api/timetable', methods=['GET'])
@login_required
def get_timetable():
    user = get_current_user()
    entries = Timetable.query.filter_by(user_id=user.id).all()
    return jsonify([t.to_dict() for t in entries])


@app.route('/api/timetable', methods=['POST'])
@login_required
def add_timetable():
    user = get_current_user()
    data = request.get_json()
    if not data or not data.get('course_code') or not data.get('day') or not data.get('start_time'):
        return jsonify({'error': 'course_code, day, and start_time required'}), 400

    entry = Timetable(
        course_code=data['course_code'],
        course_name=data.get('course_name', ''),
        day=data['day'],
        start_time=data['start_time'],
        end_time=data.get('end_time', ''),
        venue=data.get('venue', ''),
        class_type=data.get('class_type', 'lecture'),
        user_id=user.id
    )
    db.session.add(entry)
    db.session.commit()
    return jsonify(entry.to_dict()), 201


@app.route('/api/timetable/<int:entry_id>', methods=['DELETE'])
@login_required
def delete_timetable(entry_id):
    entry = Timetable.query.get_or_404(entry_id)
    db.session.delete(entry)
    db.session.commit()
    return jsonify({'message': 'Deleted'})


@app.route('/api/timetable/import-ics', methods=['POST'])
@login_required
def import_timetable_ics():
    """Import timetable from .ics file (recurring weekly classes)."""
    user = get_current_user()

    if 'ics' not in request.files:
        return jsonify({'error': 'No .ics file uploaded'}), 400

    ics_file = request.files['ics']
    if not ics_file.filename.lower().endswith('.ics'):
        return jsonify({'error': 'File must be .ics'}), 400

    try:
        content = ics_file.read().decode('utf-8')
        from datetime import datetime as dt_type
        import re as re_mod

        entries_added = 0
        day_names = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']

        vevent_pattern = r'BEGIN:VEVENT(.*?)END:VEVENT'
        vevents = re_mod.findall(vevent_pattern, content, re_mod.DOTALL)

        for vevent in vevents:
            summary_match = re_mod.search(r'SUMMARY:(.*?)(?:\r?\n)', vevent)
            dtstart_match = re_mod.search(r'DTSTART[^:]*:(.*?)(?:\r?\n)', vevent)
            dtend_match = re_mod.search(r'DTEND[^:]*:(.*?)(?:\r?\n)', vevent)
            location_match = re_mod.search(r'LOCATION:(.*?)(?:\r?\n)', vevent)

            if not summary_match or not dtstart_match:
                continue

            title = summary_match.group(1).strip()
            dtstart_raw = dtstart_match.group(1).strip()
            location = location_match.group(1).strip() if location_match else ''

            # Parse datetime
            start_time = ''
            end_time = ''
            day = ''
            try:
                if 'T' in dtstart_raw:
                    dt = dt_type.strptime(dtstart_raw[:15], '%Y%m%dT%H%M%S')
                    day = day_names[dt.weekday()]
                    start_time = dt.strftime('%H:%M')
                else:
                    dt = dt_type.strptime(dtstart_raw[:8], '%Y%m%d')
                    day = day_names[dt.weekday()]
            except (ValueError, IndexError):
                continue

            if dtend_match:
                try:
                    dtend_raw = dtend_match.group(1).strip()
                    if 'T' in dtend_raw:
                        dt_end = dt_type.strptime(dtend_raw[:15], '%Y%m%dT%H%M%S')
                        end_time = dt_end.strftime('%H:%M')
                except (ValueError, IndexError):
                    pass

            # Extract course code from title
            course_code = ''
            code_match = re_mod.search(r'[A-Z]{2,3}\d{4}', title)
            if code_match:
                course_code = code_match.group(0)

            # Determine class type
            title_lower = title.lower()
            class_type = 'lecture'
            if 'tutorial' in title_lower or 'tut' in title_lower:
                class_type = 'tutorial'
            elif 'lab' in title_lower or 'practical' in title_lower:
                class_type = 'lab'

            # Check if already exists (avoid duplicates)
            existing = Timetable.query.filter_by(
                user_id=user.id, course_code=course_code or title[:10],
                day=day, start_time=start_time
            ).first()
            if existing:
                continue

            entry = Timetable(
                course_code=course_code or title[:10],
                course_name=title,
                day=day,
                start_time=start_time,
                end_time=end_time,
                venue=location,
                class_type=class_type,
                user_id=user.id
            )
            db.session.add(entry)
            entries_added += 1

        db.session.commit()
        return jsonify({'message': f'{entries_added} classes imported to timetable'})

    except Exception as e:
        return jsonify({'error': f'Error parsing .ics: {str(e)}'}), 500


# ============ COURSE REVIEWS ROUTES ============

@app.route('/api/reviews', methods=['GET'])
def get_reviews():
    reviews = CourseReview.query.order_by(CourseReview.created_at.desc()).all()
    return jsonify([r.to_dict() for r in reviews])


@app.route('/api/reviews', methods=['POST'])
@login_required
def add_review():
    user = get_current_user()
    data = request.get_json()
    if not data or not data.get('course_code') or not data.get('rating'):
        return jsonify({'error': 'course_code and rating required'}), 400

    review = CourseReview(
        course_code=data['course_code'],
        course_name=data.get('course_name', ''),
        rating=int(data['rating']),
        difficulty=int(data.get('difficulty', 3)),
        review_text=data.get('review_text', ''),
        lecturer=data.get('lecturer', ''),
        user_id=user.id
    )
    db.session.add(review)
    db.session.commit()
    return jsonify(review.to_dict()), 201


# ============ LEADERBOARD ROUTES ============

@app.route('/api/leaderboard', methods=['GET'])
@login_required
def get_leaderboard():
    """Anonymous GPA leaderboard."""
    users = User.query.all()
    entries = []
    for u in users:
        semesters = Semester.query.filter_by(user_id=u.id).all()
        total_points = 0
        total_credits = 0
        for sem in semesters:
            for course in sem.courses:
                total_points += course.grade_point * course.credit_hours
                total_credits += course.credit_hours
        cgpa = round(total_points / total_credits, 2) if total_credits > 0 else 0
        if total_credits > 0:
            entries.append({
                'name': u.full_name[:3] + '***',  # Anonymous
                'program': u.program_id.upper(),
                'semester': u.current_semester,
                'cgpa': cgpa,
                'is_me': u.id == session.get('user_id')
            })
    entries.sort(key=lambda x: x['cgpa'], reverse=True)
    for i, e in enumerate(entries):
        e['rank'] = i + 1
    return jsonify(entries)


# ============ OUTLINE ROUTES ============

@app.route('/api/outlines', methods=['GET'])
@login_required
def get_outlines():
    user = get_current_user()
    outlines = CourseOutline.query.filter_by(user_id=user.id).order_by(CourseOutline.created_at.desc()).all()
    return jsonify([o.to_dict() for o in outlines])


@app.route('/api/outlines', methods=['POST'])
@login_required
def upload_outline():
    user = get_current_user()

    course_code = request.form.get('course_code', '').strip()
    course_name = request.form.get('course_name', '').strip()

    if not course_code or not course_name:
        return jsonify({'error': 'course_code and course_name are required'}), 400

    extracted_text = ''
    filename = ''

    try:
        if 'image' in request.files:
            # Handle image upload — use AI vision to read it
            image_file = request.files['image']
            filename = image_file.filename
            image_bytes = image_file.read()

            result = ai_read_image(image_bytes, f"Read and extract all text content from this course outline image for {course_code} ({course_name}). Return all the text you can see.")
            if result.get('success'):
                extracted_text = result.get('raw_text', '') or result.get('summary', '')
            if not extracted_text:
                return jsonify({'error': 'Could not read text from image. Try a clearer photo.'}), 400

        elif 'pdf' in request.files:
            # Handle PDF upload
            pdf_file = request.files['pdf']
            if not pdf_file.filename.lower().endswith('.pdf'):
                return jsonify({'error': 'File must be a PDF'}), 400
            filename = pdf_file.filename
            extracted_text = extract_pdf_text(pdf_file)
            if not extracted_text.strip():
                return jsonify({'error': 'Could not extract text from PDF. It may be image-based.'}), 400
        else:
            return jsonify({'error': 'No file uploaded'}), 400

        # Delete existing outline for this course (replace)
        CourseOutline.query.filter_by(user_id=user.id, course_code=course_code).delete()

        outline = CourseOutline(
            course_code=course_code,
            course_name=course_name,
            filename=filename,
            pdf_text=extracted_text,
            user_id=user.id
        )
        db.session.add(outline)
        db.session.commit()

        return jsonify({'message': f'Outline saved for {course_code}', 'outline': outline.to_dict()}), 201
    except Exception as e:
        return jsonify({'error': f'Error processing file: {str(e)}'}), 500


@app.route('/api/outlines/<int:outline_id>', methods=['DELETE'])
@login_required
def delete_outline(outline_id):
    outline = CourseOutline.query.get_or_404(outline_id)
    db.session.delete(outline)
    db.session.commit()
    return jsonify({'message': 'Outline deleted'})


@app.route('/api/outlines/<int:outline_id>/text', methods=['GET'])
@login_required
def get_outline_text(outline_id):
    outline = CourseOutline.query.get_or_404(outline_id)
    return jsonify({'course_code': outline.course_code, 'text': outline.pdf_text})


# ============ AI ROUTES ============

@app.route('/api/ai/chat', methods=['POST'])
@login_required
def ai_chat():
    user = get_current_user()
    data = request.get_json()
    if not data or not data.get('message'):
        return jsonify({'error': 'Message is required'}), 400

    # Build context from semester + course outlines
    context = ""
    if data.get('semester_id'):
        courses = Course.query.filter_by(semester_id=data['semester_id']).all()
        if courses:
            context += "Current semester courses and marks:\n"
            for c in courses:
                context += f"- {c.code} {c.name}: Carry={c.carry_mark}%, Total={c.total_mark}%, Grade={c.grade}\n"
                if c.assessments:
                    for a in c.assessments:
                        context += f"    {a.name} ({a.category}): {a.marks_obtained}/{a.total_marks}, weightage={a.weightage}%\n"

    # Include full course outlines so AI can reference them directly
    outlines = CourseOutline.query.filter_by(user_id=user.id).all()
    if outlines:
        context += "\n\n=== SAVED COURSE OUTLINES (uploaded by student) ===\n"
        context += "You already have these PDFs. Do NOT ask the student to share them again.\n"
        for o in outlines:
            context += f"\n--- {o.course_code} ({o.course_name}) [file: {o.filename}] ---\n"
            context += o.pdf_text[:3000] + "\n"

    result = get_ai_response(data['message'], context if context else None)
    return jsonify(result)


@app.route('/api/ai/analyze/<int:semester_id>', methods=['GET'])
@login_required
def ai_analyze(semester_id):
    courses = Course.query.filter_by(semester_id=semester_id).all()
    if not courses:
        return jsonify({'error': 'No courses found for this semester'}), 404

    courses_data = [c.to_dict() for c in courses]
    result = analyze_performance(courses_data)
    return jsonify(result)


@app.route('/api/ai/predict/<int:course_id>', methods=['POST'])
@login_required
def ai_predict(course_id):
    course = Course.query.get_or_404(course_id)
    data = request.get_json() or {}
    target_grade = data.get('target_grade')
    result = predict_grade(course.to_dict(), target_grade)
    return jsonify(result)


@app.route('/api/ai/tips/<int:course_id>', methods=['GET'])
@login_required
def ai_tips(course_id):
    course = Course.query.get_or_404(course_id)
    result = get_study_tips(course.to_dict())
    return jsonify(result)


@app.route('/api/ai/read-image/<int:course_id>', methods=['POST'])
@login_required
def ai_image_read(course_id):
    """Upload an image (test paper, grade sheet) and AI reads the marks."""
    course = Course.query.get_or_404(course_id)

    if 'image' not in request.files:
        return jsonify({'error': 'No image file uploaded'}), 400

    image_file = request.files['image']
    allowed_ext = ['.png', '.jpg', '.jpeg', '.webp', '.gif', '.bmp']
    if not any(image_file.filename.lower().endswith(ext) for ext in allowed_ext):
        return jsonify({'error': 'File must be an image (PNG, JPG, WEBP)'}), 400

    instruction = request.form.get('instruction', f'Extract all marks and grades for course {course.code} ({course.name}) from this image')

    try:
        image_bytes = image_file.read()
        result = ai_read_image(image_bytes, instruction)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': f'Error processing image: {str(e)}'}), 500


@app.route('/api/ai/pdf-extract/<int:course_id>', methods=['POST'])
@login_required
def ai_pdf_extract(course_id):
    """Upload a PDF (course outline/syllabus) and AI extracts assessments."""
    course = Course.query.get_or_404(course_id)

    if 'pdf' not in request.files:
        return jsonify({'error': 'No PDF file uploaded'}), 400

    pdf_file = request.files['pdf']
    if not pdf_file.filename.lower().endswith('.pdf'):
        return jsonify({'error': 'File must be a PDF'}), 400

    try:
        pdf_text = extract_pdf_text(pdf_file)
        if not pdf_text.strip():
            return jsonify({'error': 'Could not extract text from PDF. It may be image-based.'}), 400

        result = parse_assessments_from_pdf(pdf_text, course.code)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': f'Error processing PDF: {str(e)}'}), 500


@app.route('/api/ai/apply-assessments/<int:course_id>', methods=['POST'])
@login_required
def ai_apply_assessments(course_id):
    """Apply AI-extracted assessments to a course (replaces existing)."""
    course = Course.query.get_or_404(course_id)
    data = request.get_json()

    if not data or not data.get('assessments'):
        return jsonify({'error': 'assessments array is required'}), 400

    # Delete existing assessments
    Assessment.query.filter_by(course_id=course_id).delete()

    # Add new ones
    valid_categories = ['test', 'quiz', 'assignment', 'lab', 'midterm', 'final_exam', 'project', 'presentation', 'tutorial', 'other']
    for a in data['assessments']:
        cat = a.get('category', 'other')
        if cat not in valid_categories:
            cat = 'other'
        assessment = Assessment(
            name=a['name'],
            category=cat,
            marks_obtained=float(a.get('marks_obtained', 0)),
            total_marks=float(a.get('total_marks', 100)),
            weightage=float(a.get('weightage', 0)),
            course_id=course_id
        )
        db.session.add(assessment)

    db.session.commit()
    return jsonify({'message': f'{len(data["assessments"])} assessments applied', 'course': course.to_dict()})


@app.route('/api/ai/edit-assessments/<int:course_id>', methods=['POST'])
@login_required
def ai_edit_assessments_route(course_id):
    """Use AI to edit assessments via natural language instruction."""
    course = Course.query.get_or_404(course_id)
    data = request.get_json()

    if not data or not data.get('instruction'):
        return jsonify({'error': 'instruction is required'}), 400

    result = ai_edit_assessments(course.to_dict(), data['instruction'])
    return jsonify(result)


@app.route('/api/ai/calendar-edit', methods=['POST'])
@login_required
def ai_calendar_edit():
    """Use AI to add/edit/delete calendar events via natural language."""
    user = get_current_user()
    data = request.get_json()

    if not data or not data.get('instruction'):
        return jsonify({'error': 'instruction is required'}), 400

    # Get current events for context
    existing_events = [e.to_dict() for e in CalendarEvent.query.filter_by(user_id=user.id).order_by(CalendarEvent.date).all()]

    # Get courses for context
    semesters = Semester.query.filter_by(user_id=user.id).all()
    courses = []
    for sem in semesters:
        for c in sem.courses:
            courses.append({'code': c.code, 'name': c.name})

    result = ai_parse_calendar_events(data['instruction'], existing_events, courses)
    return jsonify(result)


@app.route('/api/ai/calendar-apply', methods=['POST'])
@login_required
def ai_calendar_apply():
    """Apply AI-generated calendar events (add/delete)."""
    user = get_current_user()
    data = request.get_json()

    if not data or not data.get('events'):
        return jsonify({'error': 'events array is required'}), 400

    from datetime import date as date_type
    added = 0
    deleted = 0

    for evt in data['events']:
        action = evt.get('action', 'add')

        if action == 'delete':
            # Find and delete matching event
            existing = CalendarEvent.query.filter_by(
                user_id=user.id,
                title=evt['title'],
                date=date_type.fromisoformat(evt['date'])
            ).first()
            if existing:
                db.session.delete(existing)
                deleted += 1
        else:
            # Add new event
            try:
                event_date = date_type.fromisoformat(evt['date'])
            except (ValueError, KeyError):
                continue

            event = CalendarEvent(
                title=evt['title'],
                description=evt.get('description', ''),
                event_type=evt.get('event_type', 'other'),
                course_code=evt.get('course_code', ''),
                date=event_date,
                time=evt.get('time', ''),
                user_id=user.id
            )
            db.session.add(event)
            added += 1

    db.session.commit()
    return jsonify({'message': f'{added} events added, {deleted} events deleted'})


@app.route('/api/ai/calendar-pdf', methods=['POST'])
@login_required
def ai_calendar_pdf():
    """Upload a PDF (schedule/timetable) and AI extracts calendar events."""
    user = get_current_user()

    if 'pdf' not in request.files:
        return jsonify({'error': 'No PDF file uploaded'}), 400

    pdf_file = request.files['pdf']
    if not pdf_file.filename.lower().endswith('.pdf'):
        return jsonify({'error': 'File must be a PDF'}), 400

    # Get course code if user selected one
    selected_course_code = request.form.get('course_code', '')

    try:
        pdf_text = extract_pdf_text(pdf_file)
        if not pdf_text.strip():
            return jsonify({'error': 'Could not extract text from PDF.'}), 400

        # Get courses for context
        semesters = Semester.query.filter_by(user_id=user.id).all()
        courses = []
        for sem in semesters:
            for c in sem.courses:
                courses.append({'code': c.code, 'name': c.name})

        result = ai_parse_pdf_calendar(pdf_text, courses, selected_course_code)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': f'Error processing PDF: {str(e)}'}), 500


if __name__ == '__main__':
    app.run(debug=True, port=5000)
