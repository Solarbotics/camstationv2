#!usr/bin/env python3
"""Processes chessboard corners to produce camera and distortion matrices."""

import cv2
import numpy

objpoints = []
imgpoints = []

width = 7
height = 5

objp = numpy.zeros((height*width,3), numpy.float32)
objp[:,:2] = numpy.mgrid[0:height,0:width].T.reshape(-1,2)

NUM_CORNERS = 11

# Expects each corner array to be saved in a file
# corners1.npy, corners2.npy, ..., corners{NUM_CORNERS-1}.npy
for i in range(NUM_CORNERS):
    corners = numpy.load(f"corners{i + 1}.npy")
    objpoints.append(objp)
    imgpoints.append(corners)

image = cv2.imread("exampleImage.jpg")

print(image.shape)

ret, camMatrix, distCoeffs, rvecs, tvecs = cv2.calibrateCamera(objpoints, imgpoints, (image.shape[1], image.shape[0]), None, None)

print(ret, camMatrix, distCoeffs, rvecs, tvecs, sep="\nNEXT\n")

# Calculate error
mean_error = 0
for i in range(len(objpoints)):
    imgpoints2, _ = cv2.projectPoints(objpoints[i], rvecs[i], tvecs[i], camMatrix, distCoeffs)
    error = cv2.norm(imgpoints[i], imgpoints2, cv2.NORM_L2) / len(imgpoints2)
    mean_error += error

numpy.savetxt("newCameraMatrix.txt", camMatrix, delimiter=",")
numpy.savetxt("newCameraDistortion.txt", distCoeffs, delimiter=",")

print(f"Error: {mean_error/len(objpoints)}")
