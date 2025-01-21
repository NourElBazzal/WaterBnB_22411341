import json
import csv
import math

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

#Test with =>  curl https://waterbnbf.onrender.com/

#-----------------------------------------------------------------------------
"""
#https://stackabuse.com/how-to-get-users-ip-address-using-flask/
@app.route("/ask_for_access", methods=["POST"])
def get_my_ip():
    ip_addr = request.remote_addr
    return jsonify({'ip asking ': ip_addr}), 200

# Test/Compare with  =>curl  https://httpbin.org/ip

#Proxies can make this a little tricky, make sure to check out ProxyFix
#(Flask docs) if you are using one.
#Take a look at request.environ in your particular environment :
@app.route("/ask_for_access", methods=["POST"])
def client():
    ip_addr = request.environ['REMOTE_ADDR']
    return '<h1> Your IP address is:' + ip_addr
"""

@app.route('/api/pools', methods=['GET'])
def get_pools():
    pools = list(db.pools.find({}, {'_id': 0}))  # Exclude MongoDB's _id field
    return jsonify(pools)

#https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/X-Forwarded-For
#If a request goes through multiple proxies, the IP addresses of each successive proxy is listed.
# voir aussi le parsing !


@app.route("/open", methods=['GET', 'POST'])
def openthedoor():
    idu = request.args.get('idu')  # User ID (clientid)
    idswp = request.args.get('idswp')  # Pool ID
    session['idu'] = idu
    session['idswp'] = idswp
    print("\n Peer = {}".format(idu))

    # Check if the user exists in the users collection
    user_exists = userscollection.find_one({"name": idu}) is not None
    granted = "YES" if user_exists else "NO"

    # Log the access attempt in MongoDB
    db.access_logs.insert_one({
        "client_id": idu,
        "pool_id": idswp,
        "access_granted": granted,
        "timestamp": datetime.datetime.utcnow()
    })

    # Return response
    return jsonify({'idu': session['idu'], 'idswp': session['idswp'], "granted": granted}), 200

# Test with => curl -X POST https://waterbnbf.onrender.com/open?who=gillou
# Test with => curl https://waterbnbf.onrender.com/open?who=gillou


#-----------------------------------------------------------------------------
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
    curl https://waterbnbf.onrender.com/users
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
        lat = data.get("location", {}).get("gps", {}).get("lat", None)
        lon = data.get("location", {}).get("gps", {}).get("lon", None)
        temperature = data["status"]["temperature"]
        light_intensity = data["status"]["light_intensity"]
        fire_detected = data["status"]["fire_detected"]
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
                    "light_intensity": light_intensity,
                    "fire_detected": fire_detected,
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
    