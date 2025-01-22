# WaterBnB_22411341

**Contributors**
Nour El Bazzal

---

**Focus Areas**
+Advanced MongoDB Integration
1.Efficient data import and duplicate prevention mechanisms
2.Pool occupancy tracking and status updates
+Access Control and Logging
1.Multi-step validation for pool access requests.
2.Automatic logging of all access attempts
+RESTful API Design
1.Well-structured API endpoints for pools, users, and access logs.
+Pool Dashboard(index.html)
1.A searchable pool data table with dynamic updated via WebSockets.
2.Embedded MongoDB charts for real-time data visualization.
3.Interactove badges for pool occupancy and hotspot status.
4.Input search functionality to filter pools by ID
5.JavaScript integration to fetch and display data from /api/pools.

---

**Render URL**
[View Site](https://waterbnb-22411341.onrender.com)

---

**MongoDB Atlas Dashboard URL**
[View Dashboard](https://charts.mongodb.com/charts-waterbnb-rbviwlt/public/dashboards/e2e2bd6c-0fd2-40c8-a9ff-b4c19fb0d610)

---

**Note**
I wrote all the functions for the led strip color changes on the flask app and the .ino file but it's not working.
But when testing with mosquitto with the following command: mosquitto_pub -h test.mosquitto.org -t uca/iot/piscine -m "{\"pool_id\": \"P_22411341\", \"led_color\": \"yellow\"}" , it's working fine and the led strip is changing its color as it should be.
My serial monitor is only displaying one pool from the real-time connected pools, and i tried to fix this issue but it didn't work. I think that's why the led strip is not changing colors when trying to access a pool. :disappointed:

---

Thank you for your time :smile: :rocket: :100:
