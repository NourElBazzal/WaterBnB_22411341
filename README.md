# WaterBnB_22411341
1-Contributors: Nour El Bazzal
2-Focus Areas:
3-Render URL: https://waterbnb-22411341.onrender.com
3-MongoDB Atlas Dahboard URL: https://charts.mongodb.com/charts-waterbnb-rbviwlt/public/dashboards/e2e2bd6c-0fd2-40c8-a9ff-b4c19fb0d610

# Curl example for the manual data insertion
curl -X POST -H "Content-Type: application/json" -d '{
"pool_id": "TEST",
"temperature": 24,
"light_intensity": 1000,
"hotspot": false,
"occupied": false,
"lat": 43.6,
"lon": 7.2
#}' https://your-app-url/api/add_pool
