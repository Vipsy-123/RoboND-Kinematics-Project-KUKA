from sympy import *
from time import time
from mpmath import radians
import tf

'''
Format of test case is [ [[EE position],[EE orientation as quaternions]],[WC location],[joint angles]]
You can generate additional test cases by setting up your kuka project and running `$ roslaunch kuka_arm forward_kinematics.launch`
From here you can adjust the joint angles to find thetas, use the gripper to extract positions and orientation (in quaternion xyzw) and lastly use link 5
to find the position of the wrist center. These newly generated test cases can be added to the test_cases dictionary.
'''

test_cases = {1:[[[2.16135,-1.42635,1.55109],
                  [0.708611,0.186356,-0.157931,0.661967]],
                  [1.89451,-1.44302,1.69366],
                  [-0.65,0.45,-0.36,0.95,0.79,0.49]],
              2:[[[-0.56754,0.93663,3.0038],
                  [0.62073, 0.48318,0.38759,0.480629]],
                  [-0.638,0.64198,2.9988],
                  [-0.79,-0.11,-2.33,1.94,1.14,-3.68]],
              3:[[[-1.3863,0.02074,0.90986],
                  [0.01735,-0.2179,0.9025,0.371016]],
                  [-1.1669,-0.17989,0.85137],
                  [-2.99,-0.12,0.94,4.06,1.29,-4.12]],
              4:[],
              5:[]}


def test_code(test_case):
    ## Set up code
    ## Do not modify!
    x = 0
    class Position:
        def __init__(self,EE_pos):
            self.x = EE_pos[0]
            self.y = EE_pos[1]
            self.z = EE_pos[2]
    class Orientation:
        def __init__(self,EE_ori):
            self.x = EE_ori[0]
            self.y = EE_ori[1]
            self.z = EE_ori[2]
            self.w = EE_ori[3]

    position = Position(test_case[0][0])
    orientation = Orientation(test_case[0][1])

    class Combine:
        def __init__(self,position,orientation):
            self.position = position
            self.orientation = orientation

    comb = Combine(position,orientation)

    class Pose:
        def __init__(self,comb):
            self.poses = [comb]

    req = Pose(comb)
    start_time = time()
    
    ########################################################################################
    ## 

    ## Insert IK code here!


    # Create symbols
    q1, q2, q3, q4, q5, q6, q7 = symbols('q1:8') # theta_i
    d1, d2, d3, d4, d5, d6, d7 = symbols('d1:8')
    a0, a1, a2, a3, a4, a5, a6 = symbols('a0:7')
    alpha0, alpha1, alpha2, alpha3, alpha4, alpha5, alpha6 = symbols('alpha0:7') 
        
    # Create Modified DH parameters
    DH_table = { alpha0:            0,  a0:      0, d1:    0.75, 
                 alpha1: radians(-90),  a1:   0.35, d2:       0,  q2: q2-radians(90),
                 alpha2:            0,  a2:   1.25, d3:       0,
                 alpha3: radians(-90),  a3: -0.054, d4:    1.50,
                 alpha4:  radians(90),  a4:      0, d5:       0,
                 alpha5: radians(-90),  a5:      0, d6:       0,
                 alpha6:            0,  a6:      0, d7:   0.303}

    # Define Modified DH Transformation matrix
    def DH_TF_Matrix(alpha, a, d, q):
        T = Matrix([[            cos(q),           -sin(q),           0,             a],
                    [ sin(q)*cos(alpha), cos(q)*cos(alpha), -sin(alpha), -sin(alpha)*d],
                    [ sin(q)*sin(alpha), cos(q)*sin(alpha),  cos(alpha),  cos(alpha)*d],
                    [                 0,                 0,           0,             1]])
        return T

    # Create individual transformation matrices
    T0_1 = DH_TF_Matrix(alpha0, a0, d1, q1).subs(DH_table)
    T1_2 = DH_TF_Matrix(alpha1, a1, d2, q2).subs(DH_table)
    T2_3 = DH_TF_Matrix(alpha2, a2, d3, q3).subs(DH_table)
    T3_4 = DH_TF_Matrix(alpha3, a3, d4, q4).subs(DH_table)
    T4_5 = DH_TF_Matrix(alpha4, a4, d5, q5).subs(DH_table)
    T5_6 = DH_TF_Matrix(alpha5, a5, d6, q6).subs(DH_table)
    T6_EE = DH_TF_Matrix(alpha6, a6, d7, q7).subs(DH_table)
    
    T0_2 = (T0_1 * T1_2)
    T0_3 = (T0_2 * T2_3)
    T0_4 = (T0_3 * T3_4)
    T0_5 = (T0_4 * T4_5)
    T0_6 = (T0_5 * T5_6)
    T0_EE = (T0_6 * T6_EE)

    # Extract end-effector position and orientation from request
    # px,py,pz = end-effector position
    # roll, pitch, yaw = end-effector orientation
    px = req.poses[x].position.x
    py = req.poses[x].position.y
    pz = req.poses[x].position.z

    (roll, pitch, yaw) = tf.transformations.euler_from_quaternion(
        [req.poses[x].orientation.x, req.poses[x].orientation.y,
            req.poses[x].orientation.z, req.poses[x].orientation.w])

    # Correction Needed to Account of Orientation Difference Between Definition of
    # Gripper Link in URDF versus DH Convention
    def rot_x(q):
        R_x = Matrix([[      1,        0,        0],
                      [      0,   cos(q),  -sin(q)],
                      [      0,   sin(q),  cos(q)]])
        return R_x
    
    def rot_y(q):              
        R_y = Matrix([[ cos(q),        0,  sin(q)],
                      [      0,        1,       0],
                      [-sin(q),        0, cos(q)]]) 
        return R_y

    def rot_z(q):    
        R_z = Matrix([[ cos(q),  -sin(q),       0],
                      [  sin(q),   cos(q),       0],
                      [       0,        0,      1]])
        return R_z
        
    r, p, y = symbols('r p y')
    R_corr = rot_z(y).subs(y, radians(180))*rot_y(p).subs(p, radians(-90))
    
    R_EE = rot_z(y)*rot_y(p)*rot_x(r)
    R_EE = R_EE * R_corr
    
    R_EE = R_EE.subs({'r': roll, 'p': pitch, 'y': yaw})
    EE = Matrix([[px],
                 [py],
                 [pz]])
    WC = EE - DH_table[d7] * R_EE[:, 2]

    # Calculate joint angles using Geometric IK method
    theta1 = atan2(WC[1], WC[0])

    # SSS triangle for theta2 and theta3
    side_a = sqrt(DH_table[d4]*DH_table[d4] + DH_table[a3]*DH_table[a3])        
    r = sqrt(WC[0]*WC[0] + WC[1]*WC[1]) - DH_table[a1]
    s = WC[2] - DH_table[d1]            
    side_b = sqrt(r*r + s*s)
    side_c = DH_table[a2]

    angle_a = acos((side_b*side_b + side_c*side_c - side_a*side_a)/(2*side_b*side_c))
    angle_b = acos((side_c*side_c + side_a*side_a - side_b*side_b)/(2*side_c*side_a))
            
    theta2 = radians(90) - angle_a - atan2(s, r)
    theta3 = radians(90) - angle_b - atan2(DH_table[a3], DH_table[d4])

    # Inverse Orientation
    R0_3 = T0_1[0:3,0:3] * T1_2[0:3,0:3] * T2_3[0:3,0:3]
    R0_3 = R0_3.evalf(subs={q1: theta1, q2: theta2, q3:theta3})

    R3_6 = R0_3.transpose()*R_EE
    
    # Euler angles from rotation matrix
    theta5 = atan2(sqrt(R3_6[0,2]**2 + R3_6[2,2]**2), R3_6[1,2])
    # Choosing between multiple possible solutions:
    if sin(theta5) < 0:
        theta4 = atan2(-R3_6[2,2], R3_6[0,2])
        theta6 = atan2(R3_6[1,1], -R3_6[1,0])
    else:
        theta4 = atan2(R3_6[2,2], -R3_6[0,2])
        theta6 = atan2(-R3_6[1,1], R3_6[1,0])

    ## 
    ########################################################################################
    
    ########################################################################################
    ## For additional debugging add your forward kinematics here. Use your previously calculated thetas
    ## as the input and output the position of your end effector as your_ee = [x,y,z]

    ## (OPTIONAL) YOUR CODE HERE!
    FK = T0_EE.evalf(subs={q1: theta1, q2: theta2, q3: theta3, q4: theta4, q5: theta5, q6: theta6})
    ## End your code input for forward kinematics here!
    ########################################################################################

    ## For error analysis please set the following variables of your WC location and EE location in the format of [x,y,z]
    your_wc = [WC[0],WC[1], WC[2]] # <--- Load your calculated WC values in this array
    your_ee = [FK[0,3], FK[1,3], FK[2,3]] # <--- Load your calculated end effector value from your forward kinematics
    ########################################################################################

    ## Error analysis
    print ("\nTotal run time to calculate joint angles from pose is %04.4f seconds" % (time()-start_time))

    # Find WC error
    if not(sum(your_wc)==3):
        wc_x_e = abs(your_wc[0]-test_case[1][0])
        wc_y_e = abs(your_wc[1]-test_case[1][1])
        wc_z_e = abs(your_wc[2]-test_case[1][2])
        wc_offset = sqrt(wc_x_e**2 + wc_y_e**2 + wc_z_e**2)
        print ("\nWrist error for x position is: %04.8f" % wc_x_e)
        print ("Wrist error for y position is: %04.8f" % wc_y_e)
        print ("Wrist error for z position is: %04.8f" % wc_z_e)
        print ("Overall wrist offset is: %04.8f units" % wc_offset)

    # Find theta errors
    t_1_e = abs(theta1-test_case[2][0])
    t_2_e = abs(theta2-test_case[2][1])
    t_3_e = abs(theta3-test_case[2][2])
    t_4_e = abs(theta4-test_case[2][3])
    t_5_e = abs(theta5-test_case[2][4])
    t_6_e = abs(theta6-test_case[2][5])
    print ("\nTheta 1 error is: %04.8f" % t_1_e)
    print ("Theta 2 error is: %04.8f" % t_2_e)
    print ("Theta 3 error is: %04.8f" % t_3_e)
    print ("Theta 4 error is: %04.8f" % t_4_e)
    print ("Theta 5 error is: %04.8f" % t_5_e)
    print ("Theta 6 error is: %04.8f" % t_6_e)
    print ("\n**These theta errors may not be a correct representation of your code, due to the fact \
           \nthat the arm can have muliple positions. It is best to add your forward kinmeatics to \
           \nconfirm whether your code is working or not**")
    print (" ")

    # Find FK EE error
    if not(sum(your_ee)==3):
        ee_x_e = abs(your_ee[0]-test_case[0][0][0])
        ee_y_e = abs(your_ee[1]-test_case[0][0][1])
        ee_z_e = abs(your_ee[2]-test_case[0][0][2])
        ee_offset = sqrt(ee_x_e**2 + ee_y_e**2 + ee_z_e**2)
        print ("\nEnd effector error for x position is: %04.8f" % ee_x_e)
        print ("End effector error for y position is: %04.8f" % ee_y_e)
        print ("End effector error for z position is: %04.8f" % ee_z_e)
        print ("Overall end effector offset is: %04.8f units \n" % ee_offset)




if __name__ == "__main__":
    # Change test case number for different scenarios
    test_case_number = 1

    test_code(test_cases[test_case_number])