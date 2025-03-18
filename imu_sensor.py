#!/usr/bin/env python

import smbus
import time
import os
import sys
import subprocess

# Data sheet for chip: https://www.nxp.com/docs/en/data-sheet/MMA8452Q.pdf 

i2c_addr = 0x1D # base i2c addr for our device

#### Commands ####
STATUS 			= 0x0
PL_STATUS 		= 0x10
SYSMOD         = 0x0B
XYZ_DATA_CFG 	= 0x0E
CTRL_REG1 		= 0x2A
PL_CFG 			= 0x11
PL_COUNT 		= 0x12
PL_BF_ZCOMP 	= 0x13

#######PL_STATUS Portrait/Landscape Status Register ##########
NEWLP_MASK         =   0x80
LO_MASK           =    0x40
LAPO1_MASK         =   0x04
LAPO0_MASK         =   0x02
BAFRO_MASK         =   0x01
LAPO_MASK           =  0x06

#######* PL_CFG Portrait/Landscape Configuration Register########
DBCNTM_MASK         =  0x80
PL_EN_MASK          =  0x40



Portrait_UP 		= 0x0 # Equipment standing vertically in the normal orientation
Portrait_DOWN 		= 0x1 # Equipment standing vertically in the inverted orientation
Landscape_RIGHT		= 0x2 # Equipment is in landscape mode to the right
Landscape_LEFT		= 0x3 # Equipment is in landscape mode to the left.

Orientation_Rotation = 0 # Offset into values above based on IMU attachment direction to the frame

def getAccelValue(data):
	Accl = (data[0] * 256 + data[1]) / 16
	if Accl > 2047 :
		Accl -= 4096
	return Accl

def getOrientation(bus):
		data = bus.read_i2c_block_data(i2c_addr, PL_STATUS, 1)
		newOrientation = False
		#print(data[0])
		if data[0] & NEWLP_MASK:
			newOrientation = True
		orientation = ((int(data[0] & 6)>>1)+Orientation_Rotation)%4
		#print("Orien: " + str(orientation))
		return newOrientation, orientation

def orientationString(orientation):
	return {
        Portrait_UP: "Portrait_UP",
		 Portrait_DOWN: "Portrait_DOWN",
		 Landscape_RIGHT: "Landscape_RIGHT",
	 	Landscape_LEFT: "Landscape_LEFT"
    }[orientation]

def configureOrientation(bus):
		CTRL_REG1_Data = bus.read_i2c_block_data(i2c_addr,CTRL_REG1, 1)[0]			#read contents of register 
		CTRL_REG1_Data &= 0xFE									#Set last bit to 0. 
		CTRL_REG1_Data &= 0xC7								#Clear the sample rate bits 
		
		#Bit 7 Bit 6 Bit 5 Bit 4 Bit 3 Bit 2 Bit 1 Bit 0
		#ASLP_RATE1 ASLP_RATE0 DR2 DR1 DR0 LNOISE F_READ ACTIVE
		# Sample rate defines
		# DR2 DR1 DR0 ODR Period
		#0 0 0 800 Hz 1.25 ms
		#0 0 1 400 Hz 2.5 ms
		#0 1 0 200 Hz 5 ms
		#0 1 1 100 Hz 10 ms
		#1 0 0 50 Hz 20 ms
		#1 0 1 12.5 Hz 80 ms
		#1 1 0 6.25 Hz 160 ms
		#1 1 1 1.56 Hz 640 ms

		#CTRL_REG1_Data |= 0x20								#Set the sample rate bits to 50 Hz 
		CTRL_REG1_Data |= 0x30								#Set the sample rate bits to 6.25 Hz 
		bus.write_byte_data(i2c_addr, CTRL_REG1,CTRL_REG1_Data );

		#Set the PL_EN bit in Register 0x11 PL_CFG. This will enable the orientation detection. 
		PLCFG_Data = bus.read_i2c_block_data(i2c_addr,PL_CFG, 1)[0]
		PLCFG_Data |= 0x40 
		bus.write_byte_data(i2c_addr, PL_CFG, PLCFG_Data)
		
		bus.write_byte_data(i2c_addr,PL_COUNT, 0x05)				#This sets the debounce counter to 100 ms at 50 Hz 
		
		CTRL_REG1_Data = bus.read_i2c_block_data(i2c_addr,CTRL_REG1, 1)[0]		#Read out the contents of the register 
		CTRL_REG1_Data |= 0x01							#Change the value in the register to Active Mode. 
		bus.write_byte_data(i2c_addr,CTRL_REG1, CTRL_REG1_Data)		#Write in the updated value to put the device in Active Mode 


def getAcceleration(bus):
	# Read data back from 0x00(0), 7 bytes
	# Status register, X-Axis MSB, X-Axis LSB, Y-Axis MSB, Y-Axis LSB, Z-Axis MSB, Z-Axis LSB
	data = bus.read_i2c_block_data(i2c_addr, STATUS, 7)

	# Convert the data
	xAccl = getAccelValue(data[1:3])
	yAccl = getAccelValue(data[3:5])
	zAccl = getAccelValue(data[5:7])
	return xAccl, yAccl, zAccl

def getSystemMode(bus):
		return bus.read_i2c_block_data(i2c_addr, SYSMOD, 1)[0]


def configureDevice(bus):
	# MMA8452Q address, 0x1D(28)
	# Select Control register, 0x2A(42)
	#		0x00(00)	StandBy mode
	bus.write_byte_data(i2c_addr, CTRL_REG1, 0x00)
	# Select Control register, 0x2A(42)
	#		0x01(01)	Active mode
	bus.write_byte_data(i2c_addr, CTRL_REG1, 0x01)
	# Select Configuration register, 0x0E(14)
	#		0x00(00)	Set range to +/- 2g
	bus.write_byte_data(i2c_addr, XYZ_DATA_CFG, 0x00)

def printAcceleration(bus):
	xAccl, yAccl, zAccl = getAcceleration(bus)
	# Output data to screen
	print ("Acceleration in X-Axis : %d" %xAccl)
	print ("Acceleration in Y-Axis : %d" %yAccl)
	print ("Acceleration in Z-Axis : %d" %zAccl)

def rotationCommand(orientation):
	return {
        Portrait_UP: "wlr-randr  --output HDMI-A-1 --transform normal",
		 Portrait_DOWN: "wlr-randr  --output HDMI-A-1 --transform 180",
		 Landscape_RIGHT: "wlr-randr  --output HDMI-A-1 --transform 90",
	 	Landscape_LEFT: "wlr-randr  --output HDMI-A-1 --transform 270"
    }[orientation]
#        Portrait_UP: "xrandr --output HDMI-1 --rotate right",
#		 Portrait_DOWN: "xrandr --output HDMI-1 --rotate left",
#		 Landscape_RIGHT: "xrandr --output HDMI-1 --rotate normal",
#	 	Landscape_LEFT: "xrandr --output HDMI-1 --rotate inverted"


def getXWindowsRotation():
	#xWinRotation = subprocess.check_output("xrandr -q --verbose | grep HDMI-1 | sed 's/primary //' | awk '{print $5}'", shell=True).decode(sys.stdout.encoding).rstrip('\n')
	xWinRotation = subprocess.check_output("wlr-randr --output HDMI-A-1 | grep Transform | awk '{print $2}'", shell=True).decode(sys.stdout.encoding).rstrip('\n')
	print ("Current XWin roatation: " + xWinRotation)
	return {
		"normal" : Portrait_UP,
		"180" : Portrait_DOWN,
		"90" : Landscape_RIGHT,
		"270" : Landscape_LEFT,
	}[xWinRotation]

def main():
	# Get I2C bus
	bus = smbus.SMBus(1)

	configureDevice(bus)
	time.sleep(0.4)
	configureOrientation(bus)
	time.sleep(0.4)
	_, extraCurrentOrientation = getOrientation(bus)
	time.sleep(0.2)
	_, currentOrientation = getOrientation(bus)
	#os.environ["DISPLAY"] = ":0.0"
	print ("Current orientation " + orientationString(currentOrientation) )
	if extraCurrentOrientation != currentOrientation:
		print ("Initial orientation changed! " + orientationString(currentOrientation) + " to " + orientationString(extraCurrentOrientation) )
	os.system(rotationCommand(currentOrientation))
	checkXWinRotation = 0 # check XWin matches what we think right away
	while 1:
		bNewOrientation, orientation = getOrientation(bus)
		#print("" + orientationString(orientation))
		if bNewOrientation or (checkXWinRotation == 0 and orientation != getXWindowsRotation()):
			getXWindowsRotation()
			print ("Orientation changed from " + orientationString(currentOrientation) + " to " + orientationString(orientation))
			os.system(rotationCommand(orientation))
			currentOrientation = orientation
		if checkXWinRotation == 0:
			checkXWinRotation = 60*5 # check against Xwindows view of the world every 5 minutes
		checkXWinRotation -= 1 
		time.sleep(1.0)

if __name__ == '__main__':
	main()
