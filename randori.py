import pygame
import OpenGL.GL as gl
import OpenGL.GLU as glu
import OpenGL.GLUT as glut
import time
import numpy as np
import sys
import argparse

rot_rate = 4
mov_rate = 0.1
nage_mov_rate = 0.1
radius = 0.4

sound = 0


def draw_checkered_floor():
    """Draws a large checkered floor using small gray quads."""
    size = 2       # Size of each individual square
    count = 20     # Number of squares in each direction

    gl.glDisable(gl.GL_LIGHTING)
    gl.glBegin(gl.GL_QUADS)
    for i in range(-count, count):
        for j in range(-count, count):
            # Alternate between light gray and dark gray
            if (i + j) % 2 == 0:
                gl.glColor3f(0.3, 0.3, 0.3)  # Dark gray
            else:
                gl.glColor3f(0.4, 0.4, 0.4)  # Light gray

            # Draw the square on the XZ plane (y = -1.7 to sit below spheres)
            y_pos = -1.7
            gl.glVertex3f(i * size, y_pos, j * size)
            gl.glVertex3f((i + 1) * size, y_pos, j * size)
            gl.glVertex3f((i + 1) * size, y_pos, (j + 1) * size)
            gl.glVertex3f(i * size, y_pos, (j + 1) * size)
    gl.glEnd()


def uke_init(how_many, distance):
    ukes = np.array([])
    gl.glEnable(gl.GL_LIGHTING)
    for i in range(how_many):
        uke = np.array([distance*(i-(how_many-1)/2), 0, 0])
        gl.glPushMatrix()           # Save current matrix state
        gl.glTranslatef(*uke)
        glut.glutSolidSphere(radius, 32, 32)
        gl.glPopMatrix()            # Restore matrix state for the next sphere
        ukes = np.vstack((ukes, uke)) if ukes.size else uke
    return ukes


def uke_update(ukes, nage):
    gl.glEnable(gl.GL_LIGHTING)
    new_ukes = np.array([[]])
    nage_coords = np.array(nage[0:3])  # just nage coordinates
    radius2 = radius*2

    for uke in ukes:  # FIXME this loop could be redone towards matrix opeartions for speed up
        random_direction = np.random.randn(3) - 0.5
        random_direction[1] = 0  # movment x,z only
        random_direction_unit = (random_direction
                                 / np.linalg.norm(random_direction))
        direction = nage_coords - uke
        direction_unit = direction / np.linalg.norm(direction)
        new_uke = (uke + (direction_unit * mov_rate)
                   + (random_direction * mov_rate * 0.1))  # 10% of randomness

        # nage detection
        if np.linalg.norm(nage_coords - uke) <= radius2:
            # print('Nage Caught!')
            beep()
            nage_direction_unit = nage[3:]
            new_uke = uke + (nage_direction_unit) * radius2 * 2
            # new_uke = new_uke + (direction_unit * mov_rate)*10
            gl.glMaterialfv(gl.GL_FRONT, gl.GL_DIFFUSE, (1, 0.3, 0.3, 1.0))
        else:
            gl.glMaterialfv(gl.GL_FRONT, gl.GL_DIFFUSE, (0.2, 0.8, 0.2, 1.0))

        # if new_uke does not touch other ukes allow for the move
        uke_distances = np.linalg.norm(new_uke - ukes, axis=1)
        if (np.sum((uke_distances > radius2))
                >= ukes.shape[0]-1):
            # the above is fster than the below
            # if all([np.linalg.norm(new_uke - o) > (radius2) for o in ukes if any(o != uke)]):
            pass
        else:
            new_uke = uke + (random_direction_unit * mov_rate)
        new_ukes = np.vstack((new_ukes, new_uke)
                             ) if new_ukes.size else new_uke
        gl.glPushMatrix()           # Save current matrix state
        gl.glTranslatef(*uke)
        glut.glutSolidSphere(radius, 32, 32)
        gl.glPopMatrix()            # Restore matrix state for the next sphere
    return new_ukes


def get_camera_position():
    """For OpenGL space it returns camera position and
    a normalized vector it points to"""

    # Get the 4x4 ModelView matrix
    modelview = gl.glGetFloatv(gl.GL_MODELVIEW_MATRIX)

    # The matrix is a 2D numpy-like array (flattened 16 elements)
    # Extract the rotation components (top-left 3x3)
    # and the translation components (elements 12, 13, 14)
    matrix = np.array(modelview).reshape(4, 4)

    # The camera position in world space is: -Rotation_Transpose * Translation
    rotation = matrix[:3, :3]     # 3x3 rotation part
    translation = matrix[3, :3]   # Translation part (x, y, z)

    # Calculate world position: pos = - (RT * T)
    camera_pos = -np.dot(rotation, translation)

    # Extract Forward Direction
    # In the ModelView matrix:
    # m[0,2], m[1,2], m[2,2] is the world-space Z-axis (Backward vector)
    # We negate it to get the Forward vector
    forward = -matrix[:3, 2]

    # Normalize the forward vector (just in case of scaling)
    forward = forward / np.linalg.norm(forward)

    return np.concatenate([camera_pos, forward])


def beep_init():
    global sound
    # Initialize mixer: 44.1kHz, 16-bit signed, mono
    pygame.mixer.init(44100, -16, 1)

    sample_rate = 44100
    frequency = 440.0
    duration = 0.3  # seconds

    # Generate sine wave
    t = np.linspace(0, duration, int(sample_rate * duration), False)
    # Scale to 16-bit integer range (-32768 to 32767)
    wave = np.sin(2 * np.pi * frequency * t) * 32767
    buffer = wave.astype(np.int16)

    sound = pygame.mixer.Sound(buffer)


def beep():
    global sound
    if not pygame.mixer.get_busy():
        sound.play()


def main():
    nage = np.array([0,  # x
                     0,  # y
                     4,  # z
                     0,  # face dir x
                     0,  # face dir y
                     0])  # face dir z
    ukes = np.array([])

    parser = argparse.ArgumentParser()
    parser.add_argument('-f', '--full-screen',
                        help='full screen',
                        action="store_true")
    parser.add_argument('ukes',
                        help='number of ukes',
                        type=int)
    args = parser.parse_args()

    set_mode_flags = pygame.DOUBLEBUF | pygame.OPENGL
    if args.full_screen:
        set_mode_flags |= pygame.FULLSCREEN

    # if len(sys.argv) != 2:
    #     print(f'Randori simulator.\nUsage: {sys.argv[0]} number_of_ukes')
    #     exit(1)
    number_of_ukes = args.ukes

    pygame.init()
    clock = pygame.time.Clock()

    glut.glutInit()
    display = (1280, 720)
    screen = pygame.display.set_mode(display,  set_mode_flags)
                                     # pygame.DOUBLEBUF
                                     # | pygame.OPENGL
                                     # | pygame.FULLSCREEN
                                     # )
    pygame.display.set_caption(sys.argv[0])

    beep_init()

    gl.glMatrixMode(gl.GL_PROJECTION)
    glu.gluPerspective(45, (display[0]/display[1]), 0.1, 50.0)

    # glTranslatef(0.0,0.0, -5)

    # 4. Setup Lighting (Makes the sphere look 3D rather than a flat circle)
    gl.glEnable(gl.GL_DEPTH_TEST)
    gl.glEnable(gl.GL_LIGHTING)
    gl.glEnable(gl.GL_LIGHT0)
    gl.glLightfv(gl.GL_LIGHT0, gl.GL_POSITION, (5, 5, 5, 1))

    # Set material color (Greenish)
    gl.glMaterialfv(gl.GL_FRONT, gl.GL_DIFFUSE, (0.2, 0.8, 0.2, 1.0))

    # a must for FPS
    gl.glMatrixMode(gl.GL_MODELVIEW)
    glu.gluLookAt(nage[0], nage[1], nage[2], 0, 0, 0, 0, 1, 0)
    # gluLookAt(0, -8, 0, 0, 0, 0, 0, 0, 1)
    viewMatrix = gl.glGetFloatv(gl.GL_MODELVIEW_MATRIX)
    gl.glLoadIdentity()

    # init mouse movement and center mouse on screen
    displayCenter = [screen.get_size()[i] // 2 for i in range(2)]
    mouseMove = [0, 0]

    while True:
        pygame.event.pump()  # Let Pygame talk to X11
        # Check if the window is focused and visible
        if pygame.display.get_active():
            pygame.mouse.set_pos(displayCenter)
            # 2. Verify the OS actually moved it
            if list(pygame.mouse.get_pos()) == displayCenter:
                break
        # Small sleep so we don't cook the CPU while waiting for the OS
        pygame.time.delay(10)
    # 3. Now that it's centered, clear the MOUSEMOTION queue
    # so your simulator doesn't start with a massive 'jerk'
    pygame.event.clear()

    paused = False
    up_down_angle = 0
    right_left_angle = 0

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                exit(0)
            if event.type == pygame.KEYDOWN or event.type == pygame.KEYUP:
                pressed = pygame.key.get_pressed()
                if pressed[pygame.K_q] or pressed[pygame.K_ESCAPE]:
                    pygame.quit()
                    exit(0)
                if (
                        pressed[pygame.K_PAUSE]
                        or pressed[pygame.K_p]
                        or pressed[pygame.K_SPACE]):
                    paused = not paused
                    # print(paused)
                    if paused:
                        print("Paused")
                    else:
                        print("Unpaused")
                        # pygame.key.set_repeat(300,10)
                        # pygame.mouse.set_pos(displayCenter)

                if pressed[pygame.K_i]:
                    print('Nage position: {}'.format(nage))
            if event.type == pygame.MOUSEMOTION:
                if not paused:
                    mouseMove = [event.pos[i] - displayCenter[i]
                                 for i in range(2)]
                    pygame.mouse.set_pos(displayCenter)

        if paused:
            time.sleep(0.05)
            continue

        # init model view matrix
        gl.glLoadIdentity()

        # apply the look up and down
        up_down_angle += mouseMove[1]*0.1
        gl.glRotatef(up_down_angle, 1.0, 0.0, 0.0)
        # init the view matrix
        gl.glPushMatrix()
        gl.glLoadIdentity()

        pressed = pygame.key.get_pressed()
        if pressed[pygame.K_s]:
            gl.glTranslatef(0, 0, -nage_mov_rate)
        if pressed[pygame.K_w]:
            gl.glTranslatef(0, 0, nage_mov_rate)
        if pressed[pygame.K_a]:
            gl.glTranslatef(nage_mov_rate, 0, 0)
        if pressed[pygame.K_d]:
            gl.glTranslatef(-nage_mov_rate, 0, 0)
        if pressed[pygame.K_LEFT]:
            gl.glRotatef(-rot_rate, 0, 1, 0)
        if pressed[pygame.K_RIGHT]:
            gl.glRotatef(rot_rate, 0, 1, 0)

        # rotate left and right
        right_left_angle = mouseMove[0]*0.1
        gl.glRotatef(right_left_angle, 0, 1, 0)

        # multiply the current matrix by the get the new view matrix
        # and store the final vie matrix
        gl.glMultMatrixf(viewMatrix)
        viewMatrix = gl.glGetFloatv(gl.GL_MODELVIEW_MATRIX)

        nage = get_camera_position()

        # apply view matrix
        gl.glPopMatrix()
        gl.glMultMatrixf(viewMatrix)

        gl.glClear(gl.GL_COLOR_BUFFER_BIT | gl.GL_DEPTH_BUFFER_BIT)

        draw_checkered_floor()

        if ukes.size == 0:
            ukes = uke_init(number_of_ukes, 1.5)
        else:
            ukes = uke_update(ukes, nage)

        pygame.display.flip()
        clock.tick(30)  # 30 fps

        # pygame.time.wait(10)


if __name__ == '__main__':
    main()
