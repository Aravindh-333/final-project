from flask import Flask, render_template, request, redirect, url_for, session, flash, Response
import io
import time
import cv2
import face_recognition
import numpy as np
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import secrets
from bson.objectid import ObjectId
from db_store import init_db, get_auth_db, get_reports_db, get_gridfs

app = Flask(__name__)

# Generate secure secret key
app.secret_key = secrets.token_hex(32)

# Configuration
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg'}
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB
app.config['SESSION_PERMANENT'] = True
app.config['PERMANENT_SESSION_LIFETIME'] = 3600  # 1 hour session

# Initialize MongoDB database and GridFS
init_db()

# Context Processor
@app.context_processor
def inject_datetime():
    return {'datetime': datetime}

# Helper Functions
def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

# Authentication Routes
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        
        if len(username) < 4 or len(password) < 6:
            flash('Username must be at least 4 characters and password 6 characters', 'error')
            return redirect(url_for('register'))
        
        users_collection = get_auth_db()
        if users_collection.find_one({'username': username}):
            flash('Username already exists', 'error')
            return redirect(url_for('register'))
        
        hashed_password = generate_password_hash(password)
        try:
            user_id = users_collection.insert_one({
                'username': username,
                'password': hashed_password
            }).inserted_id
            flash('Registration successful! Please login.', 'success')
            return redirect(url_for('login'))
        except Exception as e:
            app.logger.error(f"Registration error: {str(e)}")
            flash('Registration failed', 'error')
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        
        users_collection = get_auth_db()
        user = users_collection.find_one({'username': username})
        
        if user and check_password_hash(user['password'], password):
            session['user_id'] = str(user['_id'])
            session['username'] = user['username']
            flash('Login successful!', 'success')
            return redirect(url_for('index'))
        else:
            flash('Invalid username or password', 'error')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out', 'info')
    return redirect(url_for('login'))

# Main Application Routes
@app.route('/')
def index():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    current_time = datetime.now().strftime("%H:%M:%S")
    return render_template('index.html',
                         username=session['username'],
                         current_time=current_time,
                         version="v2.4.7")

@app.route('/scan', methods=['GET', 'POST'])
def scan():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        # Check for file
        if 'face_file' not in request.files:
            return render_template('error.html',
                                message="No file selected",
                                suggestion="Please choose an image file to upload",
                                current_time=datetime.now().strftime("%H:%M:%S"),
                                version="v2.4.7")
        
        file = request.files['face_file']
        if file.filename == '':
            return render_template('error.html',
                                message="No file selected",
                                suggestion="Please choose an image file to upload",
                                current_time=datetime.now().strftime("%H:%M:%S"),
                                version="v2.4.7")

        if not allowed_file(file.filename):
            return render_template('error.html',
                                message="Invalid file type",
                                suggestion="Only JPG, JPEG, and PNG files are allowed",
                                current_time=datetime.now().strftime("%H:%M:%S"),
                                version="v2.4.7")

        # Collect missing person details
        name = request.form.get('name', '').strip()
        age = request.form.get('age', '').strip()
        gender = request.form.get('gender', '').strip()
        last_seen_location = request.form.get('last_seen_location', '').strip()
        last_seen_date = request.form.get('last_seen_date', '').strip()
        last_seen_time = request.form.get('last_seen_time', '').strip()
        contact_number = request.form.get('contact_number', '').strip()

        # Validate required fields
        if not all([name, age, gender, last_seen_location, last_seen_date, contact_number]):
            return render_template('error.html',
                                message="Missing required details",
                                suggestion="Please provide name, age, gender, last seen location, last seen date, and contact number",
                                current_time=datetime.now().strftime("%H:%M:%S"),
                                version="v2.4.7")

        # Validate age
        try:
            age = int(age)
            if age < 0 or age > 120:
                raise ValueError("Invalid age")
        except ValueError:
            return render_template('error.html',
                                message="Invalid age",
                                suggestion="Please enter a valid age (0-120)",
                                current_time=datetime.now().strftime("%H:%M:%S"),
                                version="v2.4.7")

        # Validate last seen date format (YYYY-MM-DD)
        try:
            datetime.strptime(last_seen_date, '%Y-%m-%d')
        except ValueError:
            return render_template('error.html',
                                message="Invalid last seen date",
                                suggestion="Please enter a valid date in YYYY-MM-DD format",
                                current_time=datetime.now().strftime("%H:%M:%S"),
                                version="v2.4.7")

        # Validate last seen time if provided (HH:MM)
        if last_seen_time:
            try:
                datetime.strptime(last_seen_time, '%H:%M')
            except ValueError:
                return render_template('error.html',
                                    message="Invalid last seen time",
                                    suggestion="Please enter a valid time in HH:MM format or leave it blank",
                                    current_time=datetime.now().strftime("%H:%M:%S"),
                                    version="v2.4.7")

        # Validate contact number (basic check for digits and optional +)
        if not (contact_number.replace('+', '').replace(' ', '').isdigit() and len(contact_number.replace('+', '').replace(' ', '')) >= 7):
            return render_template('error.html',
                                message="Invalid contact number",
                                suggestion="Please enter a valid phone number (minimum 7 digits)",
                                current_time=datetime.now().strftime("%H:%M:%S"),
                                version="v2.4.7")

        gridfs = get_gridfs()
        try:
            # Read the uploaded file into memory
            file_data = file.read()
            
            # Load the image for face recognition using BytesIO
            file_stream = io.BytesIO(file_data)
            uploaded_img = face_recognition.load_image_file(file_stream)
            uploaded_encodings = face_recognition.face_encodings(uploaded_img)
            
            if not uploaded_encodings:
                return render_template('error.html',
                                     message="No faces detected",
                                     suggestion="Please ensure the image contains a clear face",
                                     current_time=datetime.now().strftime("%H:%M:%S"),
                                     version="v2.4.7")
            
            # Detect face locations for drawing the rectangle
            face_locations = face_recognition.face_locations(uploaded_img)
            if not face_locations:
                return render_template('error.html',
                                     message="No faces detected for annotation",
                                     suggestion="Please ensure the image contains a clear face",
                                     current_time=datetime.now().strftime("%H:%M:%S"),
                                     version="v2.4.7")

            # Convert the image to OpenCV format for annotation
            file_stream.seek(0)
            img_array = np.frombuffer(file_stream.read(), np.uint8)
            img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
            
            # Draw a rectangle around each detected face
            for (top, right, bottom, left) in face_locations:
                cv2.rectangle(img, (left, top), (right, bottom), (0, 255, 0), 2)

            # Add the scan date and time as text on the image
            scan_date = datetime.now().strftime("%Y-%m-%d")
            scan_time = datetime.now().strftime("%H:%M:%S")
            text = f"Scan Date: {scan_date} {scan_time}"
            cv2.putText(img, text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

            # Encode the modified image back to bytes
            _, img_encoded = cv2.imencode('.jpg', img)
            img_bytes = img_encoded.tobytes()
            
            # Store the modified image in GridFS
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            gridfs_filename = f"{timestamp}_{file.filename}"
            reference_file_id = gridfs.put(img_bytes, filename=gridfs_filename, content_type='image/jpeg')
            
            # Store form data in session to pass to scanning route
            session['scan_data'] = {
                'name': name,
                'age': age,
                'gender': gender,
                'last_seen_location': last_seen_location,
                'last_seen_date': last_seen_date,
                'last_seen_time': last_seen_time,
                'contact_number': contact_number,
                'reference_file_id': str(reference_file_id),
                'scan_date': scan_date,
                'scan_time': scan_time,
                'uploaded_encodings': uploaded_encodings[0].tolist()  # Convert numpy array to list
            }
            
            # Redirect to scanning route
            return redirect(url_for('scanning'))
        
        except Exception as e:
            app.logger.error(f"Processing error: {str(e)}")
            return render_template('error.html',
                                 message="Scan processing failed",
                                 suggestion="Try again with a different image",
                                 current_time=datetime.now().strftime("%H:%M:%S"),
                                 version="v2.4.7")
    
    current_time = datetime.now().strftime("%H:%M:%S")
    return render_template('scan.html',
                         username=session['username'],
                         current_time=current_time,
                         version="v2.4.7")

@app.route('/scanning')
def scanning():
    if 'user_id' not in session or 'scan_data' not in session:
        return redirect(url_for('login'))
    
    scan_data = session.get('scan_data', {})
    reference_file_id = scan_data.get('reference_file_id')
    uploaded_encodings = np.array(scan_data.get('uploaded_encodings', []))
    
    gridfs = get_gridfs()
    try:
        # Proceed with face recognition
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            gridfs.delete(ObjectId(reference_file_id))
            session.pop('scan_data', None)
            return render_template('error.html',
                                message="Camera not accessible",
                                suggestion="Check if another application is using the camera",
                                current_time=datetime.now().strftime("%H:%M:%S"),
                                version="v2.4.7")
        
        try:
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
            time.sleep(2)  # Camera warm-up
            
            best_confidence = 0
            start_time = time.time()
            timeout = 30  # seconds
            matched_file_id = None
            
            while time.time() - start_time < timeout:
                ret, frame = cap.read()
                if not ret:
                    break
                
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                face_locations = face_recognition.face_locations(frame_rgb)
                
                if face_locations:
                    encodings = face_recognition.face_encodings(frame_rgb, face_locations)
                    for encoding, (top, right, bottom, left) in zip(encodings, face_locations):
                        face_distance = face_recognition.face_distance([uploaded_encodings], encoding)[0]
                        confidence = (1 - face_distance) * 100
                        best_confidence = max(best_confidence, confidence)
                        
                        if confidence > 60:
                            # Annotate the matched frame
                            cv2.rectangle(frame, (left, top), (right, bottom), (0, 255, 0), 2)
                            text = f"Match: {confidence:.2f}% - {scan_data['scan_date']} {scan_data['scan_time']}"
                            cv2.putText(frame, text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                            
                            # Save the matched frame to GridFS
                            _, frame_encoded = cv2.imencode('.jpg', frame)
                            frame_bytes = frame_encoded.tobytes()
                            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                            matched_filename = f"matched_{timestamp}.jpg"
                            matched_file_id = gridfs.put(frame_bytes, filename=matched_filename, content_type='image/jpeg')
                            
                            # Save the report with missing person details
                            reports_collection = get_reports_db()
                            try:
                                reports_collection.insert_one({
                                    'user_id': session['user_id'],
                                    'username': session['username'],
                                    'confidence': best_confidence,
                                    'scan_date': scan_data['scan_date'],
                                    'scan_time': scan_data['scan_time'],
                                    'reference_file_id': reference_file_id,
                                    'matched_file_id': str(matched_file_id),
                                    'missing_person': {
                                        'name': scan_data['name'],
                                        'age': scan_data['age'],
                                        'gender': scan_data['gender'],
                                        'last_seen_location': scan_data['last_seen_location'],
                                        'last_seen_date': scan_data['last_seen_date'],
                                        'last_seen_time': scan_data['last_seen_time'],
                                        'contact_number': scan_data['contact_number']
                                    },
                                    'created_at': datetime.now()
                                })
                                app.logger.info(f"Saved report with reference_file_id: {reference_file_id}, matched_file_id: {matched_file_id}")
                            except Exception as e:
                                app.logger.error(f"Database error: {str(e)}")
                                gridfs.delete(ObjectId(reference_file_id))
                                if matched_file_id:
                                    gridfs.delete(ObjectId(matched_file_id))
                                session.pop('scan_data', None)
                                return render_template('error.html',
                                                    message="Database error",
                                                    suggestion="Contact support or try again later",
                                                    current_time=datetime.now().strftime("%H:%M:%S"),
                                                    version="v2.4.7")
                            
                            # Update session with matched file ID
                            session['scan_data']['matched_file_id'] = str(matched_file_id)
                            session.modified = True
                            
                            session.pop('scan_data', None)
                            return render_template('result.html',
                                                confidence=f"{best_confidence:.2f}%",
                                                scan_date=scan_data['scan_date'],
                                                scan_time=scan_data['scan_time'],
                                                matched_file_id=str(matched_file_id),
                                                current_time=datetime.now().strftime("%H:%M:%S"),
                                                version="v2.4.7")
            
            # If no match is found, delete the GridFS files
            gridfs.delete(ObjectId(reference_file_id))
            session.pop('scan_data', None)
            return render_template('error.html',
                                 message=f"No match found (best: {best_confidence:.2f}%)",
                                 suggestion="Try again with better lighting",
                                 current_time=datetime.now().strftime("%H:%M:%S"),
                                 version="v2.4.7")
        
        except Exception as e:
            app.logger.error(f"Camera error: {str(e)}")
            gridfs.delete(ObjectId(reference_file_id))
            session.pop('scan_data', None)
            return render_template('error.html',
                                message="Camera processing error",
                                suggestion="Try restarting the application",
                                current_time=datetime.now().strftime("%H:%M:%S"),
                                version="v2.4.7")
        finally:
            cap.release()
            cv2.destroyAllWindows()
    
    except Exception as e:
        app.logger.error(f"Scanning error: {str(e)}")
        session.pop('scan_data', None)
        return render_template('error.html',
                             message="Scan processing failed",
                             suggestion="Try again later",
                             current_time=datetime.now().strftime("%H:%M:%S"),
                             version="v2.4.7")

@app.route('/reports')
def reports():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    try:
        reports_collection = get_reports_db()
        raw_reports = reports_collection.find({'user_id': session['user_id']}).sort('created_at', -1)
        reports = []
        
        gridfs = get_gridfs()
        for report in raw_reports:
            try:
                # Ensure required fields exist
                if 'missing_person' not in report or 'confidence' not in report:
                    app.logger.warning(f"Skipping invalid report: {report.get('_id')}")
                    continue
                
                # Prepare report data
                report_data = {
                    '_id': str(report['_id']),
                    'confidence': report.get('confidence', 0),
                    'scan_date': report.get('scan_date', 'N/A'),
                    'scan_time': report.get('scan_time', 'N/A'),
                    'missing_person': {
                        'name': report['missing_person'].get('name', 'N/A'),
                        'age': report['missing_person'].get('age', 'N/A'),
                        'gender': report['missing_person'].get('gender', 'N/A'),
                        'last_seen_location': report['missing_person'].get('last_seen_location', 'N/A'),
                        'last_seen_date': report['missing_person'].get('last_seen_date', 'N/A'),
                        'last_seen_time': report['missing_person'].get('last_seen_time', 'N/A'),
                        'contact_number': report['missing_person'].get('contact_number', 'N/A')
                    },
                    'reference_file_id': str(report['reference_file_id']) if report.get('reference_file_id') else None,
                    'matched_file_id': str(report['matched_file_id']) if report.get('matched_file_id') else None
                }
                
                # Verify GridFS files exist for downloads
                if report_data['reference_file_id']:
                    try:
                        gridfs.get(ObjectId(report_data['reference_file_id']))
                    except:
                        app.logger.warning(f"Reference file not found: {report_data['reference_file_id']}")
                        report_data['reference_file_id'] = None
                
                if report_data['matched_file_id']:
                    try:
                        gridfs.get(ObjectId(report_data['matched_file_id']))
                    except:
                        app.logger.warning(f"Matched file not found: {report_data['matched_file_id']}")
                        report_data['matched_file_id'] = None
                
                reports.append(report_data)
            
            except Exception as e:
                app.logger.error(f"Error processing report {report.get('_id')}: {str(e)}")
                continue
        
        if not reports and raw_reports.count() > 0:
            flash('Some reports could not be loaded due to missing or corrupted data.', 'warning')
        
        return render_template('reports.html', reports=reports)
    
    except Exception as e:
        app.logger.error(f"Database error in reports: {str(e)}")
        flash('Error retrieving reports. Database may be offline.', 'error')
        return redirect(url_for('index'))

@app.route('/uploads/<file_id>')
def serve_uploaded_file(file_id):
    try:
        gridfs = get_gridfs()
        file_obj = gridfs.get(ObjectId(file_id))
        return Response(file_obj.read(), mimetype=file_obj.content_type)
    except Exception as e:
        app.logger.error(f"File serve error for {file_id}: {str(e)}")
        flash('Image not found in database.', 'error')
        return redirect(url_for('reports'))

@app.route('/download/<file_id>')
def download_file(file_id):
    try:
        gridfs = get_gridfs()
        file_obj = gridfs.get(ObjectId(file_id))
        return Response(
            file_obj.read(),
            mimetype=file_obj.content_type,
            headers={'Content-Disposition': f'attachment; filename={file_obj.filename}'}
        )
    except Exception as e:
        app.logger.error(f"File download error for {file_id}: {str(e)}")
        flash('File not found in database.', 'error')
        return redirect(url_for('reports'))

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)