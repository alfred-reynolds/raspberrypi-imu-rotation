# raspberrypi-imu-rotation
A python script to read the output of a MMA8452Q and rotate the display on the Raspberry PI. 
The script uses the smbus python module to communicate via I2C to a MMA8452Q chip (https://www.nxp.com/docs/en/data-sheet/MMA8452Q.pdf ).
It enables the Portrait/Landscape Status Register mode on the chip and issues xrandr rotate commands when a rotation is reported by the chip.
