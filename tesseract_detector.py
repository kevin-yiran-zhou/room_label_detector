import cv2
import numpy as np
import pytesseract
from PIL import Image, ImageEnhance, ImageFilter
import time


def reorder_corners(corners):
    top_right, top_left, bottom_left, bottom_right = corners
    points = np.array([top_right, top_left, bottom_left, bottom_right])
    y_sorted = points[np.argsort(points[:, 1])]
    top_points = y_sorted[:2]
    bottom_points = y_sorted[2:]
    top_left, top_right = top_points[np.argsort(top_points[:, 0])]
    bottom_left, bottom_right = bottom_points[np.argsort(bottom_points[:, 0])]
    return np.array([top_right, top_left, bottom_left, bottom_right])


def detect_number(image, corners):
    reordered_corners = reorder_corners(corners)
    top_right, top_left, bottom_left, bottom_right = reordered_corners

    width = max(np.linalg.norm(np.array(top_right) - np.array(top_left)),
                np.linalg.norm(np.array(bottom_right) - np.array(bottom_left)))
    height = max(np.linalg.norm(np.array(top_left) - np.array(bottom_left)),
                 np.linalg.norm(np.array(top_right) - np.array(bottom_right)))
    
    dst_points = np.array([
        [0, 0],
        [width - 1, 0],
        [width - 1, height - 1],
        [0, height - 1]
    ], dtype="float32")
    
    src_points = np.array([top_left, top_right, bottom_right, bottom_left], dtype="float32")
    
    matrix = cv2.getPerspectiveTransform(src_points, dst_points)
    warped = cv2.warpPerspective(image, matrix, (int(width), int(height)))
    cv2.imshow('Warped Image', warped)

    # OCR
    image = Image.fromarray(warped)
    gray_image = image.convert('L')
    enhancer = ImageEnhance.Contrast(gray_image)
    enhanced_image = enhancer.enhance(2)
    threshold_image = enhanced_image.point(lambda p: p > 75 and 255)
    sharpened_image = threshold_image.filter(ImageFilter.SHARPEN)
    ## Detect only digits
    # text = pytesseract.image_to_string(sharpened_image, config='--oem 3 --psm 6 outputbase digits')
    # Detect digits and letters
    text = pytesseract.image_to_string(sharpened_image, config='--oem 3 --psm 6')

    text = text.replace(" ", "").replace("\n", "")
    return text, reordered_corners


def detect_room_label_contours(image, resize_factor=5, area_threshold=100, approx_tolerance=0.1):
    start_time = time.time()
    # Resize the image
    image = cv2.resize(image, (int(image.shape[1] / resize_factor), int(image.shape[0] / resize_factor)))
    
    # Apply bilateral filter for noise reduction while keeping edges sharp
    filtered_image = cv2.bilateralFilter(image, 15, 80, 80)
    
    # Convert to grayscale
    gray = cv2.cvtColor(filtered_image, cv2.COLOR_BGR2GRAY)
    
    # Apply dilation followed by erosion to enhance the shapes
    kernel = np.ones((5, 5), np.float32) / 49
    dilated = cv2.dilate(gray, kernel, iterations=3)
    
    # Apply erosion to remove noise
    eroded = cv2.erode(dilated, kernel, iterations=1)
    
    # Detect edges using Canny Edge Detector
    thr1, thr2 = 50, 200
    edged = cv2.Canny(eroded, thr1, thr2)
    
    # Find contours
    contours, _ = cv2.findContours(edged, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    rectangle_corners = []
    the_corners = None

    for cnt in contours:
        area = cv2.contourArea(cnt)
        
        if area > area_threshold:
            approx = cv2.approxPolyDP(cnt, approx_tolerance * cv2.arcLength(cnt, True), True)
            if len(approx) == 4:
                corners = [point[0] for point in approx]
                rectangle_corners.append(corners)

                OCR_result, reordered_corners = detect_number(image, corners)

                if sum(char.isdigit() for char in OCR_result) >= 1:
                # if len(OCR_result) >= 4:
                    cv2.drawContours(image, [approx], -1, (0, 255, 0), 3)
                    cv2.putText(image, OCR_result, tuple(corners[0]), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
                    the_corners = reordered_corners
                    the_number = OCR_result
                else:
                    cv2.drawContours(image, [approx], -1, (0, 0, 255), 3)
                    cv2.putText(image, "No numbers", tuple(corners[0]), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
            else:
                cv2.drawContours(image, [approx], -1, (0, 0, 255), 3)
                cv2.putText(image, "Not rectangle", tuple(approx[0][0]), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)

    
    # if the_corners is not None:
    #     print("Time taken:", time.time() - start_time)
    #     cv2.imshow('Rectangles Detected', image)
    #     while cv2.getWindowProperty('Rectangles Detected', cv2.WND_PROP_VISIBLE) >= 1:
    #         key = cv2.waitKey(1)
    #         if key == 27:
    #             break
    #     cv2.destroyAllWindows()
    #     return the_corners, the_number
    # else:
    #     print("No room label detected")
    #     return None, None

    print("Time taken:", time.time() - start_time)
    cv2.imshow('Rectangles Detected', image)
    while cv2.getWindowProperty('Rectangles Detected', cv2.WND_PROP_VISIBLE) >= 1:
        key = cv2.waitKey(1)
        if key == 27:
            break
    cv2.destroyAllWindows()


image = cv2.imread("/home/kevinbee/Desktop/room_label_detector/images/office_dark.JPG")
# corners, number = detect_room_label_contours(image, resize_factor=4, area_threshold=10000, approx_tolerance=0.05)
detect_room_label_contours(image, resize_factor=4, area_threshold=5000, approx_tolerance=0.05)

image = cv2.imread("/home/kevinbee/Desktop/room_label_detector/images/office_dark_different_angle.JPG")
detect_room_label_contours(image, resize_factor=4, area_threshold=5000, approx_tolerance=0.05)

image = cv2.imread("/home/kevinbee/Desktop/room_label_detector/images/office.JPG")
detect_room_label_contours(image, resize_factor=5, area_threshold=5000, approx_tolerance=0.05)

image = cv2.imread("/home/kevinbee/Desktop/room_label_detector/images/office_.JPG")
detect_room_label_contours(image, resize_factor=2.5, area_threshold=5000, approx_tolerance=0.05)

image = cv2.imread("/home/kevinbee/Desktop/room_label_detector/images/office_rotated.JPG")
detect_room_label_contours(image, resize_factor=4, area_threshold=5000, approx_tolerance=0.05)

image = cv2.imread("/home/kevinbee/Desktop/room_label_detector/images/office_rotated_.JPG")
detect_room_label_contours(image, resize_factor=2.5, area_threshold=5000, approx_tolerance=0.05)

image = cv2.imread("/home/kevinbee/Desktop/room_label_detector/images/office_different_angle.JPG")
detect_room_label_contours(image, resize_factor=4, area_threshold=5000, approx_tolerance=0.05)

image = cv2.imread("/home/kevinbee/Desktop/room_label_detector/images/office_different_angle_.JPG")
detect_room_label_contours(image, resize_factor=2.5, area_threshold=10000, approx_tolerance=0.05)