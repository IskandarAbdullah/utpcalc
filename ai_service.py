import json
import re
import base64
from config import Config

# ============ AI CLIENT (Groq cloud or Ollama local) ============

def _chat(messages, use_vision=False):
    """Send chat to AI - uses Groq if API key set, otherwise falls back to Ollama."""
    if Config.USE_GROQ:
        return _chat_groq(messages, use_vision)
    else:
        return _chat_ollama(messages, use_vision)


def _chat_groq(messages, use_vision=False):
    """Chat via Groq API (free cloud)."""
    import httpx

    model = Config.GROQ_VISION_MODEL if use_vision else Config.GROQ_MODEL
    headers = {
        'Authorization': f'Bearer {Config.GROQ_API_KEY}',
        'Content-Type': 'application/json'
    }

    # Convert messages to Groq/OpenAI format
    groq_messages = []
    for msg in messages:
        if 'images' in msg and msg['images']:
            # Vision message with image
            content = [
                {'type': 'text', 'text': msg['content']},
                {'type': 'image_url', 'image_url': {'url': f"data:image/jpeg;base64,{msg['images'][0]}"}}
            ]
            groq_messages.append({'role': msg['role'], 'content': content})
        else:
            groq_messages.append({'role': msg['role'], 'content': msg['content']})

    payload = {
        'model': model,
        'messages': groq_messages,
        'temperature': 0.7,
        'max_tokens': 2048
    }

    response = httpx.post(
        'https://api.groq.com/openai/v1/chat/completions',
        headers=headers,
        json=payload,
        timeout=60
    )
    response.raise_for_status()
    data = response.json()
    return data['choices'][0]['message']['content']


def _chat_ollama(messages, use_vision=False):
    """Chat via local Ollama."""
    import ollama

    model = Config.OLLAMA_VISION_MODEL if use_vision else Config.OLLAMA_MODEL
    response = ollama.chat(model=model, messages=messages)
    return response['message']['content']


# ============ CORE AI FUNCTIONS ============

def get_ai_response(prompt, context=None):
    """Get AI response."""
    system_message = """You are an AI academic advisor for Universiti Teknologi PETRONAS (UTP) students. 
You help students understand their academic performance, calculate marks, provide study tips, 
and predict grades based on their current performance. 
You are knowledgeable about UTP's grading system (4.0 GPA scale) and assessment structures.
Be encouraging but honest about areas needing improvement.
Keep responses concise and actionable.

IMPORTANT RULES:
- If course outline data is provided in the context, you ALREADY HAVE the PDF content. Do NOT ask the student to share or upload it again.
- Use the provided outline data directly to answer questions about assessments, weightages, topics, etc.
- If the student asks you to edit assessments based on a PDF they uploaded, use the outline data in the context to do it immediately.
- Always reference specific details from the outlines when available."""

    messages = [{'role': 'system', 'content': system_message}]

    if context:
        messages.append({
            'role': 'user',
            'content': f"Here is the student's current academic data:\n{context}\n\nNow answer this question: {prompt}"
        })
    else:
        messages.append({'role': 'user', 'content': prompt})

    try:
        content = _chat(messages)
        return {'success': True, 'response': content}
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'response': 'AI service unavailable. Check your Groq API key or Ollama connection.'
        }


def analyze_performance(courses_data):
    """Analyze student performance and provide insights."""
    context = "Student's current courses and marks:\n"
    for course in courses_data:
        context += f"\n{course['code']} - {course['name']}:\n"
        context += f"  Carry Mark: {course['carry_mark']}%\n"
        context += f"  Final Exam: {course['final_exam_mark']}%\n"
        context += f"  Total: {course['total_mark']}%\n"
        context += f"  Grade: {course['grade']} (GP: {course['grade_point']})\n"
        context += f"  Assessments:\n"
        for a in course['assessments']:
            context += f"    - {a['name']} ({a['category']}): {a['marks_obtained']}/{a['total_marks']} (Weightage: {a['weightage']}%, Weighted: {a['weighted_score']}%)\n"

    prompt = """Based on this student's academic data, provide:
1. Overall performance summary
2. Strongest and weakest courses
3. Specific study recommendations
4. GPA prediction for this semester
5. Areas that need immediate attention"""

    return get_ai_response(prompt, context)


def predict_grade(course_data, target_grade=None):
    """Predict what marks are needed in remaining assessments."""
    context = f"Course: {course_data['code']} - {course_data['name']}\n"
    context += f"Current carry mark: {course_data['carry_mark']}%\n"
    context += f"Assessments completed:\n"

    total_weightage_done = 0
    for a in course_data['assessments']:
        context += f"  - {a['name']} ({a['category']}): {a['marks_obtained']}/{a['total_marks']} (Weightage: {a['weightage']}%)\n"
        total_weightage_done += a['weightage']

    remaining_weightage = 100 - total_weightage_done
    context += f"\nTotal weightage completed: {total_weightage_done}%\n"
    context += f"Remaining weightage: {remaining_weightage}%\n"

    if target_grade:
        prompt = f"What marks does this student need in their remaining assessments (worth {remaining_weightage}% total) to achieve a {target_grade} grade? Provide specific calculations."
    else:
        prompt = f"Based on current performance, what grade can this student realistically expect? What do they need in remaining assessments ({remaining_weightage}% worth) to get an A?"

    return get_ai_response(prompt, context)


def get_study_tips(course_data):
    """Get personalized study tips based on performance patterns."""
    context = f"Course: {course_data['code']} - {course_data['name']}\n"
    context += f"Assessments:\n"
    for a in course_data['assessments']:
        context += f"  - {a['name']} ({a['category']}): {a['percentage_score']}% score\n"

    prompt = """Based on this student's assessment scores, provide:
1. Performance pattern analysis (are they improving or declining?)
2. Which assessment types they excel at vs struggle with
3. Specific study strategies tailored to their weak areas
4. Time management tips for upcoming assessments"""

    return get_ai_response(prompt, context)


# ============ PDF & EXTRACTION FUNCTIONS ============

def extract_pdf_text(pdf_file):
    """Extract text from uploaded PDF file."""
    from PyPDF2 import PdfReader
    import io

    reader = PdfReader(io.BytesIO(pdf_file.read()))
    text = ""
    for page in reader.pages:
        text += page.extract_text() or ""
    return text


def parse_assessments_from_pdf(pdf_text, course_code=None):
    """Use AI to extract assessment details from PDF text."""
    system_message = """You are a data extraction AI. You extract assessment/evaluation information from university course outlines.

You MUST respond with ONLY a valid JSON array. No explanation, no markdown, just the JSON.

Each assessment object should have:
- "name": the assessment name (e.g., "Test 1", "Quiz 1", "Final Exam")
- "category": one of: test, quiz, assignment, lab, midterm, final_exam, project, presentation, tutorial, other
- "total_marks": the total marks (number, default 100)
- "weightage": the percentage weightage (number, e.g., 15 means 15%)

Rules:
- Extract ALL assessments mentioned
- If weightage is given as a range (e.g., 2 quizzes worth 10% each), create separate entries
- Ensure all weightages add up to approximately 100%

Example output:
[{"name": "Test 1", "category": "test", "total_marks": 100, "weightage": 15}]"""

    messages = [
        {'role': 'system', 'content': system_message},
        {'role': 'user', 'content': f"Extract all assessments from this course document:\n\n{pdf_text[:4000]}"}
    ]

    try:
        content = _chat(messages)
        json_match = re.search(r'\[.*\]', content, re.DOTALL)
        if json_match:
            content = json_match.group(0)

        assessments = json.loads(content)
        valid_categories = ['test', 'quiz', 'assignment', 'lab', 'midterm', 'final_exam', 'project', 'presentation', 'tutorial', 'other']
        cleaned = []
        for a in assessments:
            if not isinstance(a, dict) or not a.get('name') or not a.get('category'):
                continue
            if a['category'] not in valid_categories:
                a['category'] = 'other'
            cleaned.append({
                'name': str(a['name']),
                'category': a['category'],
                'total_marks': float(a.get('total_marks', 100)),
                'weightage': float(a.get('weightage', 0)),
                'marks_obtained': 0
            })

        return {'success': True, 'assessments': cleaned, 'raw_text_preview': pdf_text[:500]}
    except json.JSONDecodeError:
        return {'success': False, 'error': 'AI could not parse assessments. Try a clearer PDF.', 'raw_text_preview': pdf_text[:500]}
    except Exception as e:
        return {'success': False, 'error': str(e), 'raw_text_preview': pdf_text[:500] if pdf_text else ''}


def ai_edit_assessments(course_data, instruction):
    """Use AI to edit/modify assessments based on natural language instruction."""
    system_message = """You are an AI that modifies student assessment data based on instructions.
You MUST respond with ONLY a valid JSON object with key "assessments" containing the updated array.

Each assessment: {"name": string, "category": one of test/quiz/assignment/lab/midterm/final_exam/project/presentation/tutorial/other, "marks_obtained": number, "total_marks": number, "weightage": number}

Example: {"assessments": [{"name": "Test 1", "category": "test", "marks_obtained": 85, "total_marks": 100, "weightage": 15}]}"""

    context = f"Course: {course_data['code']} - {course_data['name']}\nCurrent assessments:\n{json.dumps(course_data['assessments'], indent=2)}"
    messages = [
        {'role': 'system', 'content': system_message},
        {'role': 'user', 'content': f"{context}\n\nInstruction: {instruction}\n\nReturn updated assessments as JSON."}
    ]

    try:
        content = _chat(messages)
        json_match = re.search(r'\{.*\}', content, re.DOTALL)
        if json_match:
            content = json_match.group(0)

        result = json.loads(content)
        assessments = result.get('assessments', [])
        valid_categories = ['test', 'quiz', 'assignment', 'lab', 'midterm', 'final_exam', 'project', 'presentation', 'tutorial', 'other']
        cleaned = []
        for a in assessments:
            if not isinstance(a, dict) or not a.get('name'):
                continue
            cat = a.get('category', 'other')
            if cat not in valid_categories:
                cat = 'other'
            cleaned.append({
                'name': str(a['name']),
                'category': cat,
                'marks_obtained': float(a.get('marks_obtained', 0)),
                'total_marks': float(a.get('total_marks', 100)),
                'weightage': float(a.get('weightage', 0))
            })
        return {'success': True, 'assessments': cleaned}
    except json.JSONDecodeError:
        return {'success': False, 'error': 'AI response was not valid JSON. Try rephrasing.'}
    except Exception as e:
        return {'success': False, 'error': str(e)}


# ============ CALENDAR AI FUNCTIONS ============

def ai_parse_calendar_events(instruction, existing_events=None, courses=None):
    """Use AI to parse natural language into calendar events."""
    system_message = """You are an AI that manages a student's academic calendar.
You MUST respond with ONLY a valid JSON object with key "events" containing an array.

Each event: {"action": "add" or "delete", "title": string, "event_type": one of test/quiz/assignment/lab/exam/other, "course_code": string, "date": "YYYY-MM-DD", "time": "HH:MM" or "", "description": string}

For delete: include title and date to identify the event."""

    context = f"Today's date: {__import__('datetime').date.today().isoformat()}\n"
    if courses:
        context += "Courses:\n" + "\n".join(f"  - {c['code']} ({c['name']})" for c in courses) + "\n"
    if existing_events:
        context += "Current events:\n" + "\n".join(f"  - {e['date']} {e.get('time','')} | {e['title']} ({e['event_type']})" for e in existing_events) + "\n"

    messages = [
        {'role': 'system', 'content': system_message},
        {'role': 'user', 'content': f"{context}\nInstruction: {instruction}"}
    ]

    try:
        content = _chat(messages)
        json_match = re.search(r'\{.*\}', content, re.DOTALL)
        if json_match:
            content = json_match.group(0)

        result = json.loads(content)
        events = result.get('events', [])
        valid_types = ['test', 'quiz', 'assignment', 'lab', 'exam', 'other']
        cleaned = []
        for e in events:
            if not isinstance(e, dict) or not e.get('title') or not e.get('date'):
                continue
            evt_type = e.get('event_type', 'other')
            if evt_type not in valid_types:
                evt_type = 'other'
            cleaned.append({
                'action': e.get('action', 'add'),
                'title': str(e['title']),
                'event_type': evt_type,
                'course_code': str(e.get('course_code', '')),
                'date': str(e['date']),
                'time': str(e.get('time', '')),
                'description': str(e.get('description', ''))
            })
        return {'success': True, 'events': cleaned}
    except json.JSONDecodeError:
        return {'success': False, 'error': 'AI could not parse your instruction. Try rephrasing.'}
    except Exception as e:
        return {'success': False, 'error': str(e)}


def ai_parse_pdf_calendar(pdf_text, courses=None, selected_course_code=''):
    """Extract calendar events from a PDF."""
    system_message = """You are a data extraction AI. Extract dates and academic events from university documents.
You MUST respond with ONLY a valid JSON object with key "events" containing an array.

Each event: {"title": string, "event_type": one of test/quiz/assignment/lab/exam/other, "course_code": string, "date": "YYYY-MM-DD", "time": "HH:MM" or "", "description": string}

Rules:
- If year not specified, assume 2025
- If a specific course code is provided, tag ALL events with it unless clearly different"""

    context = ""
    if selected_course_code:
        context += f"THIS IS FOR COURSE: {selected_course_code}. Tag all events with this code.\n\n"
    if courses:
        context += "Courses:\n" + "\n".join(f"  - {c['code']} ({c['name']})" for c in courses) + "\n\n"

    messages = [
        {'role': 'system', 'content': system_message},
        {'role': 'user', 'content': f"{context}Extract events from:\n\n{pdf_text[:4000]}"}
    ]

    try:
        content = _chat(messages)
        json_match = re.search(r'\{.*\}', content, re.DOTALL)
        if json_match:
            content = json_match.group(0)

        result = json.loads(content)
        events = result.get('events', [])
        valid_types = ['test', 'quiz', 'assignment', 'lab', 'exam', 'other']
        cleaned = []
        for e in events:
            if not isinstance(e, dict) or not e.get('title') or not e.get('date'):
                continue
            evt_type = e.get('event_type', 'other')
            if evt_type not in valid_types:
                evt_type = 'other'
            cleaned.append({
                'title': str(e['title']),
                'event_type': evt_type,
                'course_code': str(e.get('course_code', '') or selected_course_code),
                'date': str(e['date']),
                'time': str(e.get('time', '')),
                'description': str(e.get('description', ''))
            })
        return {'success': True, 'events': cleaned}
    except json.JSONDecodeError:
        return {'success': False, 'error': 'AI could not extract events from the PDF.'}
    except Exception as e:
        return {'success': False, 'error': str(e)}


# ============ VISION AI FUNCTION ============

def ai_read_image(image_bytes, instruction="Extract all marks and grades from this image"):
    """Use vision model to read an image (test paper, grade sheet, etc.)."""
    b64_image = base64.b64encode(image_bytes).decode('utf-8')

    system_prompt = """You are an AI that reads student test papers, grade sheets, and academic documents from images.
Extract marks, scores, grades, and any assessment information you can see.

Respond with a JSON object:
{"assessments": [{"name": "...", "category": "test/quiz/assignment/lab/midterm/final_exam/project/other", "marks_obtained": number, "total_marks": number}], "raw_text": "text from image", "summary": "brief summary"}

Valid categories: test, quiz, assignment, lab, midterm, final_exam, project, presentation, tutorial, other"""

    messages = [{
        'role': 'user',
        'content': f"{system_prompt}\n\nInstruction: {instruction}",
        'images': [b64_image]
    }]

    try:
        content = _chat(messages, use_vision=True)
        json_match = re.search(r'\{.*\}', content, re.DOTALL)
        if json_match:
            try:
                result = json.loads(json_match.group(0))
                valid_categories = ['test', 'quiz', 'assignment', 'lab', 'midterm', 'final_exam', 'project', 'presentation', 'tutorial', 'other']
                if 'assessments' in result:
                    for a in result['assessments']:
                        if a.get('category') not in valid_categories:
                            a['category'] = 'other'
                return {'success': True, **result}
            except json.JSONDecodeError:
                pass

        return {'success': True, 'assessments': [], 'raw_text': content, 'summary': content[:200]}
    except Exception as e:
        return {'success': False, 'error': str(e), 'assessments': [], 'raw_text': '', 'summary': 'Vision AI unavailable.'}
