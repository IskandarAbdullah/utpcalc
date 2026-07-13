# UTP Mark Calculator with AI Advisor

A Flask web application for Universiti Teknologi PETRONAS (UTP) students to calculate test marks, carry marks, and GPA for each course and semester. Integrated with Llama3 AI for performance analysis and study tips.

## Features

- **Mark Calculation**: Input test, quiz, assignment, lab, project, and final exam marks
- **Carry Mark**: Automatically calculates carry mark (all assessments excluding final exam)
- **GPA Calculator**: Semester GPA based on UTP's 4.0 grading scale
- **AI Advisor (Llama3)**: 
  - Performance analysis
  - Grade predictions
  - Personalized study tips
  - Chat about academic questions

## UTP Grading Scale

| Grade | Marks Range | Grade Point |
|-------|-------------|-------------|
| A+    | 90-100      | 4.00        |
| A     | 80-89       | 4.00        |
| A-    | 75-79       | 3.67        |
| B+    | 70-74       | 3.33        |
| B     | 65-69       | 3.00        |
| B-    | 60-64       | 2.67        |
| C+    | 55-59       | 2.33        |
| C     | 50-54       | 2.00        |
| C-    | 45-49       | 1.67        |
| D+    | 40-44       | 1.33        |
| D     | 35-39       | 1.00        |
| F     | 0-34        | 0.00        |

## Setup

### Prerequisites
- Python 3.9+
- Ollama (for AI features)

### 1. Install Python Dependencies

```bash
pip install -r requirements.txt
```

### 2. Install Ollama and Pull Llama3

Download Ollama from https://ollama.com then:

```bash
ollama pull llama3
```

### 3. Start Ollama (keep running in background)

```bash
ollama serve
```

### 4. Run the App

```bash
python app.py
```

Open http://localhost:5000 in your browser.

## How to Use

1. **Create a Semester** - Add your current semester (e.g., "January 2025")
2. **Add Courses** - Add each course with its code, name, and credit hours
3. **Add Assessments** - For each course, add tests, quizzes, assignments with:
   - Marks obtained and total marks
   - Weightage (percentage contribution to final grade)
4. **View Results** - See carry marks, total marks, grades, and GPA automatically calculated
5. **Ask AI** - Use the AI tab to get performance analysis, predictions, and study tips

## Project Structure

```
utpcalc/
├── app.py              # Flask application & routes
├── models.py           # Database models (Semester, Course, Assessment)
├── ai_service.py       # Llama3 AI integration via Ollama
├── config.py           # Configuration
├── requirements.txt    # Python dependencies
├── templates/
│   └── index.html      # Frontend (single-page app)
└── README.md
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET    | /api/semesters | List all semesters |
| POST   | /api/semesters | Create semester |
| DELETE | /api/semesters/:id | Delete semester |
| GET    | /api/semesters/:id/courses | List courses |
| POST   | /api/semesters/:id/courses | Add course |
| DELETE | /api/courses/:id | Delete course |
| POST   | /api/courses/:id/assessments | Add assessment |
| PUT    | /api/assessments/:id | Update assessment |
| DELETE | /api/assessments/:id | Delete assessment |
| GET    | /api/semesters/:id/gpa | Calculate GPA |
| POST   | /api/ai/chat | Chat with AI |
| GET    | /api/ai/analyze/:sem_id | AI performance analysis |
| POST   | /api/ai/predict/:course_id | AI grade prediction |
| GET    | /api/ai/tips/:course_id | AI study tips |
