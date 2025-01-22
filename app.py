import json
import csv
import threading
import time

from flask import request
from flask import jsonify
from flask import Flask
from flask import session
from flask import render_template
from flask_socketio import SocketIO


#https://python-adv-web-apps.readthedocs.io/en/latest/flask.html
#https://www.emqx.com/en/blog/how-to-use-mqtt-in-flask
from flask_mqtt import Mqtt
from flask_pymongo import PyMongo
from pymongo import MongoClient
import datetime

#%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
# Initialisation :  Mongo DataBase
from urllib.parse import quote_plus

username = quote_plus("nourbazzal4")
password = quote_plus("nour@mongodb2025")  # Escape any special characters
cluster_url = "iot.rll4q.mongodb.net"
database_name = "WaterBnB"

connection_string = f"mongodb+srv://{username}:{password}@{cluster_url}/{database_name}?retryWrites=true&w=majority"


# Connect to Cluster Mongo : attention aux permissions "network"/MONGO  !!!!!!!!!!!!!!!!
ADMIN=False # Faut etre ADMIN/mongo pour ecrire dans la base
#client = MongoClient("mongodb+srv://menez:i.....Q@cluster0.x0zyf.mongodb.net/?retryWrites=true&w=majority")
#client = MongoClient("mongodb+srv://logincfsujet:pwdcfsujet@cluster0.x0zyf.mongodb.net/?retryWrites=true&w=majority")
#client = MongoClient("mongodb+srv://visitor:doliprane@cluster0.x0zyf.mongodb.net/?retryWrites=true&w=majority")
client = MongoClient(connection_string)
print(client.list_database_names())

#-----------------------------------------------------------------------------
# Looking for "WaterBnB" database in the cluster
#https://stackoverflow.com/questions/32438661/check-database-exists-in-mongodb-using-pymongo
dbname= 'WaterBnB'
dbnames = client.list_database_names()
if dbname in dbnames: 
    print(f"{dbname} is there!")
else:
    print("YOU HAVE to CREATE the db !\n")

db = client.WaterBnB

collection = db["pools"]

#-----------------------------------------------------------------------------
# Fetch all documents
documents = list(collection.find())
if documents:
    print(f"The 'pools' collection contains {len(documents)} document(s):")
    for doc in documents:
        print(doc)
else:
    print("The 'pools' collection is empty.")
    

#-----------------------------------------------------------------------------
# Looking for "users" collection in the WaterBnB database
collname= 'users'
collnames = db.list_collection_names()
if collname in collnames: 
    print(f"{collname} is there!")
else:
    print(f"YOU HAVE to CREATE the {collname} collection !\n")
    
userscollection = db.users

#-----------------------------------------------------------------------------
# import authorized users .. if not already in ?
if ADMIN :
    userscollection.delete_many({})  # empty collection
    excel = csv.reader(open("usersM1_2025.csv")) # list of authorized users
    for l in excel : #import in mongodb
        ls = (l[0].split(';'))
        #print(ls)
        if userscollection.find_one({"name" : ls[0]}) ==  None :
            userscollection.insert_one({"name": ls[0], "num": ls[1]})
    

#%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
# Initialisation :  Flask service
app = Flask(__name__)

# Notion de session ! .. to share between routes !
# https://flask-session.readthedocs.io/en/latest/quickstart.html
# https://testdriven.io/blog/flask-sessions/
# https://www.fullstackpython.com/flask-globals-session-examples.html
# https://stackoverflow.com/questions/49664010/using-variables-across-flask-routes
app.secret_key = 'BAD_SECRET_KEY'

socketio = SocketIO(app)
  
#-----------------------------------------------------------------------------
@app.route('/')
def dashboard():
    return render_template('index.html')

#Test with =>  curl curl -X POST https://waterbnb-22411341.onrender.com/

#-----------------------------------------------------------------------------
@app.route('/api/pools', methods=['GET'])
def get_pools():
    pools = list(db.pools.find({}, {'_id': 0}))  # Exclude MongoDB's _id field
    return jsonify(pools)

#-----------------------------------------------------------------------------
# Add users to the users pool: i added this endpoint since i had problems with the csv file when trying to add its data to the users collection (yes i set the Admin as True)
# Test with curl -X POST https://waterbnb-22411341.onrender.com/api/add_user
@app.route('/api/add_user', methods=['POST'])
def add_users_from_pools():
    try:
        # Fetch all pools from the collection
        pools = list(db.pools.find({}, {"_id": 0, "user": 1, "pool_id": 1}))

        # Track added users
        added_users = []
        existing_users = []

        for pool in pools:
            user_name = pool.get("user")
            user_id = pool.get("pool_id")

            if user_name and user_id:
                # Check if the user already exists in the users collection
                if not userscollection.find_one({"name": user_name}):
                    # Add user to the users collection
                    userscollection.insert_one({"name": user_name, "num": user_id})
                    added_users.append(user_name)
                else:
                    existing_users.append(user_name)

        return jsonify({
            "message": "User addition completed",
            "added_users": added_users,
            "existing_users": existing_users
        }), 201

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    

#-----------------------------------------------------------------------------
#Resets the LED color for a pool to green after 30 seconds.
def reset_led(pool_id):
    time.sleep(30)  # Wait for 30 seconds
    mqtt_message = {"pool_id": pool_id, "led_color": "green"}
    
    # Publish the reset message to MQTT
    mqtt_client.publish("uca/iot/piscine", json.dumps(mqtt_message))
    print(f"LED for Pool {pool_id} reset to green.")



@app.route("/open", methods=['GET', 'POST'])
def openthedoor():
    idu = request.args.get('idu')  # User ID (clientid)
    idswp = request.args.get('idswp')  # Pool ID
    session['idu'] = idu
    session['idswp'] = idswp
    print(f"\nAccess request from User: {idu} for Pool: {idswp}")

    # Initialize response data
    granted = "NO"
    feedback_message = ""
    led_color = "green"  # Default color is green for available

    # Step 1: Check if the user exists in the users collection
    user_exists = userscollection.find_one({"num": idu}) is not None
    if not user_exists:
        feedback_message = "User is not registered."
        led_color = "red"  # Deny access if user is not registered
    else:
        # Step 2: Check if the pool exists and is not occupied
        pool = db.pools.find_one({"pool_id": idswp})
        if pool is None:
            feedback_message = "Pool does not exist."
            led_color = "red"  # Deny access if pool does not exist
        elif pool.get("occuped") == True:
            feedback_message = "Pool is already occupied."
            led_color = "red"  # Deny access if pool is occupied

            # Schedule LED reset to green after 30 seconds
            threading.Thread(target=reset_led, args=(idswp,)).start()
        else:
            # Access granted
            granted = "YES"
            feedback_message = "Access granted. Pool is now occupied."
            led_color = "yellow"  # Occupied pool color

            # Update pool status to occupied in MongoDB
            db.pools.update_one({"pool_id": idswp}, {"$set": {"occuped": True}})

    # Publish the LED color change via MQTT
    mqtt_message = {"pool_id": idswp, "led_color": led_color}
    result= mqtt_client.publish("uca/iot/piscine", json.dumps(mqtt_message))
    print(f"Published MQTT message: {mqtt_message}, Result: {result}")

    # Log the access attempt in the access_logs collection
    db.access_logs.insert_one({
        "client_id": idu,
        "pool_id": idswp,
        "access_granted": granted,
        "feedback_message": feedback_message,
        "timestamp": datetime.datetime.utcnow()
    })

    # Return response
    return jsonify({
        "idu": session['idu'],
        "idswp": session['idswp'],
        "granted": granted,
        "feedback": feedback_message
    }), 200

#-----------------------------------------------------------------------------
#Test with https://waterbnb-22411341.onrender.com/api/access_logs
@app.route('/api/access_logs', methods=['GET'])
def get_access_logs():
    logs = list(db.access_logs.find({}, {'_id': 0}))  # Exclude MongoDB's `_id` field
    return jsonify(logs)

#-----------------------------------------------------------------------------
#Inserting data manually using the following endpoint:
@app.route('/api/add_pool', methods=['POST'])
def add_pool():
    try:
        data = request.json
        db.pools.insert_one(data)
        return jsonify({"message": "Pool added successfully"}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 400

#-----------------------------------------------------------------------------
@app.route("/users")
def lists_users(): # Liste des utilisateurs déclarés
    """
    https://waterbnb-22411341.onrender.com/users
    """
    todos = userscollection.find()
    return jsonify([todo['name'] for todo in todos])

@app.route('/publish', methods=['POST'])
def publish_message():
    """
    mosquitto_sub -h test.mosquitto.org -t gillou
    mosquitto_pub -h test.mosquitto.org -t gillou -m tutu
    curl -X POST -H Content-Type:application/json -d "{\"topic\":\"gillou\",\"msg\":\"hello\"}"  https://waterbnbf.onrender.com/publish
    """
    content_type = request.headers.get('Content-Type')
    print("\n Content type = {}".format(content_type))
    request_data = request.get_json()
    print("\n topic = {}".format(request_data['topic']))
    
    publish_result = mqtt_client.publish(request_data['topic'], request_data['msg'])
    return jsonify({'code': publish_result[0]})

#%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%        
# Initialisation MQTT
app.config['MQTT_BROKER_URL'] =  "test.mosquitto.org"
app.config['MQTT_BROKER_PORT'] = 1883
#app.config['MQTT_USERNAME'] = ''  # Set this item when you need to verify username and password
#app.config['MQTT_PASSWORD'] = ''  # Set this item when you need to verify username and password
#app.config['MQTT_KEEPALIVE'] = 5  # Set KeepAlive time in seconds
app.config['MQTT_TLS_ENABLED'] = False  # If your broker supports TLS, set it True

topicname = "uca/iot/piscine"
mqtt_client = Mqtt(app)

@mqtt_client.on_connect()
def handle_connect(client, userdata, flags, rc):
   if rc == 0:
       print('Connected successfully')
       mqtt_client.subscribe(topicname) # subscribe topic
   else:
       print('Bad connection. Code:', rc)
       

@mqtt_client.on_message()
def handle_mqtt_message(client, userdata, msg):
    try:
        # Decode the MQTT message
        message = msg.payload.decode()
        data = json.loads(message)
        print(f"Received data: {data}")

        # Extract pool details
        pool_id = data["info"]["ident"]
        user= data["info"]["user"]
        lat = data.get("location", {}).get("gps", {}).get("lat", None)
        lon = data.get("location", {}).get("gps", {}).get("lon", None)
        temperature = data["status"]["temperature"]
        #light_intensity = data["status"]["light_intensity"]
        #fire_detected = data["status"]["fire_detected"]
        hotspot = data["piscine"]["hotspot"]
        occuped = data["piscine"]["occuped"]
        
        # Create or update the pool document in MongoDB
        db.pools.update_one(
            {"pool_id": pool_id},  # Match by pool ID
            {
                "$set": {
                    "lat": lat,
                    "lon": lon,
                    "temperature": temperature,
                    #"light_intensity": light_intensity,
                    #"fire_detected": fire_detected,
                    "user": user,
                    "hotspot": hotspot,
                    "occuped": occuped,
                    "last_updated": datetime.datetime.utcnow()
                }
            },
            upsert=True  # Insert if no matching document is found
        )
        print(f"Pool {pool_id} data inserted/updated in MongoDB.")
    except Exception as e:
        print(f"Error processing MQTT message: {e}")
        
    socketio.emit('update', data)  # Broadcast new data to all connected clients


#%%%%%%%%%%%%%  main driver function
if __name__ == '__main__':
    mqtt_client.subscribe(topicname)
    print(f"Subscribed to topic: {topicname}")
    # run() method of Flask class runs the application 
    # on the local development server.
    app.run(debug=False) #host='127.0.0.1', port=5000)
    