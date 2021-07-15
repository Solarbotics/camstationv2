#!usr/bin/env python3
"""Methods to help calibrate a camera."""

import os
import pathlib
import sys

import cv2
import numpy

from . import camera


def next_name(path: str) -> str:
    """Find the next numeric unused path.

    E.g. if dir is empty, next_name('dir/file') will return 'dir/file0',
    but if 'dir/file0', 'dir/file1' already exist, then 'dir/file2' will be returned.

    If the provided path has an extension (. character), indexes will be checked/added
    before the first period.
    """
    name, *extensions = path.split(".")
    extension = ".".join(extensions)
    # If an extension exists, prefix it with .
    if extension:
        extension = "." + extension
    index = 0
    while os.path.exists(f"{name}{index}{extension}"):
        index += 1
    return f"{name}{index}{extension}"


def save_snapshot(width, height) -> None:
    """Take a snapshot from the camera and pull chessboard data."""
    _, result = camera.Camera(
        processor=camera.ChessboardFinder(width, height)
    ).get_processed_frame()
    data, encoded = result
    # print(data, encoded)
    pathlib.Path("corners").mkdir(parents=True, exist_ok=True)
    with open(next_name("corners/corners.npy"), "wb") as file:
        numpy.save(file, data)
    pathlib.Path("images").mkdir(parents=True, exist_ok=True)
    with open(next_name("images/image.jpg"), "wb") as imFile:
        imFile.write(encoded)


def calculate_parameters(width, height, amount) -> None:
    """Use saved corner arrays and images to find camera and distortion parameters."""
    objpoints = []
    imgpoints = []

    objp = numpy.zeros((height * width, 3), numpy.float32)
    objp[:, :2] = numpy.mgrid[0:height, 0:width].T.reshape(-1, 2)

    NUM_CORNERS = amount

    # Expects each corner array to be saved in a file
    # corners1.npy, corners2.npy, ..., corners{NUM_CORNERS-1}.npy
    for i in range(NUM_CORNERS):
        try:
            corners = numpy.load(f"corners/corners{i}.npy")
        except ValueError:
            pass
        else:
            if corners.shape:
                objpoints.append(objp)
                imgpoints.append(corners)

    image = cv2.imread("images/image0.jpg")

    print(image.shape)

    ret, camMatrix, distCoeffs, rvecs, tvecs = cv2.calibrateCamera(
        objpoints, imgpoints, (image.shape[1], image.shape[0]), None, None
    )

    print(ret, camMatrix, distCoeffs, rvecs, tvecs, sep="\nNEXT\n")

    # Calculate error
    mean_error = 0
    for i in range(len(objpoints)):
        imgpoints2, _ = cv2.projectPoints(
            objpoints[i], rvecs[i], tvecs[i], camMatrix, distCoeffs
        )
        error = cv2.norm(imgpoints[i], imgpoints2, cv2.NORM_L2) / len(imgpoints2)
        mean_error += error

    numpy.savetxt("newCameraMatrix.txt", camMatrix, delimiter=",")
    numpy.savetxt("newCameraDistortion.txt", distCoeffs, delimiter=",")

    print(f"Error: {mean_error/len(objpoints)}")


if __name__ == "__main__":
    BOARD_WIDTH = 7
    BOARD_HEIGHT = 5
    calculate_parameters(BOARD_WIDTH, BOARD_HEIGHT, int(sys.argv[1]))
