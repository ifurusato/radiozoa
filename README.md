# The Radiozoa Robot

The Radiozoa is a third-generation autonomous robot implemented on a single 160mm 
diameter PC board. The hardware architecture integrates eight VL53L1X Time-of-Flight 
(ToF) distance sensors, a WeAct ESP32-S3-FH4R2 microcontroller, a DRV8833 two-channel 
motor driver, a 5V 3A buck-boost regulator, and a 3.3V to 5V level shifter to drive a 
NeoPixel ring. The rough cost of building this robot was targeted at around US$100.


# The Radiozoa Robot Operating System (RROS)

The Radiozoa Robot Operating System (RROS) is written in MicroPython and coordinates multiple 
concurrent behaviors by blending their target velocities into a single movement vector, which 
is then mapped to a two-wheel differential drive chassis. The primary input comes from the 
Radiozoa behavior module, which calculates desired lateral (vx), longitudinal (vy), and rotational 
(omega) values based on distance data from the eight ToF sensors, which feature a 1cm accuracy over 
a 4m range. Because a differential drive robot cannot physically move laterally, the motor controller 
converts the vx component into an auxiliary rotational value. This forces the robot to rotate its 
chassis away from closer obstacles, turning a lateral error into a heading correction. The system 
functions as a closed feedback loop where the physical environment acts as the frame of reference, 
allowing the robot to center itself without an IMU.

Once the final target velocities for the port and starboard motors are calculated, they pass through 
a low-level processing pipeline. This pipeline applies controller-level speed modifiers, executes 
per-side motor trim calibration, and clamps the output within safe hardware limits. To ensure smooth 
execution on the ESP32-S3 microcontroller, an exponential moving average is applied to the power 
outputs to eliminate timing jitter and erratic motor changes. The entire software implementation is 
optimized for MicroPython, using low-allocation routines and minimal thread locking to prevent runtime 
latency spikes during garbage collection.

The MotorController executes forward velocity kinematics, taking a desired body-level velocity vector 
(vx, vy, omega) and mapping it directly to individual wheel velocities:

* **The Behavioral Mapping:** First, the controller takes the unachievable lateral intent (vx) and 
    projects it into the rotational domain by setting the final rotational velocity to the sum of 
    omega and the product of the lateral gain and vx. This represents a behavioral translation to 
    handle the non-holonomic constraint rather than a pure kinematic equation.
* **The Kinematic Mixing:** It then applies standard forward differential kinematics to split that 
    adjusted body velocity into explicit wheel speeds: the port forward target equals vy plus the 
    final rotational velocity, and the starboard forward target equals vy minus the final rotational velocity.

Because this relies on a direct algebraic distribution of the target body velocities straight to the 
wheel actuators, the pipeline falls strictly under standard forward wheel kinematics.


# Generalised

Note that while the hardware uses a custom PB board, this software could be used with any set of 1-8
VL53L0X or VL53L1X sensors and an ESP32, with the code easily ported to a different microcontroller
family by making necessary changes to the I2C pin configuration and the pins chosen for the eight 
connections to the XSHUT pins on each of the eight ToF sensors. The specific configuraiton may be
found at the bottom of the Device class.


## Configuration

To manage this configuration, the system utilizes eight dedicated GPIO pins on the ESP32-S3, with each 
pin wired directly to the hardware shutdown (XSHUT) pin of a corresponding VL53 sensor. By driving these 
lines low, the initialization routine forces all sensors into a hardware standby state at startup. 

The system then pulls a single XSHUT line high to wake a target sensor, assigns it a new address via 
the I2C bus, and leaves it active while repeating the process for the next sensor in the sequence. 
This combination of discrete GPIO control lines and sequential software addressing safely resolves the 
address conflict without requiring external multiplexing hardware.


## References

See: [WeAct ESP32-S3-FH4R2](https://github.com/WeActStudio/WeActStudio.ESP32S3-MINI.git)

