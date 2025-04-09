from ultralytics import YOLO
import cv2

model = YOLO("best.pt")

image_path = input("Please enter the path to the image: ")

results = model(image_path)

results[0].show()
