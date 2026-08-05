
from math import atan2, asin, degrees, sqrt
import sys
from machine import I2C, Pin
from utime import sleep_ms
import icm20948

# force module reload
for mod in ["icm20948", "test_imu"]:
    if mod in sys.modules:
        del sys.modules[mod]

i2c = I2C(1, scl=38, sda=18, freq=400000)

imu = icm20948.ICM20948(i2c, dmp=True, debug=0)

if imu.dmp_ready:
    imu.DMP_enable_sensor("ACCELEROMETER", True)
    imu.DMP_enable_sensor("GYROSCOPE", True)
    imu.DMP_enable_sensor("ROTATION_VECTOR", True)
#   imu.DMP_enable_sensor("GAME_ROTATION_VECTOR", True)

def get_dmp_euler(q, scale_factor=1.0):
    # Keep right-handed coordinate frame:
    # Match physical chassis axes without double-negation hacks
    qx = q[0] * scale_factor
    qy = q[1] * scale_factor
    qz = q[2] * scale_factor

    v_sq = qx * qx + qy * qy + qz * qz

    # If scaled vector magnitude exceeds 1.0, clamp to prevent sqrt domain error
    if v_sq > 1.0:
        qx /= sqrt(v_sq)
        qy /= sqrt(v_sq)
        qz /= sqrt(v_sq)
        v_sq = 1.0

    q0 = sqrt(1.0 - v_sq)

    # Standard right-handed Roll (X-axis)
    t0 = 2.0 * (q0 * qx + qy * qz)
    t1 = 1.0 - 2.0 * (qx * qx + qy * qy)
    roll = degrees(atan2(t0, t1))

    # Standard right-handed Pitch (Y-axis)
    t2 = 2.0 * (q0 * qy - qz * qx)
    if t2 > 1.0:
        t2 = 1.0
    elif t2 < -1.0:
        t2 = -1.0
    pitch = degrees(asin(t2))

    # Standard right-handed Heading / Yaw (Z-axis)
    t3 = 2.0 * (q0 * qz + qx * qy)
    t4 = 1.0 - 2.0 * (qy * qy + qz * qz)
    heading = degrees(atan2(t3, t4))

    if heading < 0.0:
        heading += 360.0

    return heading, pitch, roll


while True:
    if imu.dmp_ready:
        imu.DMP_fifo_proceed()
        heading, pitch, roll = get_dmp_euler(imu._quat9)
        print("Heading: {0:7.3f} | Pitch: {1:7.3f} | Roll: {2:7.3f}".format(heading, pitch, roll))
    sleep_ms(250)

