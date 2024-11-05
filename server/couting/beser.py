import threading
from flask import Flask, request, jsonify,Response
import firebase_admin
from datetime import datetime
import cv2
import numpy as np
from ultralytics import YOLO
from zeroconf import ServiceInfo, Zeroconf
import socket
from sort import Sort  # Import SORT library
from flask_socketio import SocketIO, emit
import requests
import time
import base64
from threading import Thread
from firebase_admin import credentials, db

# Initialize the Firebase Admin SDK using your credentials JSON file
cred = credentials.Certificate('**************************.json')
firebase_admin.initialize_app(cred, {
    'databaseURL': '********************************'  # Replace with your database URL
})
app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins='*')

feed_active = False  # Flag to track whether feed is active
frame_width = 640 
# In-memory dictionary to store box_key and ip_address pairs
boxest = {}
ref = db.reference()
lock = threading.Lock()
# Store thread reference
detection_threads = {}
lights_on_one=False
lights_on_all=False
#contivity=False
Th=8
nol=1

class DetectionThread(threading.Thread):
    def __init__(self, target, args=(), **kwargs):
        super().__init__(target=target, args=args, **kwargs)
        self.stop_event = threading.Event() 
        
@app.route('/add_box', methods=['POST'])
def add_box():
    data = request.json
    box_key = data.get('box_key')
    ip_address = data.get('ip_address')
    
    if True:
        #boxes[box_key] = ip_address  # Store the relationship
        #
        ## Start detection in a new thread and save the reference
        #detection_thread = threading.Thread(target=detection, args=(ip_address,), daemon=True)
        #detection_threads[box_key] = detection_thread
        #detection_thread.start()
        
        return jsonify({'message': 'Box added successfully!', 'box_key': box_key, 'ip_address': ip_address}), 200

@app.route('/get_ip', methods=['GET'])
def get_ip():
    box_key = request.args.get('box_key')  # Get box key from query parameters
    
    if box_key in boxest:
        ip_address = boxest[box_key]  # Retrieve the associated IP address
        return jsonify({'box_key': box_key, 'ip_address': ip_address}), 200
    return jsonify({'message': 'Box key not found!'}), 404

def fetch_times_from_firebase(ip_add):
    try:
        # Reference to the start time and end time in Firebase
        start_time_ref = db.reference(f'Time/{ip_add}/ST')
        end_time_ref = db.reference(f'Time/{ip_add}/ET')
        
        # Fetching values from Firebase
        start_time_str = start_time_ref.get()
        end_time_str = end_time_ref.get()
        print(start_time_str,end_time_str)
        
        if start_time_str and end_time_str:
            # Convert the retrieved strings to datetime.time objects
            start_time = datetime.strptime(start_time_str, "%I:%M %p").time()
            end_time = datetime.strptime(end_time_str, "%I:%M %p").time()
            print(start_time, end_time)
            return start_time, end_time
        else:
            print("Start time or end time not found in Firebase.")
            return None, None
    except Exception as e:
        print(f"Error retrieving times from Firebase: {e}")
        return None, None
    
def switch_lights_on(count):
    try:
        url = f'http://{relay_ip}/lights/on'
        response = requests.post(url, data={'count': count})
        if response.status_code == 200:
            #if not contivity:
            #    contivity=True
            if not lights_on_one:
                update_light_status1(True)
                update_light_status2(True)
            print(f"Relay responded successfully: {response.text}")
        else:
            print(f"Failed to send request: {response.status_code}")
    except requests.RequestExceptiosn as e:
        #if not contivity:
        #    contivity=False
        db.reference(f'connectivity/{ipp}').set(False)
        print(f"Error communicating with relay: {e}")

def switch_lights_off(count):
    try:
        url = f'http://{relay_ip}/lights/off'
        response = requests.post(url, data={'count': count})
        if response.status_code == 200:
            if count==0:
                update_light_status1(False)
                update_light_status2(False)
            print(f"Relay responded successfully: {response.text}")
        else:
            print(f"Failed to send request: {response.status_code}")
    except requests.RequestException as e:
        #if not contivity:
        #    contivity=False
        db.reference(f'connectivity/{ipp}').set(False)
        print(f"Error communicating with relay: {e}")


    
def update_light_status1(status: bool):
    try:
        lights_ref = db.reference(f'Lights/{ipp}/all')
        lights_ref.set(status)  # Set the boolean value
        print(f"Updated light status to: {status}")
    except Exception as e:
        print(f"Error updating light status: {e}")

def update_light_status2(status: bool):
    try:
        lights_ref = db.reference(f'Lights/{ipp}/One')
        lights_ref.set(status)  # Set the boolean value
        print(f"Updated light status to: {status}")
    except Exception as e:
        print(f"Error updating light status: {e}")

@app.route('/save', methods=['POST'])
def save():
    data = request.json
    ipq = data.get('ip_address')
    Tha = data.get('TH')
    nola = data.get('NOL')
    relay_ip_ref = db.reference(f'ips/{ipq}')
    relay_ipe = relay_ip_ref.get()
    try:
       send_to_esp(Th=Tha,nol=nola,relay_ip=relay_ipe,ipq=ipq)
       print('done')
       return jsonify({'message': 'Configures'}), 200
    except:
       return jsonify({'message': 'No configuration'}), 400

@app.route('/connect', methods=['POST'])
def connect():
    data = request.json
    start_time, end_time = fetch_times_from_firebase(data.get('ip_address'))
    current_time = datetime.now().time()

    # Check if the current time is within the detection schedule
    if start_time <= current_time <= end_time:
        box_key = data.get('box_key')
        
        if box_key in detection_threads:
            # If the box_key already has a running detection thread, stop it
            detection_threads[box_key].stop_event.set()  # Signal the thread to stop

            # Wait for a moment to ensure the thread stops (without blocking)
            time.sleep(1)  # Add a small delay

            # Restart the detection thread with the current IP address
            ip_address = boxest[box_key]
            print(ip_address)
            detection_thread = DetectionThread(target=detection, args=(ip_address, box_key), daemon=True)
            detection_threads[box_key] = detection_thread  # Store the new thread
            detection_thread.start()  # Start the new thread

            return jsonify({'message': 'Detection thread restarted successfully!'}), 200
        else:
            # If box_key does not exist, we assume we are adding a new box
            ip_address = data.get('ip_address')
            print(ip_address)
            if box_key and ip_address:
                boxest[box_key] = ip_address  # Store the relationship
                print(boxest)
                # Start detection in a new thread and save the reference
                detection_thread = DetectionThread(target=detection, args=(ip_address, box_key), daemon=True)
                detection_threads[box_key] = detection_thread  # Store the thread
                detection_thread.start()  # Start the thread
                
                return jsonify({'message': 'Box added successfully!', 'box_key': box_key, 'ip_address': ip_address}), 200
            return jsonify({'message': 'Box key and IP address are required!'}), 400
    else:
        return jsonify({'message': 'Detection is closed!'}), 200

    

def send_to_esp(Th,nol,relay_ip,ipq):
    try:
        url = f'http://{relay_ip}/lights/config'
        print(Th,nol)
        response = requests.post(url,data={'countThreshold':Th,'lightsLessThanThreshold': nol})
        if response.status_code == 200:
            print(f"Relay responded successfully: {response.text}")
            db.reference(f'connectivity/{ipq}').set(True)
        else:
            print(f"Failed to send request: {response.status_code}")
    except requests.RequestException as e:
        #if not contivity:
        #    contivity=True
        db.reference(f'connectivity/{ipq}').set(False)
        print(f"Error communicating with relay: {e}")

@app.route('/toggle_detection', methods=['POST'])
def toggle_detection():
    global lights_on_all,lights_on_one
    data = request.json
    value= 1 if data.get('value') else 0
    ip= data.get('newKey')
    relay_ip_ref = db.reference(f'ips/{ip}')
    relay_ipe = relay_ip_ref.get()
    try:
        url = f'http://{relay_ipe}/lights/toggle'
        response = requests.post(url,data={'togl':value})
        if response.status_code == 200:
            lights_on_all=True
            lights_on_one=True
            print(f"Relay responded successfully: {response.text}")
        else:
            print(f"Failed to send request: {response.status_code}")      
        return jsonify({'message': 'Toggle detection route triggered successfully!'}), 200
    except Exception as e:
        db.reference(f'connectivity/{ip}').set(False)
        return jsonify({'error': str(e)}), 500


def detection(ip_address, box_key):
    global Th, nol, relay_ip, lights_on_all, lights_on_one, stop_event,ipp
    stop_event = threading.Event()
    person_count_stop_event = threading.Event()
    update_thread = None  # Declare update_thread here

    with lock:  # Ensure thread-safe access
        detection_threads[box_key] = DetectionThread(target=detection, args=(ip_address, box_key), daemon=True)
        detection_threads[box_key].stop_event = stop_event  # Assign the stop event to the thread      

    try:
        relay_ip_ref = db.reference(f'ips/{ip_address}')
        relay_ip = relay_ip_ref.get()
        ipp=ip_address
        model = YOLO('yolov8n.pt')
        tracker = Sort()

        cap = cv2.VideoCapture(3)
        if not cap.isOpened():
            print("Error: Could not open camera.")
            exit()


        zero_count_frames = 0
        cooldown_threshold = 30
        
        person_count_variable = 0
        previous_person_count = 0
        history_length = 20
        person_count_history = []


        ref1 = db.reference(f'Lights/{ip_address}/One')
        ref2 = db.reference(f'Lights/{ip_address}/all')
        lights_on_one = ref1.get()
        lights_on_all = ref2.get()
        #Th = ref3['TH']
        #nol = ref3['LTSO']
        running=True
        def update_person_count_to_firebase(ip_address, stop_event):
            ref = db.reference(f'NOP/{ip_address}')
            while not stop_event.is_set():
                ref.set(person_count_variable)  # Use a shared variable
                stop_event.wait(1)  # Sleep for 1 second
        
        #listener = ref2.listen(lights_on_all_listener)
        # Start the thread after the function is defined
        update_thread = Thread(target=update_person_count_to_firebase, args=(ip_address, person_count_stop_event))
        update_thread.start()
        
        while not stop_event.is_set():
            ret, frame = cap.read()
            personc = 0
        
            results = model(frame, verbose=False)
            detections = []
        
            for result in results:
                boxes = result.boxes.xyxy
                scores = result.boxes.conf
                class_ids = result.boxes.cls
        
                for i, box in enumerate(boxes):
                    x1, y1, x2, y2 = map(int, box)
                    conf = scores[i]
                    cls = int(class_ids[i])
                    if cls == 0 and conf > 0.4:
                        personc += 1
                        detections.append([x1, y1, x2, y2, conf])
                        cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                        cv2.putText(frame, f'Person {conf:.2f}', (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
            
            person_count_history.append(personc)
            if len(person_count_history) > history_length:
                person_count_history.pop(0)
        
            most_frequent_person_count = max(set(person_count_history), key=person_count_history.count)
            
            if most_frequent_person_count != previous_person_count:
                person_count_variable=most_frequent_person_count
                if 0 < most_frequent_person_count < 8 and not lights_on_one:
                    switch_lights_on(most_frequent_person_count)
                    lights_on_one = True
                    lights_on_all = False
                    zero_count_frames = 0  # Reset zero count frames
                    
                elif most_frequent_person_count >= 8 and not lights_on_all:
                    switch_lights_on(most_frequent_person_count)
                    lights_on_all = True
                    lights_on_one = True
                    zero_count_frames = 0  # Reset zero count frames
        
                elif 0 < most_frequent_person_count < 8 and (lights_on_all or lights_on_one):
                    zero_count_frames += 1
                    if zero_count_frames >= cooldown_threshold:
                       lights_on_all = False
                       switch_lights_off(most_frequent_person_count)
                       zero_count_frames = 0  # Reset zero count after switching off lights
                
                elif most_frequent_person_count == 0:
                    zero_count_frames += 1
                    if zero_count_frames >= cooldown_threshold:
                        if lights_on_one or lights_on_all:
                            lights_on_one = False
                            lights_on_all = False
                            switch_lights_off(most_frequent_person_count)
                            zero_count_frames = 0  # Reset zero count after switching off light
                # Update previous person count
                previous_person_count = most_frequent_person_count
            else:
               if most_frequent_person_count == 0:
                   zero_count_frames += 1
                   if zero_count_frames >= cooldown_threshold:
                       if lights_on_one or lights_on_all:
                           lights_on_one = False
                           lights_on_all = False
                           switch_lights_off(most_frequent_person_count)
                           zero_count_frames = 0  # Reset zero count after switching off lights
            cv2.putText(frame, f'Persons in Frame: {most_frequent_person_count}', (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 0, 0), 2)
            cv2.imshow('Detection', frame)
        
            if cv2.waitKey(1) & 0xFF == ord('q'):
                detection_threads[box_key].stop_event.set()
                
                if detection_threads[box_key].is_alive():
                    print(f'Stopping thread for box key: {box_key}')
                    detection_threads[box_key].join()  # Wait for the thread to finish
                    print(f'Thread for box key {box_key} has been stopped.')
                with lock:
                   boxest.pop(box_key, None)
                   detection_threads.pop(box_key, None)
                break
        
        cap.release()
        cv2.destroyAllWindows()
    except Exception as e:
        print(f"Error in detection thread: {e}")
    finally:
        # running = False
        #update_light_status1(False)
        #update_light_status2(False)
        #running=False
        #listener.close()
        person_count_stop_event.set()  # Signal the thread to stop
        if update_thread is not None:
            update_thread.join()  # Ensure update_thread is joined only if it's initialized
        print('closed')

@app.route('/stop', methods=['POST'])
def stop_detection():
    data = request.json
    box_key = data.get('box_key')
    print('stop')

    if box_key in detection_threads:
        # Signal the detection thread to stop
        detection_threads[box_key].stop_event.set()

        # Check if the thread is alive before joining
        if detection_threads[box_key].is_alive():
            print(f'Stopping thread for box key: {box_key}')
            detection_threads[box_key].join()  # Wait for the thread to finish
            print(f'Thread for box key {box_key} has been stopped.')

        # Clean up resources
        with lock:
            boxest.pop(box_key, None)
            detection_threads.pop(box_key, None)

        # Print current threads status
        if not detection_threads:
            print('No detection threads are currently running.')
        else:
            print(f'Current detection threads: {list(detection_threads.keys())}')

        return jsonify({'message': 'Detection thread stopped successfully!'}), 200
    else:
        print(f'Box key {box_key} not found or detection thread not running!')
        return jsonify({'message': 'Box key not found or detection thread not running!'}), 200


def switch_on(): 
    print('make different function for all lights onn')

def switch_off():
    print('make different function for all lights off')
# Adding a stop event to the detection thread
def start_detection_thread(box_key, ip_address):
    detection_thread = threading.Thread(target=detection, args=(ip_address,), daemon=True)
    detection_threads[box_key] = detection_thread
    detection_thread.start()

def generate_frames():
    global frame_width, feed_active
    cap = cv2.VideoCapture(3)

    if not cap.isOpened():
        return

    frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    print(f"Camera frame width: {frame_width}")

    while feed_active:  # Only run when feed_active is True
        ret, frame = cap.read()
        if not ret:
            break

        # Encode the frame as JPEG
        _, buffer = cv2.imencode('.jpg', frame)
        jpg_as_text = base64.b64encode(buffer).decode('utf-8')

        # Send the frame to the client
        socketio.emit('video_frame', jpg_as_text)

        socketio.sleep(0.02)  # Wait for a short period to simulate 30 FPS

    cap.release()
    print("Video feed stopped")


@socketio.on('connect')
def handle_connect():
    print('Client connected')


@socketio.on('disconnect')
def handle_disconnect():
    print('Client disconnected')


@app.route('/start_feed', methods=['POST'])
def start_feed():
    global feed_active
    feed_active = True
    socketio.start_background_task(generate_frames)
    return Response(status=200)


@app.route('/stop_feed', methods=['POST'])
def stop_feed():
    global feed_active
    feed_active = False
    return Response(status=200)


@app.route('/frame_width', methods=['GET'])
def get_frame_width():
    return jsonify({'frame_width': frame_width})


def register_mdns_service():
    # Get local IP address
    local_ip = socket.gethostbyname(socket.gethostname())
    
    # Create the service info for mDNS
    service_info = ServiceInfo(
        "_http._tcp.local.",   # Service type
        "MyFlaskServer._http._tcp.local.",  # Service name
        addresses=[socket.inet_aton(local_ip)],  # Local IP address (as bytes)
        port=5000,  # Port
        properties={},
        server="MyFlaskServer.local."
    )

    # Create a Zeroconf instance and register the service
    zeroconf = Zeroconf()
    zeroconf.register_service(service_info)
    
    return zeroconf

if __name__ == '__main__':
    # Register the mDNS service when the server starts
    zeroconf = register_mdns_service()
    try:
        socketio.run(app, host='0.0.0.0', port=5000)  # Use socketio.run instead of app.run
    finally:
        # Unregister the service on shutdown
        zeroconf.unregister_all_services()
        zeroconf.close()