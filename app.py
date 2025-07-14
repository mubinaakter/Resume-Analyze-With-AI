from flask import Flask, render_template, request, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from flask_sqlalchemy import SQLAlchemy
import os
import docx2txt
import PyPDF2
from pdfminer.high_level import extract_text
import docx
import re
from datetime import timedelta

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# Allowed resume file extensions
ALLOWED_EXTENSIONS = {'pdf', 'docx'}

app = Flask(__name__)
app.secret_key = 'your_secret_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///analyzer.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'uploads'
app.permanent_session_lifetime = timedelta(days=7)

db = SQLAlchemy(app)

# User database model
class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), unique=True, nullable=False)
    email = db.Column(db.String(30), unique=True, nullable=False)
    phone = db.Column(db.String(11), nullable=False)
    password = db.Column(db.String(128), nullable=False)

# Helper to check allowed file extensions
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Resume parsing functions for different file types
def parse_pdf(file_path):
    try:
        text = extract_text(file_path)
        return text
    except Exception:
        return ""

def parse_docx(file_path):
    try:
        doc = docx.Document(file_path)
        full_text = [para.text for para in doc.paragraphs]
        return '\n'.join(full_text)
    except Exception:
        return ""

def parse_resume(file_path):
    ext = file_path.rsplit('.', 1)[1].lower()
    if ext == 'pdf':
        return parse_pdf(file_path)
    elif ext == 'docx':
        return parse_docx(file_path)
    else:
        return ""

# Scoring the resume based on various categories with detailed feedback
def score_resume_detailed(text):
    text = text.lower()
    results = []

    # Contact Information
    email_pattern = r'\b[\w.-]+@[\w.-]+\.\w{2,4}\b'
    phone_pattern = r'\b(\+?\d{1,3}[-.\s]?)?(\(?\d{3}\)?[-.\s]?)?\d{3}[-.\s]?\d{4}\b'
    has_email = re.search(email_pattern, text) is not None
    has_phone = re.search(phone_pattern, text) is not None
    contact_score = 10 if has_email and has_phone else 5
    contact_flaws, contact_fixes = [], []
    if not has_email or not has_phone:
        contact_flaws.append("Missing or incomplete contact information (email and/or phone).")
        contact_fixes.append("Add a professional email address and your current phone number at the top of your resume.")
    results.append({
        'category': 'Contact Information',
        'score': contact_score,
        'max_score': 10,
        'flaws': contact_flaws,
        'fix_tips': contact_fixes,
        'suggestions': ["Make sure your contact details are easy to find and up-to-date."] if contact_flaws else []
    })

    # Professional Summary
    has_summary = 'summary' in text or 'objective' in text
    summary_score = 10 if has_summary else 0
    summary_flaws, summary_fixes = [], []
    if not has_summary:
        summary_flaws.append("No professional summary or objective found.")
        summary_fixes.append("Write a brief professional summary or objective that highlights your skills and career goals.")
    results.append({
        'category': 'Professional Summary',
        'score': summary_score,
        'max_score': 10,
        'flaws': summary_flaws,
        'fix_tips': summary_fixes,
        'suggestions': ["Keep your summary concise and tailored to the job."] if summary_flaws else []
    })

    # Skills
    skills_list = ['python', 'java', 'sql', 'excel', 'communication', 'teamwork', 'leadership']
    skills_found = [skill for skill in skills_list if skill in text]
    skills_score = min(len(skills_found) * 3, 15)
    skills_flaws, skills_fixes = [], []
    if len(skills_found) < 3:
        skills_flaws.append("Skills section is weak or missing relevant skills.")
        skills_fixes.append("Include more technical and soft skills relevant to your target job, e.g. Python, SQL, communication.")
    results.append({
        'category': 'Skills',
        'score': skills_score,
        'max_score': 15,
        'flaws': skills_flaws,
        'fix_tips': skills_fixes,
        'suggestions': ["List skills clearly and group them if possible."] if skills_flaws else []
    })

    # Work Experience
    experience_keywords = ['experience', 'worked', 'managed', 'developed', 'achieved']
    exp_found = any(word in text for word in experience_keywords)
    experience_score = 20 if exp_found else 0
    exp_flaws, exp_fixes = [], []
    if not exp_found:
        exp_flaws.append("Work experience section seems missing or weak.")
        exp_fixes.append("Add detailed descriptions of your past roles, responsibilities, and key achievements.")
    results.append({
        'category': 'Work Experience',
        'score': experience_score,
        'max_score': 20,
        'flaws': exp_flaws,
        'fix_tips': exp_fixes,
        'suggestions': ["Use action verbs and quantify achievements."] if exp_flaws else []
    })

    # Education
    education_keywords = ['bachelor', 'master', 'university', 'college', 'degree']
    edu_found = any(word in text for word in education_keywords)
    education_score = 15 if edu_found else 0
    edu_flaws, edu_fixes = [], []
    if not edu_found:
        edu_flaws.append("Education details are missing or incomplete.")
        edu_fixes.append("Include your highest degree, university name, and graduation year.")
    results.append({
        'category': 'Education',
        'score': education_score,
        'max_score': 15,
        'flaws': edu_flaws,
        'fix_tips': edu_fixes,
        'suggestions': ["List education in reverse chronological order."] if edu_flaws else []
    })

    # Certifications
    cert_found = 'certification' in text or 'certified' in text
    cert_score = 10 if cert_found else 0
    cert_flaws, cert_fixes = [], []
    if not cert_found:
        cert_flaws.append("No certifications or trainings mentioned.")
        cert_fixes.append("Add relevant certifications to boost credibility.")
    results.append({
        'category': 'Certifications',
        'score': cert_score,
        'max_score': 10,
        'flaws': cert_flaws,
        'fix_tips': cert_fixes,
        'suggestions': ["Include professional courses and certifications."] if cert_flaws else []
    })

    # Formatting & Length
    length_score = 10 if len(text) > 500 else 0
    length_flaws, length_fixes = [], []
    if len(text) <= 500:
        length_flaws.append("Resume appears too short, consider adding more details.")
        length_fixes.append("Expand sections with relevant projects, skills, and experiences.")
    results.append({
        'category': 'Formatting & Length',
        'score': length_score,
        'max_score': 10,
        'flaws': length_flaws,
        'fix_tips': length_fixes,
        'suggestions': ["Keep the resume clear and easy to scan."] if length_flaws else []
    })

    # Keyword Match for target job keywords (basic scoring)
    job_keywords = ['python', 'data', 'analysis', 'machine learning', 'project']
    matched = sum(word in text for word in job_keywords)
    keyword_score = min(matched * 2, 10)
    results.append({
        'category': 'Keyword Match',
        'score': keyword_score,
        'max_score': 10,
        'flaws': [],
        'fix_tips': [],
        'suggestions': []
    })

    total_score = sum(item['score'] for item in results)
    total_score = min(total_score, 100)  # Cap max score to 100

    return total_score, results

# Additional text extraction functions (alternative to pdfminer for PDF)
def extract_text_from_pdf(file_path):
    text = ""
    with open(file_path, 'rb') as file:
        reader = PyPDF2.PdfReader(file)
        for page in reader.pages:
            text += page.extract_text() or ""
    return text.strip()

def extract_text_from_docx(file_path):
    return docx2txt.process(file_path)

def extract_text_from_txt(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        return file.read()

def extract_text(file_path):
    ext = file_path.rsplit('.', 1)[1].lower()
    if ext == 'pdf':
        return extract_text_from_pdf(file_path)
    elif ext == 'docx':
        return extract_text_from_docx(file_path)
    elif ext == 'txt':
        return extract_text_from_txt(file_path)
    else:
        return ""

# Calculate similarity score between resume and job keywords using TF-IDF and cosine similarity
def calculate_text_score(resume_text, keywords):
    """
    Uses TF-IDF vectorization and cosine similarity to measure how closely
    the resume matches the job keywords.
    Returns similarity percentage (0-100).
    """
    vectorizer = TfidfVectorizer(stop_words='english')
    # Prepare list with resume + keywords for vectorization
    combined_text = [resume_text] + keywords
    tfidf_matrix = vectorizer.fit_transform(combined_text)
    cosine_sim = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:])
    return cosine_sim[0].mean() * 100

# Basic design evaluation (stub function)
def evaluate_design_score(resume_text):
    """
    Dummy design score based on presence of Education and Experience keywords.
    Could be expanded to analyze formatting, layout, font usage etc.
    """
    if 'education' in resume_text.lower() and 'experience' in resume_text.lower():
        return 80
    return 50

# Default keywords (can be customized based on user/job)
keywords = ["Python", "data analysis", "machine learning", "SQL", "project management"]

# Flask routes and handlers follow

@app.route('/')
def root():
    return redirect(url_for('home'))

@app.route('/home')
def home():
    return render_template('home.html')

@app.route('/product')
def product():
    return render_template('product.html')

@app.route('/profile')
def profile():
    if 'user_id' not in session:
        flash('Please log in to view your profile.', 'danger')
        return redirect(url_for('login'))
    user = User.query.get(session['user_id'])
    return render_template('profile.html', user=user)

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        phone = request.form['phone']
        password = request.form['password']
        confirm_password = request.form['confirm_password']

        # Validation checks
        if User.query.filter_by(username=username).first():
            flash('Username already exists.', 'danger')
            return redirect(url_for('signup'))
        if User.query.filter_by(email=email).first():
            flash('Email already exists.', 'danger')
            return redirect(url_for('signup'))
        if User.query.filter_by(phone=phone).first():
            flash('Phone number already exists.', 'danger')
            return redirect(url_for('signup'))
        if password != confirm_password:
            flash('Passwords do not match.', 'danger')
            return redirect(url_for('signup'))

        # Save new user with hashed password
        new_user = User(
            username=username,
            email=email,
            phone=phone,
            password=generate_password_hash(password, method='pbkdf2:sha256')
        )
        db.session.add(new_user)
        db.session.commit()
        flash('Signup successful! You can now log in.', 'success')
        return redirect(url_for('login'))
    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = User.query.filter_by(email=email).first()

        if user and check_password_hash(user.password, password):
            session.permanent = True
            session['user_id'] = user.id
            flash('Login successful!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid email or password.', 'danger')

    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        flash('Please log in.', 'danger')
        return redirect(url_for('login'))

    user = User.query.get(session['user_id'])
    return render_template('dashboard.html', user=user)

@app.route('/matchresume', methods=['GET'])
def matchresume():
    if 'user_id' not in session:
        flash('Please log in to use the Resume Analyzer.', 'danger')
        return redirect(url_for('login'))
    return render_template('matchresume.html')

@app.route('/matcher', methods=['POST'])
def matcher():
    if 'user_id' not in session:
        flash('Please log in to use the Resume Analyzer.', 'danger')
        return redirect(url_for('login'))

    job_description = request.form['job_description']
    resume_files = request.files.getlist('resumes')

    if not resume_files or not job_description:
        return render_template('matcher_result.html', message="Please upload resumes and enter a job description.")

    resumes = []
    for resume_file in resume_files:
        filename = os.path.join(app.config['UPLOAD_FOLDER'], resume_file.filename)
        resume_file.save(filename)
        resumes.append(extract_text(filename))

    # Vectorize and calculate cosine similarity between job description and resumes
    vectorizer = TfidfVectorizer().fit_transform([job_description] + resumes)
    vectors = vectorizer.toarray()
    job_vector = vectors[0]
    resume_vectors = vectors[1:]
    similarities = cosine_similarity([job_vector], resume_vectors)[0]

    top_indices = similarities.argsort()[-5:][::-1]
    top_resumes = [resume_files[i].filename for i in top_indices]
    similarity_scores = [round(similarities[i], 2) for i in top_indices]

    return render_template('matcher_result.html',
                           message="Top matching resumes:",
                           top_resumes=top_resumes,
                           similarity_scores=similarity_scores)

@app.route('/upload_resume', methods=['GET', 'POST'])
def upload_resume():
    if request.method == 'POST':
        if 'resume' not in request.files:
            return "No file part", 400

        file = request.files['resume']

        if file.filename == '':
            return "No selected file", 400

        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)

            resume_text = parse_resume(filepath)
            if not resume_text.strip():
                return "Failed to parse resume. Please upload a valid PDF or DOCX file."

            score, detailed_results = score_resume_detailed(resume_text)
            return render_template('result.html', score=score, results=detailed_results)
        else:
            return "Allowed file types are PDF and DOCX only.", 400

    return render_template('upload.html')

@app.route('/resumebuilder', methods=['GET'])
def resumebuilder():
    if 'user_id' not in session:
        flash('Please log in to use the Resume Analyzer.', 'danger')
        return redirect(url_for('login'))
    return render_template('resumebuilder.html')

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    flash('Logged out.', 'success')
    return redirect(url_for('home'))

@app.route('/upload', methods=['POST'])
def upload():
    if 'user_id' not in session:
        flash('Please log in first.', 'danger')
        return redirect(url_for('login'))

    result = None
    if 'resume' in request.files:
        resume = request.files['resume']
        if resume:
            filename = secure_filename(resume.filename)
            path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            resume.save(path)
            result = extract_text_from_pdf(path)

    return render_template('analyze.html', result=result)


if __name__ == '__main__':
    with app.app_context():
        db.create_all()

    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        os.makedirs(app.config['UPLOAD_FOLDER'])

    app.run(debug=True)