/*
 * params.h
 *
 *  Created on: 16 nov. 2017
 *      Author: fabien
 */

#ifndef PARAMS_H_
#define PARAMS_H_
#include "Arduino.h"
#include "arm_math.h"

//#define SIMULATOR

const int LED_PIN = 13;

/* BEGIN -----------------Motors & Odometry-------------------------- */
const int MOT3_PWM = 2;
const int MOT3_DIR = 3;
const int MOT3_ENCA = 11;
const int MOT3_ENCB = 12;

const int MOT1_PWM = 4;
const int MOT1_DIR = 5;
const int MOT1_ENCA = 24;
const int MOT1_ENCB = 25;

const int MOT2_PWM = 6;
const int MOT2_DIR = 7;
const int MOT2_ENCA = 26;
const int MOT2_ENCB = 27;


const float PWM_FREQUENCY = 915.527;
const int PWM_RESOLUTION = 8;
const int PWM_MAX = pow(2, PWM_RESOLUTION) - 5;

const float32_t INC_PER_MM = 7.554804140138556;

#define HOLONOMIC
const float CONTROL_PERIOD = 0.05;

const float32_t ROBOT_RADIUS = 185.0;

/* END ------------------- Motors & Odometry --------------------------*/

/* BEGIN ----------------------- HMI ----------------------------------*/
const int LED_RED = 19;
const int LED_GREEN = 20;
const int LED_BLUE = 18;
const int CORD = 21;
const int BUTTON1 = 10;
const int BUTTON2 = 9;

/* END ------------------------- HMI ----------------------------------*/

/* BEGIN ----------------------- IOs ----------------------------------*/
const HardwareSerial RASPI_COMMUNICATION_SERIAL = Serial1;
const int RASPI_COMMUNICATION_BAUDRATE = 115200;
const int DYNAMIXEL_CONTROL = 35;
const float IO_REPORT_PERIOD = 0.5;
const int WATER_DELIVERER_GREEN = 2;  // Dynamixel ID
const int WATER_DELIVERER_ORANGE = 4;  // Dynamixel ID
const int WATER_CANNON_GREEN = 23;
const int WATER_CANNON_ORANGE = 22;
const int SCORE_DISPLAY_DIO = 32;
const int SCORE_DISPLAY_CLK = 31;
const int BEE_ARM_GREEN = 16;
const int BEE_ARM_ORANGE = 15;
const int BALL_DETECTOR_GREEN = 37;
const int BALL_DETECTOR_ORANGE = 38;
const bool DYNA_TURN_CW = false;
const bool DYNA_TURN_CCW = true;
const int BAT_SIG = A21;
const int BAT_POW = A22;
const int BALL_DETECTOR_BALL_THR_GREEN = 950;
const int BALL_DETECTOR_NO_BALL_THR_GREEN = 750;
const int BALL_DETECTOR_BALL_THR_ORANGE = 500;
const int BALL_DETECTOR_NO_BALL_THR_ORANGE = 200;
/* END ------------------------- IOs ----------------------------------*/


const float POS_REPORT_PERIOD = 0.2;
const unsigned int TIME_SPEED_FAILSAFE = 1000;

#define HOLONOMIC

#if defined(HOLONOMIC)

extern arm_matrix_instance_f32 Dplus;
extern arm_matrix_instance_f32 D;

#else
#error "No Robot type defined (TRIKE, DIFFERENTIAL or HOLONOMIC)"
#endif

#endif /* PARAMS_H_ */
