from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()


class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    full_name = db.Column(db.String(100), nullable=False)
    program_id = db.Column(db.String(20), nullable=False)
    current_semester = db.Column(db.Integer, nullable=False, default=1)
    is_admin = db.Column(db.Boolean, nullable=False, default=False)
    bio = db.Column(db.String(200), nullable=True, default='')
    profile_pic = db.Column(db.Text, nullable=True)  # base64
    dark_mode = db.Column(db.Boolean, nullable=False, default=False)
    target_cgpa = db.Column(db.Float, nullable=True, default=3.5)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    semesters = db.relationship('Semester', backref='user', lazy=True, cascade='all, delete-orphan')
    events = db.relationship('CalendarEvent', backref='user', lazy=True, cascade='all, delete-orphan')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'full_name': self.full_name,
            'program_id': self.program_id,
            'current_semester': self.current_semester,
            'is_admin': self.is_admin,
            'bio': self.bio or '',
            'profile_pic': self.profile_pic,
            'dark_mode': self.dark_mode,
            'target_cgpa': self.target_cgpa,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class Semester(db.Model):
    __tablename__ = 'semesters'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    year = db.Column(db.Integer, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    courses = db.relationship('Course', backref='semester', lazy=True, cascade='all, delete-orphan')

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'year': self.year,
            'courses': [c.to_dict() for c in self.courses]
        }


class Course(db.Model):
    __tablename__ = 'courses'

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(20), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    credit_hours = db.Column(db.Integer, nullable=False, default=3)
    semester_id = db.Column(db.Integer, db.ForeignKey('semesters.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    assessments = db.relationship('Assessment', backref='course', lazy=True, cascade='all, delete-orphan')

    @property
    def carry_mark(self):
        """Calculate total carry mark (all assessments excluding final exam)."""
        total = 0
        for a in self.assessments:
            if a.category != 'final_exam':
                total += a.weighted_score
        return round(total, 2)

    @property
    def final_exam_mark(self):
        """Get final exam mark."""
        for a in self.assessments:
            if a.category == 'final_exam':
                return round(a.weighted_score, 2)
        return 0

    @property
    def total_mark(self):
        """Calculate total mark (carry mark + final exam)."""
        return round(self.carry_mark + self.final_exam_mark, 2)

    @property
    def grade(self):
        """Determine grade based on total mark (UTP grading scale)."""
        total = self.total_mark
        if total >= 85:
            return 'A'
        elif total >= 80:
            return 'A-'
        elif total >= 75:
            return 'B+'
        elif total >= 65:
            return 'B'
        elif total >= 55:
            return 'C+'
        elif total >= 50:
            return 'C'
        elif total >= 45:
            return 'D+'
        elif total >= 40:
            return 'D'
        else:
            return 'F'

    @property
    def grade_point(self):
        """Get grade point value (UTP 4.0 scale)."""
        grade_map = {
            'A': 4.00, 'A-': 3.75,
            'B+': 3.50, 'B': 3.00,
            'C+': 2.50, 'C': 2.00,
            'D+': 1.50, 'D': 1.00, 'F': 0.00
        }
        return grade_map.get(self.grade, 0.00)

    def to_dict(self):
        return {
            'id': self.id,
            'code': self.code,
            'name': self.name,
            'credit_hours': self.credit_hours,
            'semester_id': self.semester_id,
            'assessments': [a.to_dict() for a in self.assessments],
            'carry_mark': self.carry_mark,
            'final_exam_mark': self.final_exam_mark,
            'total_mark': self.total_mark,
            'grade': self.grade,
            'grade_point': self.grade_point
        }


class Assessment(db.Model):
    __tablename__ = 'assessments'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    category = db.Column(db.String(30), nullable=False)
    marks_obtained = db.Column(db.Float, nullable=False, default=0)
    total_marks = db.Column(db.Float, nullable=False, default=100)
    weightage = db.Column(db.Float, nullable=False, default=0)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    @property
    def percentage_score(self):
        if self.total_marks == 0:
            return 0
        return (self.marks_obtained / self.total_marks) * 100

    @property
    def weighted_score(self):
        if self.total_marks == 0:
            return 0
        return (self.marks_obtained / self.total_marks) * self.weightage

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'category': self.category,
            'marks_obtained': self.marks_obtained,
            'total_marks': self.total_marks,
            'weightage': self.weightage,
            'percentage_score': round(self.percentage_score, 2),
            'weighted_score': round(self.weighted_score, 2),
            'course_id': self.course_id
        }


class CalendarEvent(db.Model):
    __tablename__ = 'calendar_events'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    event_type = db.Column(db.String(30), nullable=False)  # test, quiz, assignment, lab, exam, other
    course_code = db.Column(db.String(20), nullable=True)
    date = db.Column(db.Date, nullable=False)
    time = db.Column(db.String(10), nullable=True)  # e.g., "14:00"
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'event_type': self.event_type,
            'course_code': self.course_code,
            'date': self.date.isoformat(),
            'time': self.time,
            'user_id': self.user_id
        }


class CourseOutline(db.Model):
    __tablename__ = 'course_outlines'

    id = db.Column(db.Integer, primary_key=True)
    course_code = db.Column(db.String(20), nullable=False)
    course_name = db.Column(db.String(100), nullable=False)
    filename = db.Column(db.String(200), nullable=False)
    pdf_text = db.Column(db.Text, nullable=False)  # Extracted text from PDF
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'course_code': self.course_code,
            'course_name': self.course_name,
            'filename': self.filename,
            'user_id': self.user_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'text_preview': self.pdf_text[:200] + '...' if len(self.pdf_text) > 200 else self.pdf_text
        }


class Post(db.Model):
    __tablename__ = 'posts'

    id = db.Column(db.Integer, primary_key=True)
    caption = db.Column(db.Text, nullable=True)
    image_data = db.Column(db.Text, nullable=False)  # base64 encoded image
    post_type = db.Column(db.String(30), nullable=False, default='general')  # general, certificate, achievement, event
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    likes = db.relationship('PostLike', backref='post', lazy=True, cascade='all, delete-orphan')
    comments = db.relationship('PostComment', backref='post', lazy=True, cascade='all, delete-orphan')

    def to_dict(self, current_user_id=None):
        user = User.query.get(self.user_id)
        return {
            'id': self.id,
            'caption': self.caption,
            'image_data': self.image_data,
            'post_type': self.post_type,
            'user_id': self.user_id,
            'username': user.full_name if user else 'Unknown',
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'likes_count': len(self.likes),
            'liked_by_me': any(l.user_id == current_user_id for l in self.likes) if current_user_id else False,
            'comments': [c.to_dict() for c in self.comments]
        }


class PostLike(db.Model):
    __tablename__ = 'post_likes'

    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey('posts.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class PostComment(db.Model):
    __tablename__ = 'post_comments'

    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.Text, nullable=False)
    post_id = db.Column(db.Integer, db.ForeignKey('posts.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        user = User.query.get(self.user_id)
        return {
            'id': self.id,
            'text': self.text,
            'username': user.full_name if user else 'Unknown',
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class Attendance(db.Model):
    __tablename__ = 'attendance'

    id = db.Column(db.Integer, primary_key=True)
    course_code = db.Column(db.String(20), nullable=False)
    date = db.Column(db.Date, nullable=False)
    status = db.Column(db.String(10), nullable=False, default='present')  # present, absent, late
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    def to_dict(self):
        return {
            'id': self.id,
            'course_code': self.course_code,
            'date': self.date.isoformat(),
            'status': self.status
        }


class CourseReview(db.Model):
    __tablename__ = 'course_reviews'

    id = db.Column(db.Integer, primary_key=True)
    course_code = db.Column(db.String(20), nullable=False)
    course_name = db.Column(db.String(100), nullable=False)
    rating = db.Column(db.Integer, nullable=False)  # 1-5
    difficulty = db.Column(db.Integer, nullable=False, default=3)  # 1-5
    review_text = db.Column(db.Text, nullable=True)
    lecturer = db.Column(db.String(100), nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        user = User.query.get(self.user_id)
        return {
            'id': self.id,
            'course_code': self.course_code,
            'course_name': self.course_name,
            'rating': self.rating,
            'difficulty': self.difficulty,
            'review_text': self.review_text,
            'lecturer': self.lecturer,
            'username': user.full_name if user else 'Anonymous',
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class Timetable(db.Model):
    __tablename__ = 'timetable'

    id = db.Column(db.Integer, primary_key=True)
    course_code = db.Column(db.String(20), nullable=False)
    course_name = db.Column(db.String(100), nullable=False)
    day = db.Column(db.String(10), nullable=False)  # monday, tuesday, etc.
    start_time = db.Column(db.String(10), nullable=False)  # HH:MM
    end_time = db.Column(db.String(10), nullable=False)
    venue = db.Column(db.String(50), nullable=True)
    class_type = db.Column(db.String(20), nullable=False, default='lecture')  # lecture, tutorial, lab
    repeat_until = db.Column(db.String(10), nullable=True)  # YYYY-MM format e.g. "2025-10"
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    def to_dict(self):
        return {
            'id': self.id,
            'course_code': self.course_code,
            'course_name': self.course_name,
            'day': self.day,
            'start_time': self.start_time,
            'end_time': self.end_time,
            'venue': self.venue,
            'class_type': self.class_type,
            'repeat_until': self.repeat_until
        }


class LectureNote(db.Model):
    __tablename__ = 'lecture_notes'

    id = db.Column(db.Integer, primary_key=True)
    course_code = db.Column(db.String(20), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)  # extracted text from PDF/image or typed
    file_data = db.Column(db.Text, nullable=True)  # base64 encoded original file
    file_type = db.Column(db.String(20), nullable=True)  # pdf, image/jpeg, etc.
    filename = db.Column(db.String(200), nullable=True)
    week_number = db.Column(db.Integer, nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'course_code': self.course_code,
            'title': self.title,
            'content': self.content,
            'filename': self.filename,
            'file_type': self.file_type,
            'has_file': bool(self.file_data),
            'week_number': self.week_number,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class JournalEntry(db.Model):
    __tablename__ = 'journal_entries'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=True)
    entry_type = db.Column(db.String(20), nullable=False, default='milestone')  # milestone, achievement, memory, goal
    date = db.Column(db.Date, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'content': self.content,
            'entry_type': self.entry_type,
            'date': self.date.isoformat(),
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class TodoItem(db.Model):
    __tablename__ = 'todo_items'

    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.String(300), nullable=False)
    done = db.Column(db.Boolean, nullable=False, default=False)
    priority = db.Column(db.String(10), nullable=False, default='medium')  # low, medium, high
    due_date = db.Column(db.Date, nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'text': self.text,
            'done': self.done,
            'priority': self.priority,
            'due_date': self.due_date.isoformat() if self.due_date else None,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
