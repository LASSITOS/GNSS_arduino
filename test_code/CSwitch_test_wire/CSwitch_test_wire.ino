/*
 Uses library 
 by Mischianti Renzo <http://www.mischianti.org>

 https://www.mischianti.org/2019/01/02/pcf8574-i2c-digital-i-o-expander-fast-easy-usage/
*/



// --------------------------------
// Settings I2C
//---------------------------------

#include <Wire.h>


#define  CSwitchTx_address 0x24
#define  CSwitchCal_address 0x26
#define  MA12070P_address 0x20
uint8_t CSwitch =0 ;  // Controlling witch switch is open. 0 all a close.  1 for first, 2 for second,   4  for third. Sum for combinations. 
uint8_t  CSwitch_code =0xFF;


uint16_t addr;
char addrStr[5];
uint16_t dat;
char datStr[19];
uint32_t msg;
uint16_t out;
char txString2[50];
char txString[500];   // String containing messages to be send to BLE terminal
char subString[20];    




// /////////////////////////////////////////////
// --------------------------------
// I2C communication
//---------------------------------
// /////////////////////////////////////////////
void setCswitchTx ( uint8_t state ){

  //  CSwitch_code = 0xFF-((state>>2)*3 )<<6 ;// parse first bit
  //  CSwitch_code = CSwitch_code - ((state>>1)%2*3 )<<4 ;// parse second bit
  //  CSwitch_code = CSwitch_code - ((state)%2*3 )<<2  ;  // parse third bit
  CSwitch_code = 0xFF-state;

	 //Write message to the slave
	 Serial.printf("New state is: %d\n", state);
	 Serial.printf("Setting Cswitch #: 0X%x to: 0X%x\n", CSwitchTx_address,CSwitch_code);
	 Wire.beginTransmission(CSwitchTx_address); // For writing last bit is set to 0 (set to 1 for reading)
	 Wire.write(CSwitch_code );
	 uint8_t error = Wire.endTransmission(true);
	 Serial.printf("endTransmission: %u\n", error);
}


void setCswitchCal ( uint8_t state ){

	CSwitch_code = 0xFF-state;

	 //Write message to the slave
	 Serial.printf("New state is: %d\n", state);
	 Serial.printf("Setting Cswitch Cal #: 0X%x to: 0X%x\n", CSwitchCal_address,CSwitch_code);
	 Wire.beginTransmission(CSwitchCal_address); // For writing last bit is set to 0 (set to 1 for reading)
	 Wire.write(CSwitch_code );
	 uint8_t error = Wire.endTransmission(true);
	 Serial.printf("endTransmission: %u\n", error);
}

void write_I2C (uint8_t device, uint8_t address, uint8_t msg ){
  //Write message to the slave
  Serial.printf("Writing to reg: %x, msg: %x\n", address,msg);
  Wire.beginTransmission(device);
  Wire.write(address);
  Wire.write(msg);
  uint8_t error = Wire.endTransmission(true);
  Serial.printf("endTransmission: %u\n", error);
}


uint8_t readRegI2C (uint8_t device, uint8_t address){
  uint8_t bytesReceived=0;
  int temp=0;
  Serial.printf("Reading reg: %#02X\n", address);
  Wire.beginTransmission(device);
  Wire.write(address);
  uint8_t error = Wire.endTransmission(false);
  Serial.printf("endTransmission error: %u\n", error);
  //Read 16 bytes from the slave
  bytesReceived = Wire.requestFrom(device, 1);
  temp = Wire.read();
  Serial.printf("bytes received: %d\n", bytesReceived);
  Serial.printf("value: %x\n", temp);
  Serial.printf("value in decimal: %d\n", temp);
  return  temp;
}



// /////////////////////////////////////////////
// ---------------------------------------------
// Input parsing functions
// ---------------------------------------------
// /////////////////////////////////////////////
void parse( String rxValue){
	  //Start new data files if START is received and stop current data files if STOP is received
  if (rxValue.indexOf("SETTSW") != -1) {
	
	Serial.println("Setting new state for Tx CSwitch.");
    int index = rxValue.indexOf(":");
    int index2 = rxValue.indexOf(":",index+1);
    if (index !=-1 and index2 !=-1){
      rxValue.substring(index+1,index2).toCharArray(addrStr,5);
      CSwitch=strtoul (addrStr, NULL, 16);
      setCswitchTx (CSwitch);

    } else {
      sprintf(txString,"CSwitch state can not be parsed from string '%s''",rxValue);
      Serial.println(txString);
    }

  
    // Set new values on CSwitch calibration 
  }else if (rxValue.indexOf("SETCSW") != -1) {
 
  Serial.println("Setting new state for calibration coil CSwitch.");
    int index = rxValue.indexOf(":");\
    int index2 = rxValue.indexOf(":",index+1);
    if (index !=-1 and index2 !=-1){
      rxValue.substring(index+1,index2).toCharArray(addrStr,5);
      CSwitch=strtoul (addrStr, NULL, 16);
      setCswitchCal (CSwitch);

    } else {
      sprintf(txString,"CSwitch state can not be parsed from string '%s''",rxValue);
      Serial.println(txString);
    }

  
    // Read register  I2C
  }else if(rxValue.substring(0,4)== "I2CR" and rxValue.charAt(8)== 'R') {
	  char addrStr[5];
	  rxValue.substring(4,8).toCharArray(addrStr,5);
	  uint8_t addr=strtoul (addrStr, NULL, 16);
	  Serial.print("Reading register: ");
	  Serial.println(addr, HEX);
	  uint8_t out=readRegI2C ( MA12070P_address,addr);
	  sprintf(txString2,"Addr:%#02X Data:",addr);
	  Serial.print(txString2);
	  Serial.println(out,BIN);

	  
  // Write to register  I2C  
  } else if (rxValue.substring(0,4)== "I2CW" and (rxValue.charAt(8) == 'X' or rxValue.charAt(8) == 'B')) {
	  char addrStr[5];
	  char datStr[19];
	  uint8_t addr;
	  uint8_t dat;
	  
	  if(rxValue.charAt(8) == 'X'){
		  rxValue.substring(9,13).toCharArray(datStr,5);
		  Serial.print(datStr);
		  dat=strtoul (datStr, NULL, 16);
		
	  }else if(rxValue.charAt(8)== 'B'){
		   rxValue.substring(9,17).toCharArray(datStr,17);
           Serial.print(datStr);
		   dat=strtoul (datStr, NULL, 2);
	  }
	  rxValue.substring(4,8).toCharArray(addrStr,5);
	  addr=strtoul (addrStr, NULL, 16);
	  sprintf(txString2,"Writing register:%#02X Data:%#04X",addr);
	  Serial.print(txString2);
	  Serial.println(dat,BIN);
	  write_I2C(MA12070P_address,addr,dat);
  
  }else{
	Serial.println("Input could not be parsed!");
  } 	
}



// /////////////////////////////////////////////
// -%--------------------------------------------
// Setup and loop
// %%------------------------------------------------------------------------------------------------------------------------------
void setup(){

    Serial.begin(115200);


	// Initialize the I2C transmitter.	
	Wire.begin();	
	
	// Set the initial state of the pins on the PCF8574 devices
	Wire.beginTransmission(CSwitchTx_address); // device 1
    Wire.write(0x00); // all ports off
    uint8_t error = Wire.endTransmission();
    Serial.printf("endTransmission on CSwitch Tx: %u\n", error);
    Wire.begin();
    Wire.beginTransmission(CSwitchCal_address); // device 2
    Wire.write(0x00); // all ports off
    error = Wire.endTransmission();
    Serial.printf("endTransmission on CSwitch CalibCoil: %u\n", error);
  
}


void loop(){
 
  if (Serial.available()){ // Check Serial inputs
    String rxValue = Serial.readString();
    if (rxValue.length() > 0) {
      Serial.println("*********");
      Serial.print("Received Value: ");
      for (int i = 0; i < rxValue.length(); i++)
        Serial.print(rxValue[i]);
        Serial.println();
	      parse(rxValue);
      
      Serial.println("*********");
      }
  }  
  
  
  delay(50);
}
