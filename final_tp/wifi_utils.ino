/*** Basic/Static Wifi connection
     Fichier wificonnect/wifi_utils.ino ***/

#include <WiFi.h> // https://www.arduino.cc/en/Reference/WiFi
#include "wifi_utils.h"

#define USE_SERIAL Serial

/*--------------------------------------------------------------------------*/
String translateEncryptionType(wifi_auth_mode_t encryptionType) {
  //  encryptiontype to string      
  // cf https://www.arduino.cc/en/Reference/WiFiEncryptionType 
  switch (encryptionType) {
  case (WIFI_AUTH_OPEN):
    return "Open";
  case (WIFI_AUTH_WEP):
    return "WEP";
  case (WIFI_AUTH_WPA_PSK):
    return "WPA_PSK";
  case (WIFI_AUTH_WPA2_PSK):
    return "WPA2_PSK";
  case (WIFI_AUTH_WPA_WPA2_PSK):
    return "WPA_WPA2_PSK";
  case (WIFI_AUTH_WPA2_ENTERPRISE):
    return "WPA2_ENTERPRISE";
  }
}
/*--------------------------------------------------------------------------*/
void wifi_printstatus(int C){
  /* print the status of the connected wifi  in two ways ! */

  if (C){
    // Use Pure C =>  array of chars
    USE_SERIAL.printf("WiFi Status : \n");
    USE_SERIAL.printf("\tIP address : %s\n", WiFi.localIP().toString().c_str());
    USE_SERIAL.printf("\tMAC address : %s\n", WiFi.macAddress().c_str());
    USE_SERIAL.printf("\tSSID : %s\n", WiFi.SSID());
    USE_SERIAL.printf("\tReceived Signal Strength Indication : %ld dBm\n",WiFi.RSSI());
    USE_SERIAL.printf("\tReceived Signal Strength Indication : %ld %\n",constrain(2 * (WiFi.RSSI() + 100), 0, 100));
    USE_SERIAL.printf("\tBSSID : %s\n", WiFi.BSSIDstr().c_str());
    USE_SERIAL.printf("\tEncryption type : %s\n", translateEncryptionType(WiFi.encryptionType(0)));
  }
  else {
    // Use of C++ =>  String !
    String s = "WiFi Status : \n";
    //s += "\t#" + String() + "\n";
    s += "\tIP address : " + WiFi.localIP().toString() + "\n"; 
    s += "\tMAC address : " + String(WiFi.macAddress()) + "\n";
    s += "\tSSID : " + String(WiFi.SSID()) + "\n";
    s += "\tReceived Sig Strength Indication : " + String(WiFi.RSSI()) + " dBm\n";
    s += "\tReceived Sig Strength Indication : " + String(constrain(2 * (WiFi.RSSI() + 100), 0, 100)) + " %\n";
    s += "\tBSSID : " + String(WiFi.BSSIDstr()) + "\n";
    s += "\tEncryption type : " + translateEncryptionType(WiFi.encryptionType(0))+ "\n";
    USE_SERIAL.print(s);
  }
}
/*--------------------------------------------------------------------------*/
void wifi_connect_basic(String hostname, String ssid, String passwd){
  int nbtry = 0; // Nb of try to connect

  WiFi.mode(WIFI_OFF);   
  WiFi.mode(WIFI_STA); // Set WiFi to station mode 
  // delete old config
  // WiFi.config(INADDR_NONE, INADDR_NONE, INADDR_NONE, INADDR_NONE);
  WiFi.disconnect(true); // Disconnect from an AP if it was previously connected
  // WiFi.persistent(false); // Avoid to store Wifi configuration in Flash
  
  // Define hostname before begin => in C str ! not C++
  WiFi.setHostname(hostname.c_str()); 
  
  USE_SERIAL.printf("\nAttempting %d to connect AP of SSID : %s", nbtry, ssid.c_str());
  WiFi.begin(ssid.c_str(), passwd.c_str());
  //WiFi.begin(ssid.c_str(), passwd.c_str(), 0, WiFi.BSSID(thegoodone));
  while(WiFi.status() != WL_CONNECTED && (nbtry < WiFiMaxTry)){
    delay(SaveDisconnectTime); // 500ms seems to work in most cases, may depend on AP
    USE_SERIAL.print(".");
    nbtry++;
  }
  
  if (nbtry ==  WiFiMaxTry)
    ESP.restart();
}
/*--------------------------------------------------------------------------*/
int wifi_search_neighbor(){
  //  -90 dBm : niveau minimum permettant d'exploiter le signal
#define MinimumWiFiRSSI -90
  
  /* Scan of neighbor Networks -----*/
  int N = WiFi.scanNetworks(); 
  if (N>0){ // Print descriptions if some ?
    USE_SERIAL.print("\n-------------------\n");
    USE_SERIAL.printf("Networks found : # %d\n",N);
    for (int i=0 ; i<N ; i++){
      USE_SERIAL.printf("#%d => Signal Strength (higher is better): %ld dBm\n", i , WiFi.RSSI(i));
      delay(1000);  // slow it for serial 
    }
  }
  /* Choose one among -----*/
  int thegoodone = -1;
  for (int i=0 ; i<N ; i++){
    if (WiFi.RSSI(i) > MinimumWiFiRSSI) {
      thegoodone = i;
      USE_SERIAL.printf("The #%d  satisfies criteria !\n", thegoodone);
      break; // the first 
    }
  }
  return thegoodone;
}
/*--------------------------------------------------------------------------*/
void wifi_connect_multi(String hostname){
  int nbtry = 0; // Nb of try to connect
   
  WiFiMulti wm; // Creates an instance of the WiFiMulti class
  // Attention ! PAS arrivé à sortir l'instance de la fonction => heap error ! Why ???? 
  wm.addAP("HUAWEI-6EC2", "FGY9MLBL");
  wm.addAP("HUAWEI-553A", "QTM06RTT");
  wm.addAP("GMAP", "vijx47050");
  wm.addAP("AndroidAP9637", "16171617");
  wm.addAP("Livebox-B870","MYCNcZqnvsWsiy7s52");
  
  WiFi.mode(WIFI_OFF);   
  WiFi.mode(WIFI_STA); // Set WiFi to station mode 
  // delete old config
  // WiFi.config(INADDR_NONE, INADDR_NONE, INADDR_NONE, INADDR_NONE);
  WiFi.disconnect(true); // Disconnect from an AP if it was previously connected
  // WiFi.persistent(false); // Avoid to store Wifi configuration in Flash
  
  // Define hostname  => in C str ! not C++
  WiFi.setHostname(hostname.c_str());
  
  while(wm.run() != WL_CONNECTED && (nbtry < WiFiMaxTry)) {
    USE_SERIAL.printf("\nAttempting %d to connect AP", nbtry);  
    delay(SaveDisconnectTime);
    USE_SERIAL.print(".");
    nbtry++;
  }
  
  if(wm.run() == WL_CONNECTED) {
    USE_SERIAL.printf("\nwifiMulti connected on %s !", WiFi.SSID());
  }
  else{
    ESP.restart();
  }
}
