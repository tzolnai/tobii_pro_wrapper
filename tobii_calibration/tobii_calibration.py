# -*- coding: utf-8 -*-

# Psychopy supported Tobii controller for the new Pro SDK

# Authors:
# Olivia Guayasamin (oguayasa@gmail.com) - Initial work as tobii-pro-wrapper (Date: 8/3/2017)
#(https://github.com/oguayasa/tobii_pro_wrapper)
#
# Tamás Zolnai (zolnaitamas2000@gmail.com) - Reworked / modified this module.

# License: Apache License 2.0, see LICENSE.txt for more details.

# Summary: Currently provides all functionality for running a FULL CALIBRATION
# ROUTINE for 5 and 9 point calibrations.

# Notes: This code is currently designed for working with a tobii eyetracker
# installed on the same device as the one for running experiments (laptop set-
# up with a single connected eyetracker, no external monitors, and no tobii
# external processors). It should be straightforward to adapt to other
# computer/monitor set-ups, but adaptation is required. Created on Windows OS.
# Not guaranteed.

# Please contact for questions. This will be updated as more functionality is
# added.

# -----Import Required Libraries-----
import pyglet
from psychopy import core as pcore
from psychopy import monitors, visual, event

import numpy as np
import numbers
import math
import collections
import os

import tobii_research as tobii

# localization
import gettext

try:
    dir_path = os.path.dirname(os.path.realpath(__file__))
    locales_dir_path = os.path.join(dir_path, "locales")
    current_translation = gettext.translation("all_strings", localedir=locales_dir_path, languages=['hu'])
    current_translation.install()
    _ = current_translation.gettext
except:
    _ = gettext.gettext

# -----Class for working with Tobii Eyetrackers -----
class TobiiHelper:

    def __init__(self):

        self.eyetracker = None

        self.tbCoordinates = None

        self.virtual_trackbox_width = None

        self.virtual_trackbox_height = None

        self.calibration = None

        self.tracking = False

        self.win = None

        self.monitorName = None

        self.gazeData = None

        self.logging = True

        self.accuracyInPixel = 50

# ----- Functions for initialzing the eyetracker and class attributes -----

    # find and connect to a tobii eyetracker
    def setEyeTracker(self, serialString = None):

        # if serial number is not given as a string
        if serialString is not None and not isinstance(serialString, str):
            raise TypeError("Serial number must be formatted as a string.")

        # try to find all eyetrackers
        # Sometimes the eyetracker is not identified for the first time. Try more times.
        loopCount = 1
        allTrackers = tobii.find_all_eyetrackers()
        while not allTrackers and loopCount < 50:
            allTrackers = tobii.find_all_eyetrackers()
            pcore.wait(0.02)
            loopCount += 1

        # if there are no eyetrackers
        if len(allTrackers) < 1:
            raise RuntimeError("Cannot find any eyetrackers.")

        # if there is no serialString specified, use first found eyetracker
        if serialString is None:
            # use first found eyetracker
            eyetracker = allTrackers[0]
            if self.logging:
                print("Address: " + eyetracker.address)
                print("Model: " + eyetracker.model)
                print("Name: " + eyetracker.device_name)
                print("Serial number: " + eyetracker.serial_number)
            # create eyetracker object
            self.eyetracker = eyetracker
        # if serial number is given as a string
        else:
            # get information about available eyetrackers
            for eyetracker in allTrackers:
                if eyetracker.serial_number == serialString:
                    if self.logging:
                        print("Address: " + eyetracker.address)
                        print("Model: " + eyetracker.model)
                        # fine if name is empty
                        print("Name: " + eyetracker.device_name)
                        print("Serial number: " + eyetracker.serial_number)

                    # create eyetracker object
                    self.eyetracker = eyetracker

        # check to see that eyetracker is connected
        if self.eyetracker is None:
            raise RuntimeError("Eyetracker did not connect. Check serial number?")
        elif self.logging:
            print("Eyetracker connected successfully.")

        # get track box and active display area coordinates
        self.__getTrackerSpace()


    # function for getting trackbox (tb) and active display area (ada)coordinates, returns
    # coordintes in two separate dictionaries with values in mm
    def __getTrackerSpace(self):

        # check to see that eyetracker is connected
        if self.eyetracker is None:
            raise RuntimeError("There is no eyetracker.")

        # get track box information in mm, return only the 2d coordinates
        # of the cube side closest to the eyetracker
        trackBox = self.eyetracker.get_track_box()
        self.tbCoordinates = {}
        self.tbCoordinates['bottomLeft'] = trackBox.front_lower_left
        self.tbCoordinates['bottomRight'] = trackBox.front_lower_right
        self.tbCoordinates['topLeft'] = trackBox.front_upper_left
        self.tbCoordinates['topRight'] = trackBox.front_upper_right
        # calculate box height and width
        trackBoxHeight = abs(trackBox.front_lower_left[1] -
                             trackBox.front_upper_right[1])
        trackBoxWidth = abs(trackBox.front_lower_left[0] -
                            trackBox.front_lower_right[0])
        self.tbCoordinates['height'] = trackBoxHeight
        self.tbCoordinates['width'] = trackBoxWidth

        self.tbCoordinates['frontDistance'] = trackBox.front_lower_left[2]
        self.tbCoordinates['backDistance'] = trackBox.back_lower_left[2]


    # define and calibrate experimental monitor, set monitor dimensions
    def setMonitor(self, nameString = None, dimensions = None):

        # find all connected monitors
        allMonitors = monitors.getAllMonitors()
        if len(allMonitors) is 0:
            raise RuntimeError("Can't find any monitor.")

        # if no dimensions given
        if dimensions is None:
            # use current screen dimensions
            screen = pyglet.window.get_platform().get_default_display().get_default_screen()
            dimensions = (screen.width, screen.height)
            if self.logging:
                print ("Current screen size is: " + str(dimensions[0]) + "x" + str(dimensions[1]))
        # if dimension not given as tuple
        elif not isinstance(dimensions, tuple):
            raise TypeError("Dimensions must be given as tuple.")
        elif len(dimensions) is not 2:
            raise TypeError("Dimensions must be a pair of the screen height and width.")
        elif not isinstance(dimensions[0], numbers.Number) or not isinstance(dimensions[1], numbers.Number):
            raise TypeError("The given dimensions tupple should contain numbers.")
        elif dimensions[0] <= 0 or dimensions[1] <= 0:
            raise ValueError("Screen width and height must be positive values.")

        # if there is not monitor name defined, go to first default monitor
        if nameString is None:
            # create monitor calibration object
            self.monitorName = allMonitors[0]
            thisMon = monitors.Monitor(self.monitorName)
            if self.logging:
                print ("Current monitor name is: " + self.monitorName)
            # set monitor dimensions
            thisMon.setSizePix(dimensions)
            # save monitor
            thisMon.saveMon()  # save monitor calibration
            self.win = thisMon
        # if serial number is not given as a string
        elif not isinstance(nameString, str):
            raise TypeError("Monitor name must be formatted as a string.")
        # if serial number is given as a string
        else:
            # create monitor calibration object
            thisMon = monitors.Monitor(nameString)
            if self.logging:
                print ("Current monitor name is: " + nameString)
            self.monitorName = nameString
            # set monitor dimensions
            thisMon.setSizePix(dimensions)
            # save monitor
            thisMon.saveMon()  # save monitor calibration
            self.win = thisMon

    def getMonitorName(self):
        if self.monitorName is None:
            raise RuntimeError("No monitor was set.")
        return self.monitorName

    def getMonitorDimensions(self):
        if self.win is None:
            raise RuntimeError("No monitor was set.")
        return (self.win.getSizePix()[0], self.win.getSizePix()[1])

    def enableLogging(self):
        self.logging = True

    def disableLogging(self):
        self.logging = False

    def setAccuracy(self, accuracyInPixel):
        if not isinstance(accuracyInPixel, numbers.Number):
            raise TypeError("A number is expected to be passed as accuracyInPixel parameter.")

        if accuracyInPixel <= 0 or accuracyInPixel >= 1000:
            raise ValueError("Strange value for accuracy.")

        self.accuracyInPixel = accuracyInPixel

# ----- Functions for starting and stopping eyetracker data collection -----

    # function for broadcasting real time gaze data
    def __gazeDataCallback(self, gazeData):
        self.gazeData = gazeData


    # function for subscribing to real time gaze data from eyetracker
    def __startGazeData(self):

        # check to see if eyetracker is there
        if self.eyetracker is None:
            raise RuntimeError("There is no eyetracker.")

        # if it is, proceed
        if self.logging:
            print ("Subscribing to eyetracker.")
        self.eyetracker.subscribe_to(tobii.EYETRACKER_GAZE_DATA,
                                     self.__gazeDataCallback,
                                     as_dictionary = True)
        self.tracking = True


    # function for unsubscring from gaze data
    def __stopGazeData(self):

        # check to see if eyetracker is there
        if self.eyetracker is None:
            raise RuntimeError("There is no eyetracker.")
        # if it is, proceed
        if self.logging:
            print ("Unsubscribing from eyetracker")
        self.eyetracker.unsubscribe_from(tobii.EYETRACKER_GAZE_DATA,
                                         self.__gazeDataCallback)
        self.tracking = False

# ----- Functions for converting coordinates between different coordinate systems -----

    # function for converting normalized positions from trackbox coordinate system
    # to the virtual trackbox coordinates in pixels
    def __trackBox2VirtualTrackBox(self, xyCoor):

        # check argument values
        if not isinstance(xyCoor, tuple):
            raise TypeError("XY coordinates must be given as tuple.")
        elif len(xyCoor) is not 2:
            raise ValueError("Wrong number of coordinate dimensions.")
        elif not isinstance(xyCoor[0], numbers.Number) or not isinstance(xyCoor[1], numbers.Number):
            raise TypeError("The given coordinates should be numbers.")

        if self.virtual_trackbox_height is None or self.virtual_trackbox_width is None:
            raise RuntimeError("Virtual trackbox dimensions are not set.")

        # scale up the normalized coordinates to the virtual trackbox pixel coordinates
        resultXCoord = xyCoor[0] * self.virtual_trackbox_width
        resultYCoord = xyCoor[1] * self.virtual_trackbox_height

        # move the object to the psychopy origin
        centerShift = (self.virtual_trackbox_width / 2, self.virtual_trackbox_height / 2)
        resultXCoord -= centerShift[0]
        resultYCoord -= centerShift[1]

        # mirror coordinates
        resultXCoord *= -1
        resultYCoord *= -1

        return (resultXCoord, resultYCoord)


    # function for converting from tobiis ada coordinate system in normalized
    # coordinates where (0,0) is the upper left corner, to psychopy window
    # coordinates in pix, where (0,0) is at the center of psychopy window.
    def __ada2PsychoPix(self, xyCoor):

        if self.win is None:
            raise RuntimeError("No monitor was set.")

        # check argument values
        if not isinstance(xyCoor, tuple):
            raise TypeError("XY coordinates must be given as tuple.")
        elif len(xyCoor) is not 2:
            raise ValueError("Wrong number of coordinate dimensions.")
        elif not isinstance(xyCoor[0], numbers.Number) or not isinstance(xyCoor[1], numbers.Number):
            raise TypeError("XY coordinates must be given as number values.")
        elif xyCoor[0] > 1.0 or xyCoor[0] < 0.0 or xyCoor[1] > 1.0 or xyCoor[1] < 0.0:
            raise ValueError("The given coordinates should be in normalized form ([0.0,1.0]).")

        # convert to pixels and correct for psychopy window coordinates
        monHW = (self.win.getSizePix()[0],
                 self.win.getSizePix()[1])
        wShift, hShift = monHW[0] / 2 , monHW[1] / 2
        psychoPix = (int((xyCoor[0]* monHW[0]) - wShift),
                     int(((xyCoor[1] * monHW[1]) - hShift) * -1))
        # return coordinates in psychowin 'pix' units
        return psychoPix

# ----- Functions for collecting eye and gaze data -----

    # function for collecting gaze coordinates in tobiis ada coordinate
    # system. currently written to return the average (x, y) position of both
    # eyes, but can be easily rewritten to return data from one or both eyes
    def __getAvgGazePos(self):

        # check to see if the eyetracker is connected and turned on
        if self.eyetracker is None:
            raise RuntimeError("There is no eyetracker.")
        if self.tracking is False:
            raise RuntimeError("The eyetracker is not turned on.")
        if self.gazeData is None:
            raise RuntimeError("No recorded gaze data was found.")

        # access gaze data dictionary to get gaze position tuples
        leftGazeXYZ = self.gazeData['left_gaze_point_on_display_area']
        rightGazeXYZ = self.gazeData['right_gaze_point_on_display_area']
        # get 2D gaze positions for left and right eye
        xs = (leftGazeXYZ[0], rightGazeXYZ[0])
        ys = (leftGazeXYZ[1], rightGazeXYZ[1])

        # if all of the axes have data from at least one eye
        if all([math.isnan(x) for x in xs]) or all([math.isnan(y) for y in ys]):
            # take x and y averages
            avgGazePos = (math.nan, math.nan)
        else:
            # or if no data, hide points by showing off screen
            avgGazePos = (np.nanmean(xs), np.nanmean(ys))
        return avgGazePos


    # function for finding the avg 3d position of subject's eyes, so that they
    # can be drawn in the virtual track box before calibration. The x and y
    # coordinates are returned in the virtual trackbox coordinates system in pixels.
    def __virtualTrackboxEyePos(self):

        # check to see if the eyetracker is connected and turned on
        if self.eyetracker is None:
            raise RuntimeError("There is no eyetracker.")
        if self.tracking is False:
            raise RuntimeError("The eyetracker is not turned on.")
        if self.gazeData is None:
            raise RuntimeError("No recorded gaze data was found.")

        # access gaze data dictionary to get eye position tuples,
        # in trackbox coordinate system
        lelfTbXYZ = self.gazeData['left_gaze_origin_in_trackbox_coordinate_system']
        rightTbXYZ = self.gazeData['right_gaze_origin_in_trackbox_coordinate_system']

        # left eye validity
        leftVal = self.gazeData['left_gaze_origin_validity']
        # right eye validity
        rightVal = self.gazeData['right_gaze_origin_validity']

        # if left eye is found by the eyetracker
        if leftVal:
            # update the left eye positions if the values are reasonable
            # scale left eye position so that it fits in track box
            leftTbPos = self.__trackBox2VirtualTrackBox((lelfTbXYZ[0], lelfTbXYZ[1]))
        else:
            # hide by drawing in the corner
            leftTbPos = (math.nan, math.nan)

        # if right eye is found by the eyetracker
        if rightVal:
            # update the right eye positions if the values are reasonable
            # scale right eye position so that it fits in track box
            rightTbPos = self.__trackBox2VirtualTrackBox((rightTbXYZ[0], rightTbXYZ[1]))
        else:
            # hide by drawing in the corner
            rightTbPos = (math.nan, math.nan)
        # return values for positio in track box
        return leftTbPos, rightTbPos


    # x, y, and z dimensions are given in mm from the tracker origin, gives the
    # average 3d position of both eyes, but can be easily rewritten to yield
    # the position of each eye separately
    def __getAvgEyePos(self):

        # check to see if the eyetracker is connected and turned on
        if self.eyetracker is None:
            raise RuntimeError("There is no eyetracker.")
        if self.tracking is False:
            raise RuntimeError("The eyetracker is not turned on.")
        if self.gazeData is None:
            raise RuntimeError("No recorded gaze data was found.")

        # access gaze data dictionary to get eye position tuples, given in
        # mm in from eyetracker origin
        leftOriginXYZ = self.gazeData['left_gaze_origin_in_user_coordinate_system']
        rightOriginXYZ = self.gazeData['right_gaze_origin_in_user_coordinate_system']

        # create arrays with positions of both eyes on x, y, and z axes
        xs = (leftOriginXYZ[0],rightOriginXYZ[0])
        ys = (leftOriginXYZ[1],rightOriginXYZ[1])
        zs = (leftOriginXYZ[2],rightOriginXYZ[2])

        # if all of the axes have data from at least one eye
        if not all([math.isnan(x) for x in xs]) and not all([math.isnan(y) for y in ys]) and not all([math.isnan(z) for z in zs]):
            # update the distance if the values are reasonable
            avgEyePos = (np.nanmean(xs), np.nanmean(ys), np.nanmean(zs))
        else:
            # otherwise set to zero
            avgEyePos = (0, 0, 0)
        # return average eye position in mm
        return avgEyePos


    # get average distance of the eyes from the tracker's plane, given in mm
    def __getAvgEyeDist(self):

        # check to see if the eyetracker is connected and turned on
        if self.eyetracker is None:
            raise RuntimeError("There is no eyetracker.")
        if self.tracking is False:
            raise RuntimeError("The eyetracker is not turned on.")
        if self.gazeData is None:
            raise RuntimeError("No recorded gaze data was found.")

        return self.__getAvgEyePos()[2]


# ----- Internal functions for running calibration -----

    # a rutine to workaround issues with clearing the screen using window.flip()
    def __clearScreen(self, window):
        # draw a dummy rectangle on the screen, otherwise window background will change
        dummyRect = visual.Rect(window,
                          fillColor = [1.0, 1.0, 1.0],
                          lineColor = [1.0, 1.0, 1.0],
                          pos = (0.99, 0.99),
                          units = 'norm',
                          width = 0.01,
                          height = 0.01)
        dummyRect.draw()
        window.flip()

    # calculate mean of a point list, handle x and y coordinates separately
    def __calcMeanOfPointList(self, pointList):
        # we need a non empty list
        if not isinstance(pointList, list):
            raise TypeError("pointList is expected to be a list.")
        if len(pointList) == 0:
            raise ValueError("Can not calculate avarage of an empty list.")

        sumX = 0.0
        sumY = 0.0
        for i in range(len(pointList)):

            if not isinstance(pointList[i], tuple):
                raise ValueError("pointList needs to contain points as two length tuple.")
            if len(pointList[i]) != 2:
                raise ValueError("pointList needs to contain points as two length tuple.")
            if not isinstance(pointList[i][0], numbers.Number) or not isinstance(pointList[i][1], numbers.Number):
                raise ValueError("pointList contains non number items.")

            sumX += pointList[i][0]
            sumY += pointList[i][1]

        return (sumX / len(pointList), sumY / len(pointList))

    # smoothing routine, aggregate the measured data and return with the avarage value
    def __smoothing(self, currentObject, objectList, invalidObject, smoothFunction):
        if not isinstance(objectList, list):
            raise TypeError("objectList is expected to be a list.")
        maxLength = 6

        # we remove one item, when one invalid item was passed as a parameter
        # if there are enough invalid items passed to this function the list
        # will be empty which indicated that we have no valid data
        if currentObject == invalidObject:
            if len(objectList) > 0:
                objectList.pop(0)
        else: # push valid data into the aggregator list
            objectList.append(currentObject)

        if len(objectList) == 0: # no valid data
            result = invalidObject
        else:
            result = smoothFunction(objectList) # use the specifid function to calculate the smoothed value

        # remove previous position values if the maximum limit is reached
        if len(objectList) == maxLength:
            objectList.pop(0)

        return result

    # Function for drawing a slider showing the eye distance from the eye tracker.
    # The slider is drawn on the right side of the virtual track box.
    def __drawDistanceSlider(self, drawingWin, eyeDist):

        if not isinstance(drawingWin, visual.Window):
            raise TypeError("drawingWin should be a valid visual.Window object.")

        if not isinstance(eyeDist, numbers.Number):
            raise TypeError("eyeDist should be a valid number value.")

        if self.tbCoordinates is None:
            raise RuntimeError("Missing trackbox coordinates!")

        if self.virtual_trackbox_width is None or self.virtual_trackbox_height is None:
            raise RuntimeError("Virtual trackbox's dimensions are not inited!")

        # draw the slider to the right side of the trackbox, having a small padding between the two
        sliderDrawingPos = (self.virtual_trackbox_width / 2 + 50, 0.0)

        # let the slider have the same size as the virtual trackbox
        sliderHeight = self.virtual_trackbox_height

        # split the slider into 8 pieces
        drawingUnit = sliderHeight / 8

        sliderWidth = 10

        # red range on the top of the slider (eye is too new)
        invalidTop = visual.Rect(drawingWin,
                                  fillColor = [1.0, -1.0, -1.0],
                                  lineColor = [0.0, 0.0, 0.0],
                                  pos = (sliderDrawingPos[0], sliderDrawingPos[1] + (3.5 * drawingUnit)),
                                  units = 'pix',
                                  lineWidth = 0.1,
                                  width = sliderWidth,
                                  height = drawingUnit)

        # yellow range on the top of the slider (eye is near to the front of the trackbox)
        mediumTop = visual.Rect(drawingWin,
                                  fillColor = [1.0, 1.0, 0.0],
                                  lineColor = [0.0, 0.0, 0.0],
                                  pos = (sliderDrawingPos[0], sliderDrawingPos[1] + (2.5 * drawingUnit)),
                                  units = 'pix',
                                  lineWidth = 0.1,
                                  width = sliderWidth,
                                  height = drawingUnit)

        # valid distance range
        validRegion = visual.Rect(drawingWin,
                                  fillColor = [-1.0, 1.0, -1.0],
                                  lineColor = [0.0, 0.0, 0.0],
                                  pos = (sliderDrawingPos[0], sliderDrawingPos[1]),
                                  units = 'pix',
                                  lineWidth = 0.1,
                                  width = sliderWidth,
                                  height = drawingUnit * 4)

        # yellow range on the bottom of the slider (eye is near to the back of the trackbox)
        mediumBottom = visual.Rect(drawingWin,
                                  fillColor = [1.0, 1.0, 0.0],
                                  lineColor = [0.0, 0.0, 0.0],
                                  pos = (sliderDrawingPos[0], sliderDrawingPos[1] - (2.5 * drawingUnit)),
                                  units = 'pix',
                                  lineWidth = 0.1,
                                  width = sliderWidth,
                                  height = drawingUnit)

        # red range on the bottom of the slider (eye is too far)
        invalidBottom = visual.Rect(drawingWin,
                                  fillColor = [1.0, -1.0, -1.0],
                                  lineColor = [0.0, 0.0, 0.0],
                                  pos = (sliderDrawingPos[0], sliderDrawingPos[1] - (3.5 * drawingUnit)),
                                  units = 'pix',
                                  lineWidth = 0.1,
                                  width = sliderWidth,
                                  height = drawingUnit)


        # eye relative to the front
        relativeEyeDist = eyeDist - self.tbCoordinates.get("frontDistance")
        # use the allowed range of distances
        validDistanceRange = self.tbCoordinates.get("backDistance") - self.tbCoordinates.get("frontDistance")
        # calculate the position of the marker based on the eye distance
        markerPos = ((relativeEyeDist / validDistanceRange) * (drawingUnit * 6)) - ((drawingUnit * 6) / 2)
        markerPos *= -1

        # do not allow to move the marker out of the slider
        if markerPos > (sliderHeight / 2):
            markerPos = sliderHeight / 2
        elif markerPos < -(sliderHeight / 2):
            markerPos = -(sliderHeight / 2)

        # marker indicating the current eye distance
        sliderMarker = visual.Polygon(drawingWin,
                                  fillColor = [-0.8, -0.8, -0.8],
                                  lineColor = [0.0, 0.0, 0.0],
                                  pos = (sliderDrawingPos[0] + sliderWidth, markerPos),
                                  units = 'pix',
                                  lineWidth = 0.1,
                                  radius = sliderWidth,
                                  ori = 270.0)

        invalidTop.draw()
        mediumTop.draw()
        validRegion.draw()
        mediumBottom.draw()
        invalidBottom.draw()
        sliderMarker.draw()


    # function for drawing representation of the eyes in virtual trackbox
    def __drawEyePositions(self, psychoWin):

        # check that psychopy window exists
        if not isinstance(psychoWin, visual.Window):
            raise TypeError("psychoWin should be a valid visual.Window object.")

        if self.tbCoordinates is None:
            raise RuntimeError("Missing trackbox coordinates! Try running setEyeTracker().")

        # stimuli for holding text
        calibMessage = visual.TextStim(psychoWin,
                                       color = [1.0, 1.0, 1.0],  # text
                                       units = 'norm',
                                       height = 0.08,
                                       pos = (0.0, 0.1))

        # subject instruction for track box
        calibMessage.text = _("Please position yourself so that the\n" \
                              "eye-tracker can locate your eyes." \
                              "\n\nPress 'c' to continue.")
        calibMessage.draw()
        psychoWin.flip()

        # turn keyboard reporting on and get subject response
        event.waitKeys(maxWait = 10, keyList = ['c'])  # proceed with calibration
        self.__clearScreen(psychoWin)   # clear previous text

        # Set default colors
        correctColor = [-1.0, 1.0, -1.0]
        mediumColor = [1.0, 1.0, 0.0]
        wrongColor = [1.0, -1.0, -1.0]

        # calculate the virtual track box sizes
        screen_width = psychoWin.size[0]
        screen_height = psychoWin.size[1]

        trackbox_width = self.tbCoordinates.get("width")
        trackbox_height = self.tbCoordinates.get("height")

        # which dimension is bigger relative to the screen size
        if screen_width / trackbox_width >= screen_height / trackbox_height:
            # make the virtual track box take the 8/3 of the screen
            self.virtual_trackbox_width = screen_width / 8 * 3
            # the width/height ration of the virtual trackbox should be the same what the physical track box has
            self.virtual_trackbox_height = self.virtual_trackbox_width * trackbox_height / trackbox_width
        else:
            self.virtual_trackbox_height = screen_height / 8 * 3
            self.virtual_trackbox_width = self.virtual_trackbox_height * trackbox_width / trackbox_height

        # rectangle for viewing eyes
        eyeArea = visual.Rect(psychoWin,
                              fillColor = [0.0, 0.0, 0.0],
                              lineColor = [0.0, 0.0, 0.0],
                              pos = [0.0, 0.0],
                              units = 'pix',
                              lineWidth = 3,
                              width = self.virtual_trackbox_width,
                              height = self.virtual_trackbox_height)

        # Make stimuli for the left and right eye
        leftStim = visual.Circle(psychoWin,
                                 fillColor = eyeArea.fillColor,
                                 units = 'pix',
                                 radius = 30)
        rightStim = visual.Circle(psychoWin,
                                  fillColor = eyeArea.fillColor,
                                  units = 'pix',
                                  radius = 30)
        # Make a dummy message
        findmsg = visual.TextStim(psychoWin,
                                  text = " ",
                                  color = [1.0, 1.0, 1.0],
                                  units = 'norm',
                                  pos = [0.0, -((self.virtual_trackbox_height / screen_height) + 0.10)],
                                  height = 0.07)

        eyeDistances = []
        leftPositions = []
        rightPositions = []

        event.clearEvents(eventType='keyboard')

        # while tracking
        while True:
            # find and update eye positions
            leftEyePos, rightEyePos = self.__virtualTrackboxEyePos()
            eyeDist = self.__getAvgEyeDist()

            eyeDist = self.__smoothing(eyeDist, eyeDistances, 0.0, lambda list : sum(list) / len(list))

            leftStim.pos = self.__smoothing(leftEyePos, leftPositions, (math.nan, math.nan), self.__calcMeanOfPointList)

            rightStim.pos = self.__smoothing(rightEyePos, rightPositions, (math.nan, math.nan), self.__calcMeanOfPointList)

            frontDistance = self.tbCoordinates.get('frontDistance')
            backDistance = self.tbCoordinates.get('backDistance')

            medium_left = False
            medium_right = False
            wrong_left = False
            wrong_right = False

            # change color depending on distance
            if eyeDist <= frontDistance or eyeDist >= backDistance:
                wrong_left = True
                wrong_right = True
            elif eyeDist <= frontDistance + 50 or eyeDist >= backDistance - 50:
                medium_left = True
                medium_right = True

            # change color depending on horizontal position
            if leftStim.pos[0] >= (self.virtual_trackbox_width / 2) or \
               leftStim.pos[0] <= -(self.virtual_trackbox_width / 2):
                wrong_left = True
            elif leftStim.pos[0] >= (self.virtual_trackbox_width / 2) - (self.virtual_trackbox_width / 5) or \
                 leftStim.pos[0] <= -(self.virtual_trackbox_width / 2) + (self.virtual_trackbox_width / 5):
                medium_left = True

            if rightStim.pos[0] >= (self.virtual_trackbox_width / 2) or \
               rightStim.pos[0] <= -(self.virtual_trackbox_width / 2):
                wrong_right = True
            elif rightStim.pos[0] >= (self.virtual_trackbox_width / 2) - (self.virtual_trackbox_width / 5) or \
                 rightStim.pos[0] <= -(self.virtual_trackbox_width / 2) + (self.virtual_trackbox_width / 5):
                medium_right = True

            # change color depending on vertical position
            if leftStim.pos[1] >= (self.virtual_trackbox_height / 2) or \
               leftStim.pos[1] <= -(self.virtual_trackbox_height / 2):
                wrong_left = True
            elif leftStim.pos[1] >= (self.virtual_trackbox_height / 2) - (self.virtual_trackbox_height / 5) or \
                 leftStim.pos[1] <= -(self.virtual_trackbox_height / 2) + (self.virtual_trackbox_height / 5):
                medium_left = True

            if rightStim.pos[1] >= (self.virtual_trackbox_height / 2) or \
               rightStim.pos[1] <= -(self.virtual_trackbox_height / 2):
                wrong_right = True
            elif rightStim.pos[1] >= (self.virtual_trackbox_height / 2) - (self.virtual_trackbox_height / 5) or \
                 rightStim.pos[1] <= -(self.virtual_trackbox_height / 2) + (self.virtual_trackbox_height / 5):
                medium_right = True

            if wrong_left:
                leftStim.fillColor, leftStim.lineColor = wrongColor, wrongColor
            elif medium_left:
                leftStim.fillColor, leftStim.lineColor = mediumColor, mediumColor
            else:
                leftStim.fillColor, leftStim.lineColor = correctColor, correctColor

            if wrong_right:
                rightStim.fillColor, rightStim.lineColor = wrongColor, wrongColor
            elif medium_right:
                rightStim.fillColor, rightStim.lineColor = mediumColor, mediumColor
            else:
                rightStim.fillColor, rightStim.lineColor = correctColor, correctColor

            # give distance feedback
            findmsg.text = _("Press 'c' to calibrate or 'q' to abort.")

            # update stimuli in window
            eyeArea.draw()

            if not math.isnan(leftStim.pos[0]):
                leftStim.draw()

            if not math.isnan(rightStim.pos[0]):
                rightStim.draw()

            findmsg.draw()
            self.__drawDistanceSlider(psychoWin, eyeDist)
            psychoWin.flip()

            # depending on response, either abort script or continue to calibration
            if event.getKeys(keyList=['q']):
                self.__stopGazeData()
                psychoWin.close()
                pcore.quit()
            elif event.getKeys(keyList=['c']):
                if self.logging:
                    print("Proceeding to calibration.")
                self.__stopGazeData()
                self.__clearScreen(psychoWin)
                return

            # clear events not accessed this iteration
            event.clearEvents(eventType='keyboard')

    def __drawValidationScreen(self, pointDict, valWin):

        # check the values of the point dictionary
        if not isinstance(pointDict, dict):
            raise TypeError("pointDict must be a dictionary with number " +\
                            "keys and coordinate values.")
        if not isinstance(valWin, visual.Window):
            raise TypeError("valWin should be a valid visual.Window object.")

        # get points from dictionary
        curPoints = pointDict.values()

        # convert points from normalized ada units to psychopy pix
        pointPositions = [self.__ada2PsychoPix(x) for x in curPoints]

        # stimuli for showing point of gaze
        gazeStim = visual.Circle(valWin,
                                 radius = self.accuracyInPixel,
                                 lineColor = [1.0, 0.95, 0.0],  # yellow circle
                                 fillColor = [1.0, 1.0, 0.55],  # light interior
                                 lineWidth = 40,
                                 units = 'pix')
        # Make a dummy message
        valMsg = visual.TextStim(valWin,
                                 text = _("Wait for the experimenter."),
                                 color = [1.0, 1.0, 1.0],
                                 units = 'norm',
                                 pos = [0.0, -0.5],
                                 height = 0.07)
        # Stimuli for all validation points
        valPoints = visual.Circle(valWin,
                                  units = 'pix',
                                  radius = 15,
                                  lineColor = [1.0, -1.0, -1.0],  # red
                                  fillColor = [1.0, -1.0, -1.0])  # red

        # create array for smoothing gaze position
        gazePositions = []

        # while tracking
        while True:

            avgGazePos = self.__getAvgGazePos()

            curPos = self.__smoothing(avgGazePos, gazePositions, (math.nan, math.nan), self.__calcMeanOfPointList)

            # update stimuli in window and draw if we have a valid pos
            if not math.isnan(curPos[0]) and curPos[0] <= 1.0 and curPos[0] >= 0.0 and \
               not math.isnan(curPos[1]) and curPos[1] <= 1.0 and curPos[1] >= 0.0:
                gazeStim.pos = self.__ada2PsychoPix(tuple(curPos))
                gazeStim.draw()

            # points
            for point in pointPositions:
                valPoints.pos = point
                valPoints.draw()

            # text
            valMsg.draw()
            valWin.flip()

            # depending on response, either abort script or continue to calibration
            if event.getKeys(keyList=['q']):
                self.__stopGazeData()
                pcore.quit()
            elif event.getKeys(keyList=['c']):
                if self.logging:
                    print ("Exiting calibration validation.")
                self.__stopGazeData()
                return

            # clear events not accessed this iteration
            event.clearEvents(eventType='keyboard')


    # function for getting the average left and right gaze position coordinates
    # for each calibration point in psychopy pix units
    def __calculateCalibration(self, calibResult):

        # check the values of the point dictionary
        if not isinstance(calibResult, tobii.CalibrationResult):
            raise TypeError("Argument should be a valid tobii_research.CalibResult object")

        #create an empty list to hold values
        calibDrawCoor = []

        # iterate through calibration points
        startindex = 0
        if len(calibResult.calibration_points) > 0 and \
            calibResult.calibration_points[0].position_on_display_area == (0.0, 0.0): # Tobii SDK adds an extra calib point
            startindex = 1
        for i in range(startindex, len(calibResult.calibration_points)):
            # current point
            curPoint = calibResult.calibration_points[i]
            pointPosition = curPoint.position_on_display_area  # point position
            pointSamples = curPoint.calibration_samples  # samples at point
            # empty arrays for holding left and right eye gaze coordinates
            leftOutput = np.zeros((len(pointSamples), 2))
            rightOutput = np.zeros((len(pointSamples), 2))

            # find left and right gaze coordinates for all samples in point
            for j in range(len(pointSamples)):
                curSample = pointSamples[j]
                leftEye = curSample.left_eye
                rightEye = curSample.right_eye
                leftOutput[j] = leftEye.position_on_display_area
                rightOutput[j] = rightEye.position_on_display_area

            # get average x and y coordinates using all samples in point
            leftXY = tuple(np.mean(leftOutput, axis = 0))
            rightXY = tuple(np.mean(rightOutput, axis = 0))
            point = tuple((pointPosition[0], pointPosition[1]))
            # put current calibration point coordinates , l and r eye coordinates
            # into list, and convert to psychopy window coordinates in pix
            newList = [self.__ada2PsychoPix(point), self.__ada2PsychoPix(leftXY),
                       self.__ada2PsychoPix(rightXY), pointPosition]
            calibDrawCoor.insert(i, newList)

        # return as list
        return calibDrawCoor


    # function for drawing the results of the calibration
    def __drawCalibrationResults(self, calibResult, calibWin, curDict):

        # check argument values
        if self.calibration is None:
            raise RuntimeError("No calibration object exists.")
        # check values of calibration result
        if not isinstance(calibResult, tobii.CalibrationResult):
            raise TypeError("calibResult should be a valid tobii_research.CalibrationResult object.")
        if not isinstance(calibWin, visual.Window):
            raise TypeError("calibWin should be a visual.Window object.")
        # check the values of the point dictionary
        if not isinstance(curDict, dict):
            raise TypeError("curDict must be a dictionary with number \n" +\
                            "keys and coordinate values.")
        if len(calibResult.calibration_points) > 0 and\
            calibResult.calibration_points[0].position_on_display_area == (0.0, 0.0): # Tobii SDK adds an extra calib point
            if len(curDict) != len(calibResult.calibration_points) - 1:
                raise ValueError("Data inconsistency: calibResult and curDict have different amount of items")
        else:
            if len(curDict) != len(calibResult.calibration_points):
                raise ValueError("Data inconsistency: calibResult and curDict have different amount of items")

        # get gaze position results
        points2Draw = self.__calculateCalibration(calibResult)

        # create stimuli objects for drawing
        # outlined empty circle object for showing calibration point
        calibPoint = visual.Circle(calibWin,
                                   radius = self.accuracyInPixel,
                                   lineColor = [1.0, 1.0, 1.0],  # white
                                   lineWidth = 10,
                                   fillColor = calibWin.color,
                                   units = 'pix',
                                   pos = (0.0, 0.0))
        # line object for showing right eye gaze position during calibration
        rightEyeLine = visual.Line(calibWin,
                                   units ='pix',
                                   lineColor ='red',
                                   lineWidth = 20,
                                   start = (0.0, 0.0),
                                   end = (0.0, 0.0))
        # line object for showing left eye gaze position during calibration
        leftEyeLine = visual.Line(calibWin,
                                  units ='pix',
                                  lineColor ='yellow',
                                  lineWidth = 20,
                                  start = (0.0, 0.0),
                                  end = (0.0, 0.0))
        # number for identifying point in dictionary
        pointText = visual.TextStim(calibWin,
                                    text = " ",
                                    color = [1.0, 1.0, 1.0],
                                    units = 'pix',
                                    pos = [0.0, 0.0],
                                    height = 60)
        # Make a dummy message
        checkMsg = visual.TextStim(calibWin,
                                   text = _("Wait for the experimenter. \nUse number keys to select points for recalibration."),
                                   color = [1.0, 1.0, 1.0],
                                   units = 'norm',
                                   pos = [0.0, -0.5],
                                   height = 0.07)

        # make empty dictionary for holding points to be recalibrated
        holdRedoDict = []
        holdColorPoints = []

        # clear events not accessed this iteration
        event.clearEvents(eventType='keyboard')

        # draw and update screen
        while True:

            # iterate through calibration points and draw
            for i in range(len(points2Draw)):
                # update point and calibraiton results for both eyes
                point = points2Draw[i]
                pointPos = point[3]
                pointKey = 0

                # update text
                pointFound = False
                for key, point in curDict.items():
                    if point == pointPos:
                        pointText.text = key
                        pointKey = key
                        pointFound = True

                if not pointFound:
                    raise ValueError("Data inconsistency: calibResult and curDict contains different items.")

                # if current point is selected for recalibrate, make it noticeable
                if int(pointKey) in holdColorPoints:
                    calibPoint.lineColor = [-1.0, 1.0, -1.0]  # green circle
                else:
                    calibPoint.lineColor = [1.0, 1.0, 1.0]  # no visible change

                # update point and calibraiton results for both eyes
                point = points2Draw[i]
                startCoor, leftCoor, rightCoor = point[0], point[1], point[2]
                # update positions and draw  on window
                calibPoint.pos = startCoor  # calibration point
                leftEyeLine.start = startCoor  # left eye
                leftEyeLine.end = leftCoor
                rightEyeLine.start = startCoor  # right eye
                rightEyeLine.end = rightCoor
                pointText.pos = startCoor  # point text

                # update stimuli in window
                calibPoint.draw()  # has to come first or else will cover other
                # stim
                pointText.draw()
                leftEyeLine.draw()
                rightEyeLine.draw()

            checkMsg.draw()

            # show points and lines on window
            calibWin.flip()

            # add the label of calib points to the accepted key list
            keyList = ['c', 'q']
            for key in curDict.keys():
                keyList.append(key)

            pressedKeys = event.getKeys(keyList)

            # depending on response, either...
            # abort script
            for key in pressedKeys:
                if key in ['q']:
                    calibWin.close()
                    self.calibration.leave_calibration_mode()
                    pcore.quit()

                # else if recalibration point is requested
                elif key in curDict.keys():
                    # iterate through each of these presses
                    for entry in curDict.items():
                        # if the key press is the same as the current dictionary key
                        if entry[0] == key:
                            if entry in holdRedoDict:  # user changed his / her mind
                                holdRedoDict.remove(entry)
                                holdColorPoints.remove(int(key))
                            else:
                                # append that dictionary entry into a holding dictionary
                                holdRedoDict.append(entry)
                                # append integer version to a holding list
                                holdColorPoints.append(int(key))

                # continue with calibration procedure
                elif key in ['c']:
                    if self.logging:
                        print ("Finished checking. Resuming calibration.")
                    checkMsg.pos = (0.0, 0.0)
                    checkMsg.text = _("Finished checking. Resuming calibration.")
                    checkMsg.draw()
                    calibWin.flip()

                    # return dictionary of points to be recalibration
                    redoDict = collections.OrderedDict([])  # empty dictionary for holding unique values
                    # dont put repeats in resulting dictionary
                    tempDict = collections.OrderedDict(holdRedoDict)
                    for keys in tempDict.keys():
                        if keys not in redoDict.keys():
                            redoDict[keys] = tempDict.get(keys)

                    # return dictionary
                    return redoDict

            # clear events not accessed this iteration
            event.clearEvents(eventType='keyboard')


    # function for drawing calibration points, collecting and applying
    # calibration data
    def __getCalibrationData(self, calibWin, pointList):

        # check argument values
        if self.calibration is None:
            raise RuntimeError("No calibration object exists")
        # check value of calibration window
        if not isinstance(calibWin, visual.Window):
            raise TypeError("calibWin should be a visual.Window object.")
        # check the values of the point dictionary
        if not isinstance(pointList, list):
            raise TypeError("pointList must be a list of coordinate tuples.")

        # defaults
        pointSmallRadius = 5.0  # point radius
        pointLargeRadius = pointSmallRadius * 10.0
        moveFrames = 50 # number of frames to draw between points
        # starter point for animation
        if len(pointList) > 0 and pointList[0] != (0.9, 0.9):
            startPoint = (0.9, 0.9)
        else:
            startPoint = (0.1, 0.1)

        # calibraiton point visual object
        calibPoint = visual.Circle(calibWin,
                                   radius = pointLargeRadius,
                                   lineColor = [1.0, -1.0, -1.0],  # red
                                   fillColor = [1.0, -1.0, -1.0],
                                   units = 'pix')

        # draw animation for each point
        # converting psychopy window coordinate units from normal to px
        for i in range(len(pointList)):

            # if first point draw starting point
            if i == 0:
                firstPoint = [startPoint[0], startPoint[1]]
                secondPoint = [pointList[i][0], pointList[i][1]]
            else:
                firstPoint = [pointList[i - 1][0], pointList[i - 1][1]]
                secondPoint = [pointList[i][0], pointList[i][1]]

            # draw and move dot
            # step size for dot movement is new - old divided by frames
            pointStep = [(secondPoint[0] - firstPoint[0]) / moveFrames,
                         (secondPoint[1] - firstPoint[1]) / moveFrames]

            # Move the point in position (smooth pursuit)
            for frame in range(moveFrames):
                firstPoint[0] += pointStep[0]
                firstPoint[1] += pointStep[1]
                # draw & flip
                calibPoint.pos = self.__ada2PsychoPix(tuple(firstPoint))
                calibPoint.draw()
                calibWin.flip()
            # wait to let eyes settle
            pcore.wait(0.5)

            # allow the eye to focus before beginning calibration
            # point size change step
            radiusStep = ((pointLargeRadius - pointSmallRadius) / moveFrames)

            # Shrink the outer point (gaze fixation) to encourage focusing
            for frame in range(moveFrames):
                pointLargeRadius -= radiusStep
                calibPoint.radius = pointLargeRadius
                calibPoint.draw()
                calibWin.flip()
            # first wait to let the eyes settle
            pcore.wait(0.5)

            # conduct calibration of point
            if self.logging:
                print ("Collecting data at {0}." .format(i + 1))
            collecting_status = None
            while collecting_status != tobii.CALIBRATION_STATUS_SUCCESS:
                collecting_status = self.calibration.collect_data(pointList[i][0], pointList[i][1])

            # feedback from calibration
            if self.logging:
                print ("{0} for data at point {1}."
                       .format(collecting_status, i + 1))
            pcore.wait(0.3)  # wait before continuing

            # Return point to original size
            for frame in range(moveFrames):
                pointLargeRadius += radiusStep
                calibPoint.radius = pointLargeRadius
                calibPoint.draw()
                calibWin.flip()
            # let the eyes settle and move to the next point
            pcore.wait(0.2)

            # check to quit
            # depending on response, either abort script or continue to calibration
            if event.getKeys(keyList=['q']):
                calibWin.close()
                self.calibration.leave_calibration_mode()
                pcore.quit()

            # clear events not accessed this iteration
            event.clearEvents(eventType='keyboard')

        # clear screen
        self.__clearScreen(calibWin)
        # print feedback
        if self.logging:
            print ("Computing and applying calibration.")
        # compute and apply calibration to get calibration result object
        calibResult = self.calibration.compute_and_apply()
        # return calibration result
        return calibResult


    def __drawCalibrationScreen(self, calibDict, calibWin):

        # check the values of the point dictionary
        if not isinstance(calibDict, dict):
            raise TypeError("calibDict must be a dictionary with number " +\
                            "keys and coordinate values.")
        if not isinstance(calibWin, visual.Window):
            raise TypeError("calibWin should be a valid visual.Window object.")
        # check to see that eyetracker is connected
        if self.eyetracker is None:
            raise RuntimeError("There is no eyetracker object. \n" +\
                               "Try running setEyeTracker().")

        # stimuli for holding text
        calibMessage = visual.TextStim(calibWin,
                                       color = [1.0, 1.0, 1.0],  # text
                                       units = 'norm',
                                       height = 0.08,
                                       pos = (0.0, 0.1))

        # initialize calibration
        self.calibration = tobii.ScreenBasedCalibration(self.eyetracker)  # calib object
        # enter calibration mode
        self.calibration.enter_calibration_mode()
        # subject instructions
        calibMessage.text = _("Please focus your eyes on the red dot " \
                              "and follow it with your eyes as closely as " \
                              "possible.\n\nPress 'c' to continue.")
        calibMessage.draw()
        calibWin.flip()

        # turn keyboard reporting on and get subject response
        event.waitKeys(maxWait = 10, keyList = ['c'])  # proceed with calibration
        self.__clearScreen(calibWin)
        pcore.wait(3)

        # create dictionary for holding points to be recalibrated
        redoCalDict = calibDict

        # loop through calibration process until calibration is complete
        while True:

            # create point order form randomized dictionary values
            pointOrder = list(redoCalDict.values())
            # perform calibration
            calibResult = self.__getCalibrationData(calibWin, pointOrder)

            # Check status of calibration result
            # if calibration was successful, check calibration results
            if calibResult.status == tobii.CALIBRATION_STATUS_SUCCESS:
                # give feedback
                calibMessage.text = _("Applying calibration...")
                calibMessage.draw()
                calibWin.flip()
                pcore.wait(2)
                # moving on to accuracy plot
                calibMessage.text = _("Calculating calibration accuracy...")
                calibMessage.draw()
                calibWin.flip()
                pcore.wait(2)

                # check calibration for poorly calibrated points
                redoCalDict = self.__drawCalibrationResults(calibResult,
                                                          calibWin,
                                                          calibDict)

            else:  # if calibration was not successful, leave and abort
                calibMessage.text = _("Calibration was not successful.\n\n" \
                                      "Closing the calibration window.")
                calibMessage.draw()
                calibWin.flip()
                pcore.wait(3)
                calibWin.close()
                self.calibration.leave_calibration_mode()
                return

            # Redo calibration for specific points if necessary
            if not redoCalDict:  # if no points to redo
            # finish calibration
                if self.logging:
                    print ("Calibration successful. Moving on to validation mode.")
                calibMessage.text = _("Calibration was successful.\n\n" \
                                      "Moving on to validation.")
                calibMessage.draw()
                calibWin.flip()
                pcore.wait(3)
                self.calibration.leave_calibration_mode()
                # break loop to proceed with validation
                break

            else:  # if any points to redo
                # convert list to string for feedback
                printString = " ".join(str(x) for x in redoCalDict.keys())
                # feedback
                if self.logging:
                    print ("Still need to calibrate the following points: %s"
                            % printString)
                calibMessage.text = _("Calibration is almost complete.\n\n" \
                                      "Prepare to recalibrate a few points.")
                calibMessage.draw()
                calibWin.flip()
                pcore.wait(3)
                self.__clearScreen(calibWin)
                pcore.wait(3)

                # iterate through list of redo points and remove data from calibration
                for newPoint in redoCalDict.values():
                    if self.logging:
                        print (newPoint)
                    self.calibration.discard_data(newPoint[0], newPoint[1])

        # Validate calibration
        self.__clearScreen(calibWin)
        pcore.wait(3)

# ----- Public calibration rutines -----

    # function for running simple gui to visualize subject eye position. Make
    # sure that the eyes are in optimal location for eye tracker
    def runTrackBox(self, trackWin = None):

        # check to see that eyetracker is connected
        if self.eyetracker is None:
            raise RuntimeError("There is no eyetracker object. \n" +\
                               "Try running setEyeTracker().")
        # check window attribute
        if self.win is None:
            raise RuntimeError("No experimental monitor has been specified.\n" +\
                               "Try running setMonitor().")
        if trackWin is not None and not isinstance(trackWin, visual.Window):
            raise TypeError("If trackWin parameter is set, then it should be valid visual.Window object")

        # start the eyetracker
        self.__startGazeData()
        # wait for it ot warm up
        pcore.wait(0.5)

        # use the existing window
        if trackWin is not None:
            # feedback about eye position
            self.__drawEyePositions(trackWin)
            pcore.wait(2)
        else: # use an own window
            # create window for visualizing eye position and text
            with visual.Window(size = [self.win.getSizePix()[0],
                                       self.win.getSizePix()[1]],
                                       pos = [0, 0],
                                       units = 'pix',
                                       fullscr = True,
                                       allowGUI = True,
                                       monitor = self.win,
                                       winType = 'pyglet',
                                       color = [0.4, 0.4, 0.4]) as ownTrackWin:
                ownTrackWin.mouseVisible = False

                # feedback about eye position
                self.__drawEyePositions(ownTrackWin)
                pcore.wait(2)

    # function for running a complete calibration routine
    def runFullCalibration(self, numCalibPoints = None, calibWin = None):

        if numCalibPoints is not None:
            if not isinstance(numCalibPoints, numbers.Number):
                raise TypeError("numCalibPoints should be a number.")
            if numCalibPoints not in [5, 9]:
                raise ValueError("Only 5 or 9 points calibration is supported.")

        if calibWin is not None and not isinstance(calibWin, visual.Window):
            raise TypeError("calibWin should be a valid visual.Window object.")

        # check that eyetracker is connected before running
        if self.eyetracker is None:  # eyeTracker
            raise RuntimeError("No eyetracker is specified. " +\
                               "Aborting calibration.\n" +\
                               "Try running setEyeTracker().")
        # check window attribute
        if self.win is None:
            raise RuntimeError("No experimental monitor has been specified.\n" +\
                               "Try running setMonitor().")

        # create dictionary of calibration points
        # if nothing entered then default is five
        if numCalibPoints is None:
            pointList = [('1',(0.1, 0.1)), ('2',(0.9, 0.1)), ('3',(0.5, 0.5)),
                         ('4',(0.1, 0.9)), ('5',(0.9, 0.9))]
        elif numCalibPoints is 5:
            pointList = [('1',(0.1, 0.1)), ('2',(0.9, 0.1)), ('3',(0.5, 0.5)),
                         ('4',(0.1, 0.9)), ('5',(0.9, 0.9))]
        elif numCalibPoints is 9:
            pointList = [('1',(0.1, 0.1)), ('2',(0.5, 0.1)), ('3',(0.9, 0.1)),
                         ('4',(0.1, 0.5)), ('5',(0.5, 0.5)), ('6',(0.9, 0.5)),
                         ('7',(0.1, 0.9)), ('8',(0.5, 0.9)), ('9',(0.9, 0.9))]

        # randomize points as ordered dictionary
        np.random.shuffle(pointList)
        calibDict = collections.OrderedDict(pointList)

        # create window for calibration
        if calibWin is None:
            calibWin = visual.Window(size = [self.win.getSizePix()[0],
                                             self.win.getSizePix()[1]],
                                     pos = [0, 0],
                                     units = 'pix',
                                     fullscr = True,
                                     allowGUI = True,
                                     monitor = self.win,
                                     winType = 'pyglet',
                                     color = [0.4, 0.4, 0.4])
        calibWin.mouseVisible = False
        # stimuli for holding text
        calibMessage = visual.TextStim(calibWin,
                                       color = [1.0, 1.0, 1.0],  # text
                                       units = 'norm',
                                       height = 0.08,
                                       pos = (0.0, 0.1))

        self.runTrackBox(calibWin)

        # run calibration rutine
        self.__drawCalibrationScreen(calibDict, calibWin)

        # run validation
        self.runValidation(calibDict, calibWin)
        # close window
        calibMessage.text = _("Finished validating the calibration.\n\n" \
                              "Calibration is complete. Closing window.")
        calibMessage.draw()
        calibWin.flip()
        pcore.wait(3)
        calibWin.close()


    # function for running validation routine post calibration to check
    # calibration precision and accuracy
    def runValidation(self, pointDict = None, valWin = None):

        # check the values of the point dictionary
        if pointDict is None:
            if self.logging:
                print("pointDict has no value. Using 5 point default.")
            pointList = [('1',(0.1, 0.1)), ('2',(0.9, 0.1)), ('3',(0.5, 0.5)),
                         ('4',(0.1, 0.9)), ('5',(0.9, 0.9))]
            pointDict = collections.OrderedDict(pointList)
        if not isinstance(pointDict, dict):
            raise TypeError("pointDict must be a dictionary with number " +\
                            "keys and coordinate values.")
        if valWin is not None and not isinstance(valWin, visual.Window):
            raise TypeError("valWin should be a valid visual.Window object.")
        # check window attribute
        if self.win is None:
            raise RuntimeError("No experimental monitor has been specified.\n" +\
                               "Try running setMonitor().")
        # start eyetracker
        self.__startGazeData()
        # let it warm up briefly
        pcore.wait(0.5)

        # use existing window
        if valWin is not None:
            self.__drawValidationScreen(pointDict, valWin)
        else:
            # window stimuli
            with visual.Window(size = [self.win.getSizePix()[0],
                                       self.win.getSizePix()[1]],
                                       pos = [0, 0],
                                       units = 'pix',
                                       fullscr = True,
                                       allowGUI = True,
                                       monitor = self.win,
                                       winType = 'pyglet',
                                       color = [0.4, 0.4, 0.4]) as ownValWin:
                ownValWin.mouseVisible = False
                self.__drawValidationScreen(pointDict, ownValWin)